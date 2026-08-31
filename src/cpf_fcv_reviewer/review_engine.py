from __future__ import annotations

import re

from pydantic import ValidationError

from .contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DocumentCoverage,
    DocumentRole,
    EvidencePack,
    FCVStrategicShift,
    FCVStrategyAssessment,
    ReviewDraft,
    ReviewResult,
)
from .model_gateway import ModelGateway
from .review_profiles import DETAIL_PROFILES, STAGE_PROFILES

REPAIRABLE_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "limited_mode_overclaim",
        "missing_current_context_support",
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


def _safe_schema_issues(error: ValidationError) -> list[dict[str, object]]:
    issues = []
    for item in error.errors(
        include_url=False,
        include_context=False,
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
        if not re.fullmatch(r"[a-z0-9_]{1,64}", issue_type):
            issue_type = "validation_error"
        issues.append({"loc": location, "type": issue_type})
    return issues


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
        try:
            draft = self.gateway.generate(
                prompt_name="review",
                payload=payload,
                output_type=ReviewDraft,
            )
        except ValidationError as error:
            draft = self.gateway.generate(
                prompt_name="review",
                payload={
                    **payload,
                    "schema_retry": {"issues": _safe_schema_issues(error)},
                },
                output_type=ReviewDraft,
            )
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
        draft = _normalize_repaired_assessments(
            result,
            draft,
            evidence_ids,
            allow_coverage_status_repair=allow_coverage_status_repair,
            allow_new_rra_rows=allow_new_rra_rows,
            allow_missing_strategy_rows=allow_missing_strategy_rows,
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
