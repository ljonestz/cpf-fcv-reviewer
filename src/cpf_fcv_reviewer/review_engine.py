from __future__ import annotations

import json
from collections.abc import Mapping
import re

from pydantic import ValidationError

from .contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DocumentCoverage,
    DocumentRole,
    EvidenceItem,
    EvidencePack,
    FCVStrategicShift,
    FCVStrategyAssessment,
    ReviewDraft,
    ReviewResult,
)
from .extraction import PackageCoverageUnavailable
from .model_gateway import ModelGateway
from .review_profiles import DETAIL_PROFILES, STAGE_PROFILES

# "missing_current_context_support" is intentionally excluded: it is raised with
# severity="advisory" and is therefore filtered out by the orchestrator before repair
# is ever called.  Advisory issues are surfaced to the caller via "advisory_notice"
# events; they never reach _validate_repair_issues().
REPAIRABLE_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "limited_mode_overclaim",
        "unknown_priority_area",
        "unknown_evidence",
        "raw_evidence_id_in_narrative",
        "unknown_institutional_referral",
        "unknown_assessment_evidence",
        "missing_rra_driver_assessment",
        "incomplete_strategy_assessment",
        "missing_registry_support",
        "stage_overreach",
        "stage_length_overreach",
        "missing_comment_reference",
        "prohibited_policy_language",
        "withheld_drafting",
        "invalid_revision_summary_title",
        "incomplete_coverage_absence_claim",
    }
)


def _schema_property_names(schema: object) -> frozenset[str]:
    names = set()
    pending = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(str(name) for name in properties)
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return frozenset(names)


_REVIEW_DRAFT_SCHEMA_FIELDS = _schema_property_names(ReviewDraft.model_json_schema())
_MAX_SCHEMA_RETRY_ISSUES = 25
_MAX_SCHEMA_LOCATION_DEPTH = 8
_SAFE_MODEL_VALIDATION_TYPES = {
    "gap_locus is required for partially_aligned and not_evidenced assessments.": (
        "gap_locus_required"
    ),
    "evidence_ids must contain at least one identifier unless status is not_assessable.": (
        "assessment_evidence_required"
    ),
    "Document evidence requires page, heading, or element.": "document_coordinate_required",
}
REVIEW_MAX_ESTIMATED_INPUT_TOKENS = 160_000


def _estimated_input_tokens(payload: dict) -> int:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (max(len(serialized), len(serialized.encode("utf-8"))) + 2) // 3


def _safe_schema_issues(error: ValidationError) -> list[dict[str, object]]:
    issues = []
    for item in error.errors(
        include_url=False,
        include_context=True,
        include_input=False,
    )[:_MAX_SCHEMA_RETRY_ISSUES]:
        location = []
        for part in item.get("loc", ())[:_MAX_SCHEMA_LOCATION_DEPTH]:
            if type(part) is int and 0 <= part <= 9999:
                location.append(part)
            elif isinstance(part, str) and part in _REVIEW_DRAFT_SCHEMA_FIELDS:
                location.append(part)
            else:
                location.append("unrecognized_field")
        issue_type = str(item.get("type", "validation_error"))
        if issue_type == "value_error":
            context = item.get("ctx")
            context_error = context.get("error") if isinstance(context, dict) else None
            if (
                type(context_error) is ValueError
                and len(context_error.args) == 1
                and isinstance(context_error.args[0], str)
            ):
                issue_type = _SAFE_MODEL_VALIDATION_TYPES.get(context_error.args[0], issue_type)
        if not re.fullmatch(r"[a-z0-9_]{1,64}", issue_type):
            issue_type = "validation_error"
        issues.append({"loc": location, "type": issue_type})
    return issues


class ReviewSchemaUnavailable(RuntimeError):
    """A terminal review-schema failure with content-free diagnostics."""

    failure_code = "review_schema_invalid"

    def __init__(
        self,
        initial_error: ValidationError,
        retry_error: ValidationError,
    ) -> None:
        self.safe_diagnostics = {
            "attempts": [
                {
                    "attempt": attempt,
                    "issue_count": error.error_count(),
                    "issues": _safe_schema_issues(error),
                }
                for attempt, error in ((1, initial_error), (2, retry_error))
            ]
        }
        super().__init__("Review output failed schema validation after one retry.")


