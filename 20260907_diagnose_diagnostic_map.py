"""Probe only diagnostic mapping; dry-run by default, at most two model calls.

Run with --document PATH, adding --execute only after paid-call authorization.
Credentials come only from ANTHROPIC_API_KEY. Output contains no document/model text.
"""
# Local source imports follow the repository-relative path setup.
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import DiagnosticMap, DocumentRole
from cpf_fcv_reviewer.diagnostic_map import validate_diagnostic_references
from cpf_fcv_reviewer.extraction import extract_document
from cpf_fcv_reviewer.model_gateway import AnthropicModelGateway
from cpf_fcv_reviewer.runtime import (
    DIAGNOSTIC_MAP_MAX_ESTIMATED_INPUT_TOKENS,
    DIAGNOSTIC_MAX_CHARACTERS,
    DIAGNOSTIC_MAX_PAGES,
    DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
    _diagnostic_page_items,
    _safe_diagnostic_map_schema_issues,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--model", default="claude-sonnet-4-5")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    document = extract_document(
        args.document.read_bytes(), args.document.name,
        max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
        max_segments=DIAGNOSTIC_MAX_PAGES,
        max_characters=DIAGNOSTIC_MAX_CHARACTERS,
        max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
    )
    items = _diagnostic_page_items(document, document_role=DocumentRole.CONTEXT)
    if not items:
        raise RuntimeError("no_extractable_text")
    ids = tuple(item.evidence_id for item in items)
    evidence = []
    for item in items:
        value = item.model_dump(mode="json")
        value["locator"].pop("excerpt", None)
        evidence.append(value)
    payload = {
        "diagnostic_title": document.name,
        "material_evidence_ids": list(ids),
        "evidence": evidence,
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    estimated = (max(len(serialized), len(serialized.encode("utf-8"))) + 2) // 3
    if estimated > DIAGNOSTIC_MAP_MAX_ESTIMATED_INPUT_TOKENS:
        raise RuntimeError("input_budget_exceeded")
    report = {"model": args.model, "pages_with_text": len(items),
              "estimated_input_tokens": estimated, "attempts": [],
              "status": "dry_run"}
    print(json.dumps(report), flush=True)
    if not args.execute:
        return 0
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("api_key_unavailable")
    gateway = AnthropicModelGateway(key, args.model)
    # Disable transport retries so authorization caps actual requests at two.
    gateway.client = gateway.client.with_options(max_retries=0, timeout=180.0)
    for attempt in (1, 2):
        print(json.dumps({"attempt_started": attempt}), flush=True)
        try:
            mapped = gateway.generate(prompt_name="diagnostic_map", payload=payload,
                                      output_type=DiagnosticMap)
        except ValidationError as error:
            issues = _safe_diagnostic_map_schema_issues(error)
            report["attempts"].append({"attempt": attempt, "issues": issues})
            report["status"] = "schema_invalid"
            print(json.dumps(report["attempts"][-1]), flush=True)
            payload = {**payload, "schema_retry": {"issues": issues}}
            continue
        except Exception as error:
            report["attempts"].append({"attempt": attempt,
                                       "error_type": type(error).__name__})
            report["status"] = "provider_error"
            break
        try:
            validate_diagnostic_references(ids, mapped.entries)
        except ValueError:
            report["status"] = "invalid_references"
        else:
            report["status"] = "mapped"
        report["attempts"].append({"attempt": attempt, "entry_count": len(mapped.entries)})
        break
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    output = ROOT / f"{stamp}_diagnostic-map-sanitized.json"
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "mapped" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Never print exception messages: SDK errors can include submitted text.
        print(json.dumps({"status": "preflight_error", "error_type": type(error).__name__}))
        raise SystemExit(2) from None
