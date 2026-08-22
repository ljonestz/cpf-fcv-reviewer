from __future__ import annotations

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
        "unknown_assessment_evidence",
        "missing_rra_driver_assessment",
        "incomplete_strategy_assessment",
        "missing_registry_support",
        "stage_overreach",
        "stage_length_overreach",
        "missing_comment_reference",
        "prohibited_policy_language",
        "withheld_drafting",
    }
)


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


STRATEGY_REGISTRY_EVIDENCE_IDS = {
    shift: f"registry-PUB-FCV-STRAT-{index:03d}"
    for index, shift in enumerate(FCVStrategicShift, start=1)
}


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
):
    safe_repaired = {
        row.assessment_id: row
        for row in repaired_rows
        if _is_evidence_safe(row, evidence_ids)
    }
    merged = []
    used_ids = set()
    for original_row in original_rows:
        repaired_row = safe_repaired.get(original_row.assessment_id)
        if repaired_row is not None:
            merged.append(repaired_row)
            used_ids.add(repaired_row.assessment_id)
        elif _is_evidence_safe(original_row, evidence_ids):
            merged.append(original_row)
            used_ids.add(original_row.assessment_id)
    for repaired_row in repaired_rows:
        if (
            repaired_row.assessment_id not in used_ids
            and _is_evidence_safe(repaired_row, evidence_ids)
        ):
            merged.append(repaired_row)
            used_ids.add(repaired_row.assessment_id)
    return tuple(merged)


def _normalize_repaired_assessments(
    original: ReviewResult,
    draft: ReviewDraft,
    evidence_ids: set[str] | None,
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
        normalized_strategy.append(original_row or repaired_row or _fallback_strategy_assessment(shift))
    return draft.model_copy(
        update={
            "rra_driver_assessments": _merge_rra_assessments(
                original.rra_driver_assessments,
                draft.rra_driver_assessments,
                allowed_evidence_ids,
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
        draft = self.gateway.generate(
            prompt_name="review",
            payload={
                "evidence_pack": evidence_pack.model_dump(mode="json"),
                "stage_profile": _serialize_stage_profile(stage_profile),
                "detail_profile": _serialize_detail_profile(detail_profile),
                "review_focus": review_focus,
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
        draft = self.gateway.generate(
            prompt_name="repair",
            payload={
                "draft": draft_payload,
                "validation_issues": issues,
                "forbidden_phrases": forbidden_phrases,
                "diagnostic_mode": result.metadata.diagnostic_mode.value,
                "review_stage": stage,
                "stage_profile": _serialize_stage_profile(stage_profile),
                "detail_profile": _serialize_detail_profile(detail_profile),
            },
            output_type=ReviewDraft,
        )
        coverage = result.document_coverage.model_copy(
            update={"coverage_note": draft.coverage_note}
        )
        draft = _normalize_repaired_assessments(result, draft, evidence_ids)
        content = draft.model_dump(exclude={"coverage_note"})
        metadata = result.metadata.model_copy(update={"repair_count": 1})
        return ReviewResult(
            metadata=metadata,
            document_coverage=coverage,
            **content,
        )