def _validate_repair_issues(issues: list[dict]) -> None:
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError(f"Repair issue at index {index} must be a dictionary.")
        if "code" not in issue:
            raise ValueError(f"Repair issue at index {index} has missing code.")
        code = issue["code"]
        if not isinstance(code, str):
            raise ValueError(f"Repair issue at index {index} must have a string code.")
        if code not in REPAIRABLE_ISSUE_CODES:
            raise ValueError(f"Repair issue has unknown code: {code}")


def _serialize_stage_profile(profile) -> dict[str, object]:
    return {
        "instruction": profile.instruction,
        "allowed_scales": [scale.value for scale in profile.allowed_scales],
        "max_immediate_insertion_words": profile.max_immediate_insertion_words,
    }


def _serialize_detail_profile(profile) -> dict[str, object]:
    return {
        "target_pages": profile.target_pages,
        "priority_area_range": list(profile.priority_area_range),
    }


def _scrub_raw_evidence_ids_from_narrative(
    draft: ReviewDraft,
    evidence_ids: set[str],
) -> ReviewDraft:
    raw_ids = sorted(
        (
            evidence_id
            for evidence_id in evidence_ids
            if evidence_id
            and (
                re.search(r"[-_]\d", evidence_id)
                or evidence_id.casefold().startswith("correction-")
            )
        ),
        key=len,
        reverse=True,
    )
    if not raw_ids:
        return draft
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_-])(?:{'|'.join(re.escape(item) for item in raw_ids)})(?![A-Za-z0-9_-])",
        re.IGNORECASE,
    )

    def scrub(text: str) -> str:
        return pattern.sub("the cited evidence", text)

    return draft.model_copy(
        update={
            "overall_read": scrub(draft.overall_read),
            "alignment_readout": scrub(draft.alignment_readout),
            "strategy_readout": scrub(draft.strategy_readout),
            "revision_summary": tuple(
                item.model_copy(update={"title": scrub(item.title)})
                for item in draft.revision_summary
            ),
            "priority_areas": tuple(
                item.model_copy(
                    update={
                        "heading": scrub(item.heading),
                        "assessment": scrub(item.assessment),
                        "why_it_matters": scrub(item.why_it_matters),
                        "recommended_action": scrub(item.recommended_action),
                        "comment_reference": (
                            scrub(item.comment_reference)
                            if item.comment_reference is not None
                            else None
                        ),
                    }
                )
                for item in draft.priority_areas
            ),
            "rra_driver_assessments": tuple(
                item.model_copy(
                    update={
                        "driver": scrub(item.driver),
                        "cpf_response": scrub(item.cpf_response),
                        "delivery_mechanism": scrub(item.delivery_mechanism),
                        "result_or_indicator": scrub(item.result_or_indicator),
                        "remaining_gap": scrub(item.remaining_gap),
                    }
                )
                for item in draft.rra_driver_assessments
            ),
            "fcv_strategy_assessments": tuple(
                item.model_copy(update={"assessment": scrub(item.assessment)})
                for item in draft.fcv_strategy_assessments
            ),
            "limitations": tuple(scrub(item) for item in draft.limitations),
            "coverage_note": scrub(draft.coverage_note),
        }
    )


STRATEGY_REGISTRY_EVIDENCE_IDS = {
    shift: f"registry-PUB-FCV-STRAT-{index:03d}"
    for index, shift in enumerate(FCVStrategicShift, start=1)
}


_COVERAGE_REPAIR_STATUSES = frozenset(
    {
        AssessmentStatus.NOT_ASSESSABLE,
        AssessmentStatus.PARTIALLY_ALIGNED,
    }
)


def _is_evidence_safe(row, evidence_ids: set[str]) -> bool:
    return set(row.evidence_ids).issubset(evidence_ids)


