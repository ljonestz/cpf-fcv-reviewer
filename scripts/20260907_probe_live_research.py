"""Run the three authorized research-only probes; no review or fallback calls.

Credentials stay in memory. Raw public-source results stay in the local output folder.
Default is a no-cost dry run; --execute enables one research attempt per country.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path

import certifi
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cpf_fcv_reviewer import public_research  # noqa: E402
from cpf_fcv_reviewer.extraction import extract_document  # noqa: E402
from cpf_fcv_reviewer.research_controller import (  # noqa: E402
    ResearchController,
    ResearchMode,
    ResearchRequest,
)

SERVICE_ID = "srv-d9tju52jobas73d6jvk0"


def service_environment() -> tuple[dict[str, str], ssl.SSLContext]:
    """Read only this app's environment; never persist or print credentials."""
    config = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    authorization = config["mcpServers"]["render"]["headers"]["Authorization"]
    tls = ssl.create_default_context(cafile=certifi.where())
    tls.load_default_certs()
    with httpx.Client(verify=tls, timeout=30) as client:
        response = client.get(
            f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars",
            headers={"Authorization": authorization},
            params={"limit": 100},
        )
        response.raise_for_status()
        values = {row["envVar"]["key"]: row["envVar"]["value"] for row in response.json()}
    return values, tls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guinea-cpf", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--country", choices=("Guinea", "Kenya", "Haiti"))
    parser.add_argument("--replay", type=Path,
                        help="Reuse saved public source citations; calls normalization only.")
    args = parser.parse_args()
    if args.replay and not args.country:
        parser.error("--replay requires --country")
    document = extract_document(args.guinea_cpf.read_bytes(), args.guinea_cpf.name)
    primary = " ".join(segment.text for segment in document.segments)[:12000]
    today = datetime.now(UTC).date()
    cases = [
        ResearchRequest(
            "Guinea",
            today,
            ResearchMode.HOLISTIC,
            primary_cpf_context=primary,
            review_focus="Current FCV developments affecting the supplied CPF priorities.",
        ),
        ResearchRequest(
            "Kenya",
            today,
            ResearchMode.HOLISTIC,
            review_focus="Research-only test: governance, social cohesion, exclusion and "
            "local service delivery; no Kenyan CPF was supplied.",
        ),
        ResearchRequest(
            "Haiti",
            today,
            ResearchMode.HOLISTIC,
            review_focus="Research-only test: violence, displacement, humanitarian access "
            "and delivery of basic services; no Haitian CPF was supplied.",
        ),
    ]
    if args.country:
        cases = [case for case in cases if case.country == args.country]
    print(
        json.dumps(
            {
                "mode": "execute" if args.execute else "dry_run",
                "countries": [case.country for case in cases],
                "guinea_context_characters": len(primary),
            }
        ),
        flush=True,
    )
    if not args.execute:
        return 0
    env, tls = service_environment()
    os.environ["SSL_CERT_FILE"] = certifi.where()
    from anthropic import Anthropic

    public_research.Anthropic = lambda **kw: Anthropic(
        http_client=httpx.Client(verify=tls, timeout=180), **kw
    )
    output = ROOT / "output" / datetime.now(UTC).strftime("%Y%m%d_%H%M%S_live-probes")
    output.mkdir(parents=True, exist_ok=False)
    print(json.dumps({"output": str(output), "model": env["ANTHROPIC_MODEL_ID"]}), flush=True)
    reports = []
    capture = {}
    extract_artifact = public_research._extract_search_artifact

    def observed_artifact(blocks, **kwargs):
        candidates, citations = [], []
        for block in blocks:
            kind = public_research._value(block, "type")
            if kind == "web_search_tool_result":
                for item in public_research._web_search_result_items(block):
                    title, url, published, basis = public_research._source_metadata(item)
                    if url:
                        candidates.append(
                            {
                                "title": title,
                                "url": url,
                                "published": str(published),
                                "date_basis": basis,
                            }
                        )
            elif kind == "text":
                for item in public_research._citation_items(block):
                    title, url, _, _ = public_research._source_metadata(item)
                    citations.append(
                        {
                            "title": title,
                            "url": url,
                            "quote": public_research._value(item, "cited_text"),
                        }
                    )
        capture.update({"candidates": candidates, "citations": citations})
        artifact, segments = extract_artifact(blocks, **kwargs)
        capture["retained_sources"] = [
            source.model_dump(mode="json") for source in artifact.sources
        ]
        return artifact, segments

    public_research._extract_search_artifact = observed_artifact
    for case in cases:
        print(json.dumps({"started": case.country}), flush=True)
        events = []
        capture = {}
        with httpx.Client(verify=tls, timeout=10) as metadata_client:
            gateway = public_research.AnthropicPublicResearchGateway(
                env["ANTHROPIC_API_KEY"],
                env["ANTHROPIC_MODEL_ID"],
                timeout_seconds=float(env.get("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "180")),
                metadata_client=metadata_client,
            )
            if args.replay:
                saved = json.loads(args.replay.read_text(encoding="utf-8"))
                if saved["country"] != case.country:
                    raise ValueError("Replay country mismatch.")
                source_data = saved["source_diagnostics"]
                blocks = [{"type": "web_search_tool_result", "content": [
                    {"type": "web_search_result", "title": item["title"],
                     "url": item["url"], "page_age": item.get("published")}
                    for item in source_data["candidates"]
                ]}]
                blocks.extend({"type": "text", "text": item["quote"], "citations": [
                    {"type": "web_search_result_location", "title": item["title"],
                     "url": item["url"], "cited_text": item["quote"]}
                ]} for item in source_data["citations"] if item.get("quote"))
                replay_response = {"content": blocks, "stop_reason": "end_turn"}
                gateway._create_web_search_response = (
                    lambda *a, response=replay_response, **kw: response
                )
            parse = gateway._client.messages.parse

            def observed_parse(*a, parse=parse, current_capture=capture, **kw):
                response = parse(*a, **kw)
                parsed = getattr(response, "parsed_output", None)
                current_capture["normalization"] = {
                    "stop_reason": getattr(response, "stop_reason", None),
                    "parsed": parsed.model_dump(mode="json") if parsed is not None else None,
                    "usage": response.usage.model_dump(mode="json"),
                }
                return response

            gateway._client.messages.parse = observed_parse
            search = gateway.search

            def observed_search(prompt, search=search, current_capture=capture):
                claims = search(prompt)
                current_capture["claims_before_coverage"] = [
                    c.model_dump(mode="json") for c in claims
                ]
                return claims

            gateway.search = observed_search
            controller = ResearchController(gateway, max_attempts=1)
            try:
                result = controller.run(
                    case,
                    lambda kind, data, events=events: events.append({"event": kind, "data": data}),
                    allow_document_led=True,
                )
                report = {
                    "country": case.country,
                    "tier": result.tier.value,
                    "claims": [claim.model_dump(mode="json") for claim in result.claims],
                    "rejected": result.rejected,
                    "limitation": result.limitation,
                    "diagnostics": gateway.last_diagnostics,
                    "events": events,
                }
            except Exception as exc:
                report = {
                    "country": case.country,
                    "error_type": type(exc).__name__,
                    "diagnostics": gateway.last_diagnostics,
                    "events": events,
                }
            finally:
                gateway._client.close()
        report["source_diagnostics"] = capture
        (output / f"{case.country.lower()}.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        summary = {
            k: v
            for k, v in report.items()
            if k not in {"claims", "events", "rejected", "source_diagnostics"}
        }
        summary["claim_count"] = len(report.get("claims", []))
        reports.append(summary)
        print(json.dumps(summary), flush=True)
    (output / "summary.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    return 0 if all(r["claim_count"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
