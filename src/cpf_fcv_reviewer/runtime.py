from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from secrets import compare_digest

from .contracts import (
    DetailLevel,
    DiagnosticMode,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    UserCorrection,
)
from .evidence_builder import build_reproducible_evidence_pack
from .extraction import extract_document, require_readable_primary
from .model_gateway import AnthropicModelGateway
from .orchestrator import ReviewOrchestrator
from .prompts import load_prompt
from .public_research import AnthropicPublicResearchGateway
from .registry import RegistryUnavailable, load_registry_bundle
from .review_engine import ReviewEngine
from .sources import choose_authoritative_source
from .validators import (
    matched_prohibited_policy_phrases,
    result_text,
    validate_reproducibility_metadata,
    validate_review,
)

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

    def extract_uploaded_documents(context):
        payload = context.get("payload")
        if not payload or "cpf" not in payload:
            return context
        primary = payload["cpf"]
        primary_document = extract_document(primary["bytes"], primary["name"])
        require_readable_primary(primary_document)
        package_documents = tuple(
            extract_document(item["bytes"], item["name"], max_pdf_pages=2)
            for item in payload.get("package_documents", ())
        )
        context_documents = tuple(
            extract_document(item["bytes"], item["name"], max_pdf_pages=2)
            for item in payload.get("context_documents", ())
        )
        context["primary_document"] = primary_document
        context["package_documents"] = package_documents
        context["context_documents"] = context_documents
        context["extraction_warnings"] = tuple(
            warning
            for document in (
                primary_document,
                *package_documents,
                *context_documents,
            )
            for warning in document.warnings
        )
        return context

    def build_uploaded_evidence(context):
        payload = context.get("payload")
        primary_document = context.get("primary_document")
        if not payload or primary_document is None:
            return context
        review_focus = payload.get("review_focus", "")
        if not isinstance(review_focus, str):
            review_focus = ""
        review_focus = review_focus.strip()[:4000]

        document_groups = (
            (DocumentRole.PRIMARY, (primary_document,), 12),
            (DocumentRole.PACKAGE, tuple(context.get("package_documents", ())), 4),
            (DocumentRole.CONTEXT, tuple(context.get("context_documents", ())), 2),
        )
        selected_segments = []
        for document_role, documents, per_document_limit in document_groups:
            for document in documents:
                selected_segments.extend(
                    (document, segment, document_role)
                    for segment in document.segments[:per_document_limit]
                )
        selected_segments = selected_segments[:24]

        role_counts = {role: 0 for role, _, _ in document_groups}
        evidence = []
        for document, segment, document_role in selected_segments:
            role_counts[document_role] += 1
            evidence.append(
                EvidenceItem(
                    evidence_id=(
                        f"{document_role.value}-"
                        f"{role_counts[document_role]:03d}"
                    ),
                    evidence_type="document_fact",
                    text=segment.text[:1600],
                    locator=EvidenceLocator(
                        document_title=document.name,
                        page=segment.page,
                        heading=segment.heading,
                        element=segment.element,
                        excerpt=segment.text[:600],
                    ),
                    confidence="high",
                    document_role=document_role,
                )
            )

        correction_payloads = tuple(payload.get("corrections", ()))
        corrections = tuple(
            UserCorrection(
                correction_id=item["correction_id"],
                created_at=datetime.fromisoformat(item["created_at"]),
                affected_priority_area_id=item.get("affected_priority_area_id"),
                text=item["text"][:2000],
                rationale=(item.get("rationale") or "")[:1000] or None,
                independently_supported=item.get("independently_supported", False),
            )
            for item in correction_payloads[-20:]
        )
        evidence.extend(
            EvidenceItem(
                evidence_id=f"correction-{item.correction_id}",
                evidence_type="user_correction",
                text=item.text,
                confidence="medium" if item.independently_supported else "low",
            )
            for item in corrections
        )

        document_bytes = {
            f"primary:{payload['cpf']['name']}": payload["cpf"]["bytes"]
        }
        document_bytes.update(
            {
                f"package:{index}:{item['name']}": item["bytes"]
                for index, item in enumerate(
                    payload.get("package_documents", ()),
                    start=1,
                )
            }
        )
        document_bytes.update(
            {
                f"context:{index}:{item['name']}": item["bytes"]
                for index, item in enumerate(
                    payload.get("context_documents", ()),
                    start=1,
                )
            }
        )
        prompt_bytes = {
            name: load_prompt(name).encode("utf-8")
            for name in ("diagnostic_map", "review", "repair")
        }
        context["evidence_pack"] = build_reproducible_evidence_pack(
            run_id=context["assessment_id"],
            created_at=datetime.now(UTC),
            review_stage=payload["review_stage"],
            diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
            documents=document_bytes,
            registry_bundle=path.read_bytes(),
            detail_level=payload.get("detail_level", DetailLevel.STANDARD),
            guidance=review_focus,
            prompt_bytes=prompt_bytes,
            model_id=config["ANTHROPIC_MODEL_ID"],
            source_scan_at=datetime.now(UTC),
            output_language="en",
            evidence=tuple(evidence),
            diagnostic_entries=(),
            material_diagnostic_ids=(),
            corrections=corrections,
            warnings=tuple(context.get("extraction_warnings", ())),
            correction_ids=tuple(item["correction_id"] for item in correction_payloads),
            parent_run_id=payload.get("parent_assessment_id"),
        )
        return context

    def review_validation_issues(context):
        evidence_ids = {item.evidence_id for item in context["evidence_pack"].evidence}
        issues = list(
            validate_review(
                context["result"],
                evidence_ids=evidence_ids,
                prohibited_terms=prohibited_terms,
            )
        )
        issues.extend(validate_reproducibility_metadata(context["result"].metadata))
        return [{"code": issue.code, "message": issue.message} for issue in issues]

    def mark_step(name):
        def step(context):
            context.setdefault("completed_steps", []).append(name)
            if name == "extract":
                return extract_uploaded_documents(context)
            if name == "resolve_sources" and "source_candidates" in context:
                context["authoritative_source"] = choose_authoritative_source(
                    context["source_candidates"]
                )
            if name == "review" and "evidence_pack" in context:
                review_focus = context.get("payload", {}).get("review_focus", "")
                if not isinstance(review_focus, str):
                    review_focus = ""
                review_focus = review_focus.strip()[:4000]
                context["result"] = review_engine.review(
                    context["evidence_pack"],
                    review_focus=review_focus,
                )
            if name == "research":
                context["public_research_gateway"] = research_gateway
            if name == "build_evidence":
                return build_uploaded_evidence(context)
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
        context["result"] = review_engine.repair(
            context["result"],
            issues,
            forbidden_phrases=matched_prohibited_policy_phrases(
                result_text(context["result"]),
                prohibited_terms,
            ),
        )
        context["validation_issues"] = review_validation_issues(context)
        return context

    orchestrator = ReviewOrchestrator(
        steps=tuple((name, mark_step(name)) for name in STEP_NAMES),
        repair=repair,
    )
    return {"review_orchestrator": orchestrator, "registry_bundle": bundle}