def _is_evidence_safe_strategy_row(
    row: FCVStrategyAssessment,
    evidence_ids: set[str],
) -> bool:
    if not _is_evidence_safe(row, evidence_ids):
        return False
    if row.status is AssessmentStatus.NOT_ASSESSABLE:
        return True
    required_registry_id = STRATEGY_REGISTRY_EVIDENCE_IDS[row.strategic_shift]
    return required_registry_id in row.evidence_ids and required_registry_id in evidence_ids


def _is_coverage_status_repair(
    original_row,
    repaired_row,
    *,
    allow_coverage_status_repair: bool,
) -> bool:
    return (
        allow_coverage_status_repair
        and original_row.status is AssessmentStatus.NOT_EVIDENCED
        and repaired_row.status in _COVERAGE_REPAIR_STATUSES
    )


def _normalize_missing_coverage_repair_row(repaired_row):
    if repaired_row.status is AssessmentStatus.NOT_ASSESSABLE:
        return repaired_row.model_copy(update={"evidence_ids": ()})
    return repaired_row


def _normalize_coverage_repair_row(
    original_row,
    repaired_row,
    *,
    original_is_evidence_safe: bool,
):
    if (
        repaired_row.status is AssessmentStatus.PARTIALLY_ALIGNED
        and not original_is_evidence_safe
    ):
        return None
    evidence_ids = (
        ()
        if repaired_row.status is AssessmentStatus.NOT_ASSESSABLE
        else original_row.evidence_ids
    )
    return repaired_row.model_copy(update={"evidence_ids": evidence_ids})


def _fallback_strategy_assessment(shift: FCVStrategicShift) -> FCVStrategyAssessment:
    return FCVStrategyAssessment(
        assessment_id=f"repair-strategy-{shift.value}",
        strategic_shift=shift,
        assessment=(
            "This strategic shift was not assessable after validation repair "
            "because a complete model-authored row was unavailable."
        ),
        status=AssessmentStatus.NOT_ASSESSABLE,
        confidence=AssessmentConfidence.LOW,
        gap_locus=None,
        evidence_ids=(),
    )


def _merge_rra_assessments(
    original_rows,
    repaired_rows,
    evidence_ids: set[str],
    *,
    allow_coverage_status_repair: bool = False,
    allow_new_rra_rows: bool = False,
):
    merged = []
    used_ids = set()
    original_ids = {row.assessment_id for row in original_rows}
    for original_row in original_rows:
        original_is_evidence_safe = _is_evidence_safe(original_row, evidence_ids)
        if (
            allow_coverage_status_repair
            and original_row.status is AssessmentStatus.NOT_EVIDENCED
        ):
            repaired_row = next(
                (
                    row
                    for row in repaired_rows
                    if row.assessment_id == original_row.assessment_id
                    and _is_evidence_safe(row, evidence_ids)
                    and _is_coverage_status_repair(
                        original_row,
                        row,
                        allow_coverage_status_repair=allow_coverage_status_repair,
                    )
                ),
                None,
            )
            normalized_repair = (
                _normalize_coverage_repair_row(
                    original_row,
                    repaired_row,
                    original_is_evidence_safe=original_is_evidence_safe,
                )
                if repaired_row is not None
                else None
            )
            if normalized_repair is not None:
                merged.append(normalized_repair)
                used_ids.add(normalized_repair.assessment_id)
                continue
            if not original_is_evidence_safe:
                used_ids.add(original_row.assessment_id)
        if original_is_evidence_safe:
            merged.append(original_row)
            used_ids.add(original_row.assessment_id)
    for repaired_row in repaired_rows:
        is_new_rra_row = repaired_row.assessment_id not in original_ids
        if (
            allow_coverage_status_repair
            and is_new_rra_row
            and not allow_new_rra_rows
        ):
            continue
        if (
            repaired_row.assessment_id not in used_ids
            and _is_evidence_safe(repaired_row, evidence_ids)
        ):
            normalized_repair = (
                _normalize_missing_coverage_repair_row(repaired_row)
                if allow_new_rra_rows and is_new_rra_row
                else repaired_row
            )
            merged.append(normalized_repair)
            used_ids.add(normalized_repair.assessment_id)
    return tuple(merged)


