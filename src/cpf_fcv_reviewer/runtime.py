from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from secrets import compare_digest

from .model_gateway import AnthropicModelGateway
from .orchestrator import ReviewOrchestrator
from .public_research import AnthropicPublicResearchGateway
from .registry import RegistryUnavailable, load_registry_bundle
from .review_engine import ReviewEngine
from .sources import choose_authoritative_source
from .validators import validate_priority_questions, validate_review

STEP_NAMES = (
    "extract",
    "resolve_sources",
    "research",
    "build_evidence",
    "map",
    "review",
    "validate",
    "render",
)


def build_runtime_services(config: dict) -> dict:
    path = Path(config.get("REGISTRY_BUNDLE_PATH", ""))
    expected_hash = str(config.get("REGISTRY_BUNDLE_SHA256", "")).strip().lower()
    if not expected_hash:
        raise RuntimeError("Approved registry bundle hash is required.")
    try:
        actual_hash = sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise RuntimeError("Approved registry bundle is unavailable or invalid.") from None
    if not compare_digest(actual_hash, expected_hash):
        raise RuntimeError("Approved registry bundle hash mismatch.")
    try:
        bundle = load_registry_bundle(
            path,
            allow_synthetic=config.get("ALLOW_SYNTHETIC_REGISTRY", False),
        )
    except RegistryUnavailable as exc:
        raise RuntimeError(str(exc)) from exc

    model_gateway = AnthropicModelGateway(
        config["ANTHROPIC_API_KEY"],
        config["ANTHROPIC_MODEL_ID"],
    )
    research_gateway = AnthropicPublicResearchGateway(
        config["ANTHROPIC_API_KEY"],
        config["ANTHROPIC_MODEL_ID"],
    )
    review_engine = ReviewEngine(model_gateway)

    prohibited_terms = {term for entry in bundle.entries for term in entry.prohibited_terms}

    def review_validation_issues(context):
        evidence_ids = {item.evidence_id for item in context["evidence_pack"].evidence}
        issues = list(
            validate_review(
                context["result"],
                evidence_ids=evidence_ids,
                prohibited_terms=prohibited_terms,
            )
        )
        confirmed = tuple(context.get("payload", {}).get("priority_questions", ()))
        issues.extend(validate_priority_questions(confirmed, context["result"]))
        return [
            {"code": issue.code, "message": issue.message}
            for issue in issues
        ]

    def mark_step(name):
        def step(context):
            context.setdefault("completed_steps", []).append(name)
            if name == "resolve_sources" and "source_candidates" in context:
                context["authoritative_source"] = choose_authoritative_source(
                    context["source_candidates"]
                )
            if name == "review" and "evidence_pack" in context:
                confirmed = tuple(context.get("payload", {}).get("priority_questions", ()))
                context["result"] = review_engine.review(
                    context["evidence_pack"],
                    priority_questions=confirmed,
                )
            if name == "research":
                context["public_research_gateway"] = research_gateway
            if name == "validate" and {
                "result",
                "evidence_pack",
            }.issubset(context):
                context["validation_issues"] = review_validation_issues(context)
            if name == "render" and "result" not in context:
                raise RuntimeError("Review result is unavailable.")
            return context

        return step

    def repair(context, issues):
        if "result" not in context:
            return context
        context["result"] = model_gateway.generate(
            prompt_name="repair",
            payload={
                "draft": context["result"].model_dump(mode="json"),
                "validation_issues": issues,
            },
            output_type=type(context["result"]),
        )
        context["validation_issues"] = review_validation_issues(context)
        return context

    orchestrator = ReviewOrchestrator(
        steps=tuple((name, mark_step(name)) for name in STEP_NAMES),
        repair=repair,
    )
    return {"review_orchestrator": orchestrator, "registry_bundle": bundle}