def _normalize_repaired_assessments(
    original: ReviewResult,
    draft: ReviewDraft,
    evidence_ids: set[str] | None,
    *,
    allow_coverage_status_repair: bool = False,
    allow_new_rra_rows: bool = False,
    allow_missing_strategy_rows: bool = False,
) -> ReviewDraft:
    allowed_evidence_ids = (
        set(evidence_ids)
        if evidence_ids is not None
        else {
            evidence_id
            for row in (
                *original.fcv_strategy_assessments,
                *draft.fcv_strategy_assessments,
                *original.rra_driver_assessments,
                *draft.rra_driver_assessments,
            )
            for evidence_id in row.evidence_ids
        }
    )
    normalized_strategy = []
    for shift in FCVStrategicShift:
        raw_original_row = next(
            (
                row
                for row in original.fcv_strategy_assessments
                if row.strategic_shift is shift
            ),
            None,
        )
        original_row = next(
            (
                row
                for row in original.fcv_strategy_assessments
                if row.strategic_shift is shift
                and _is_evidence_safe_strategy_row(row, allowed_evidence_ids)
            ),
            None,
        )
        repaired_row = next(
            (
                row
                for row in draft.fcv_strategy_assessments
                if row.strategic_shift is shift
                and _is_evidence_safe_strategy_row(row, allowed_evidence_ids)
            ),
            None,
        )
        coverage_identity_mismatch = (
            allow_coverage_status_repair
            and (
                (
                    raw_original_row is None
                    and not allow_missing_strategy_rows
                )
                or (
                    repaired_row is not None
                    and raw_original_row is not None
                    and raw_original_row.assessment_id != repaired_row.assessment_id
                )
            )
        )
        if coverage_identity_mismatch:
            normalized_strategy.append(original_row or _fallback_strategy_assessment(shift))
        elif (
            allow_missing_strategy_rows
            and raw_original_row is None
            and repaired_row is not None
        ):
            normalized_strategy.append(
                _normalize_missing_coverage_repair_row(repaired_row)
            )
        elif (
            allow_coverage_status_repair
            and raw_original_row is not None
            and raw_original_row.status is AssessmentStatus.NOT_EVIDENCED
        ):
            normalized_repair = (
                _normalize_coverage_repair_row(
                    raw_original_row,
                    repaired_row,
                    original_is_evidence_safe=original_row is not None,
                )
                if (
                    repaired_row is not None
                    and _is_coverage_status_repair(
                        raw_original_row,
                        repaired_row,
                        allow_coverage_status_repair=allow_coverage_status_repair,
                    )
                )
                else None
            )
            normalized_strategy.append(
                normalized_repair
                or original_row
                or _fallback_strategy_assessment(shift)
            )
        else:
            normalized_strategy.append(
                original_row or repaired_row or _fallback_strategy_assessment(shift)
            )
    return draft.model_copy(
        update={
            "rra_driver_assessments": _merge_rra_assessments(
                original.rra_driver_assessments,
                draft.rra_driver_assessments,
                allowed_evidence_ids,
                allow_coverage_status_repair=allow_coverage_status_repair,
                allow_new_rra_rows=allow_new_rra_rows,
            ),
            "fcv_strategy_assessments": tuple(normalized_strategy),
        }
    )





_POLICY_RRA_TEXT_FIELDS = (
    "driver",
    "cpf_response",
    "delivery_mechanism",
    "result_or_indicator",
    "remaining_gap",
)


def _clean_policy_fields(original, candidate, fields, forbidden_phrases):
    phrases = tuple(
        phrase.casefold() for phrase in forbidden_phrases if phrase.strip()
    )
    updates = {}
    for field in fields:
        original_text = getattr(original, field)
        candidate_text = getattr(candidate, field)
        if (
            any(phrase in original_text.casefold() for phrase in phrases)
            and not any(phrase in candidate_text.casefold() for phrase in phrases)
        ):
            updates[field] = candidate_text
    return original.model_copy(update=updates) if updates else original


def _preserve_cleaned_policy_assessment_text(
    normalized: ReviewDraft,
    repaired: ReviewDraft,
    forbidden_phrases: tuple[str, ...],
) -> ReviewDraft:
    repaired_rra = {row.assessment_id: row for row in repaired.rra_driver_assessments}
    rra_rows = tuple(
        _clean_policy_fields(
            row,
            repaired_rra[row.assessment_id],
            _POLICY_RRA_TEXT_FIELDS,
            forbidden_phrases,
        )
        if row.assessment_id in repaired_rra
        else row
        for row in normalized.rra_driver_assessments
    )
    repaired_strategy = {
        (row.strategic_shift, row.assessment_id): row
        for row in repaired.fcv_strategy_assessments
    }
    strategy_rows = tuple(
        _clean_policy_fields(
            row,
            repaired_strategy[(row.strategic_shift, row.assessment_id)],
            ("assessment",),
            forbidden_phrases,
        )
        if (row.strategic_shift, row.assessment_id) in repaired_strategy
        else row
        for row in normalized.fcv_strategy_assessments
    )
    return normalized.model_copy(
        update={
            "rra_driver_assessments": rra_rows,
            "fcv_strategy_assessments": strategy_rows,
        }
    )

def _document_names(evidence_pack: EvidencePack) -> dict[DocumentRole, tuple[str, ...]]:
    return {
        role: tuple(
            dict.fromkeys(
                item.locator.document_title
                for item in evidence_pack.evidence
                if item.document_role == role and item.locator is not None
            )
        )
        for role in DocumentRole
    }


class ReviewEngine:
    def __init__(self, gateway: ModelGateway):
        self.gateway = gateway

    def review(
        self,
        evidence_pack: EvidencePack,
        *,
        review_focus: str = "",
    ) -> ReviewResult:
        stage = evidence_pack.metadata.review_stage
        if stage not in STAGE_PROFILES:
            raise ValueError(f"Unsupported review stage: {stage}")
        names = _document_names(evidence_pack)
        if not names[DocumentRole.PRIMARY]:
            raise ValueError("At least one located primary document evidence item is required.")
        stage_profile = STAGE_PROFILES[stage]
        detail_profile = DETAIL_PROFILES[evidence_pack.metadata.detail_level]
        payload = {
            "evidence_pack": evidence_pack.model_dump(mode="json"),
            "stage_profile": _serialize_stage_profile(stage_profile),
            "detail_profile": _serialize_detail_profile(detail_profile),
            "review_focus": review_focus,
        }
        if _estimated_input_tokens(payload) > REVIEW_MAX_ESTIMATED_INPUT_TOKENS:
            raise PackageCoverageUnavailable(
                "Complete review request exceeds the safe request budget."
            )
        try:
            draft = self.gateway.generate(
                prompt_name="review",
                payload=payload,
                output_type=ReviewDraft,
            )
        except ValidationError as error:
            retry_payload = {
                **payload,
                "schema_retry": {"issues": _safe_schema_issues(error)},
            }
            if _estimated_input_tokens(retry_payload) > REVIEW_MAX_ESTIMATED_INPUT_TOKENS:
                raise PackageCoverageUnavailable(
                    "Complete review request exceeds the safe request budget."
                )
            try:
                draft = self.gateway.generate(
                    prompt_name="review",
                    payload=retry_payload,
                    output_type=ReviewDraft,
                )
            except ValidationError as retry_error:
                raise ReviewSchemaUnavailable(error, retry_error) from retry_error
        coverage = DocumentCoverage(
            primary_document=names[DocumentRole.PRIMARY][0],
            package_documents=names[DocumentRole.PACKAGE],
            context_documents=names[DocumentRole.CONTEXT],
            coverage_note=draft.coverage_note,
        )
        content = draft.model_dump(exclude={"coverage_note"})
        return ReviewResult(
            metadata=evidence_pack.metadata,
            document_coverage=coverage,
            **content,
        )

    def repair(
        self,
        result: ReviewResult,
        issues: list[dict],
        *,
        forbidden_phrases: tuple[str, ...] = (),
        evidence_ids: set[str] | None = None,
        evidence: Mapping[str, EvidenceItem] | None = None,
    ) -> ReviewResult:
        stage = result.metadata.review_stage
        if stage not in STAGE_PROFILES:
            raise ValueError(f"Unsupported review stage: {stage}")
        _validate_repair_issues(issues)
        stage_profile = STAGE_PROFILES[stage]
        detail_profile = DETAIL_PROFILES[result.metadata.detail_level]
        draft_payload = result.model_dump(
            mode="json",
            exclude={"metadata", "document_coverage"},
        )
        draft_payload["coverage_note"] = result.document_coverage.coverage_note
        available_evidence_ids = evidence_ids or set()
        support_evidence = evidence or {}
        current_support = [
            {
                "evidence_id": item.evidence_id,
                "publisher": (item.source_publisher or "")[:200],
                "source_title": (item.source_title or "")[:500],
                "source_date": item.source_date.isoformat(),
                "source_url": (item.source_url or "")[:2000],
                "supporting_quote": (item.supporting_quote or "")[:1500],
                "source_relevance": (item.source_relevance or "")[:1000],
                "publication_date_basis": item.publication_date_basis,
            }
            for item in sorted(
                support_evidence.values(), key=lambda candidate: candidate.evidence_id
            )
            if item.evidence_id in available_evidence_ids
            and item.evidence_type == "current_context"
            and item.source_publisher
            and item.source_title
            and item.source_date is not None
            and item.source_url
            and item.supporting_quote
        ]
        draft = self.gateway.generate(
            prompt_name="repair",
            payload={
                "draft": draft_payload,
                "validation_issues": issues,
                "forbidden_phrases": forbidden_phrases,
                "repair_support_evidence_ids": {
                    "current_context": sorted(
                        item for item in available_evidence_ids if item.startswith("current-")
                    ),
                    "registry_language": sorted(
                        item
                        for item in available_evidence_ids
                        if item.startswith("registry-") and "-PUB-FCV-STRAT-" in item
                    ),
                },
                "repair_support_evidence": current_support,
                "diagnostic_mode": result.metadata.diagnostic_mode.value,
                "review_stage": stage,
                "stage_profile": _serialize_stage_profile(stage_profile),
                "detail_profile": _serialize_detail_profile(detail_profile),
            },
            output_type=ReviewDraft,
        )
        allow_coverage_status_repair = any(
            issue["code"] == "incomplete_coverage_absence_claim"
            for issue in issues
        )
        allow_new_rra_rows = allow_coverage_status_repair and any(
            issue["code"] == "missing_rra_driver_assessment"
            for issue in issues
        )
        allow_missing_strategy_rows = allow_coverage_status_repair and any(
            issue["code"] == "incomplete_strategy_assessment"
            for issue in issues
        )
        repaired_assessments = draft
        draft = _normalize_repaired_assessments(
            result,
            draft,
            evidence_ids,
            allow_coverage_status_repair=allow_coverage_status_repair,
            allow_new_rra_rows=allow_new_rra_rows,
            allow_missing_strategy_rows=allow_missing_strategy_rows,
        )
        if any(issue["code"] == "prohibited_policy_language" for issue in issues):
            draft = _preserve_cleaned_policy_assessment_text(
                draft,
                repaired_assessments,
                forbidden_phrases,
            )
        if any(issue["code"] == "raw_evidence_id_in_narrative" for issue in issues):
            draft = _scrub_raw_evidence_ids_from_narrative(draft, available_evidence_ids)
        coverage = result.document_coverage.model_copy(
            update={"coverage_note": draft.coverage_note}
        )
        content = draft.model_dump(exclude={"coverage_note"})
        metadata = result.metadata.model_copy(update={"repair_count": 1})
        return ReviewResult(
            metadata=metadata,
            document_coverage=coverage,
            **content,
        )
