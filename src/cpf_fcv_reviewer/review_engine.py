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


def _normalize_strategy_assessments(
    draft: ReviewDraft,
    fallback_rows: tuple[FCVStrategyAssessment, ...] = (),
) -> ReviewDraft:
    rows_by_shift = {}
    for row in (*draft.fcv_strategy_assessments, *fallback_rows):
        rows_by_shift.setdefault(row.strategic_shift, row)

    normalized = tuple(
        rows_by_shift.get(shift)
        or FCVStrategyAssessment(
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
        for shift in FCVStrategicShift
    )
    return draft.model_copy(update={"fcv_strategy_assessments": normalized})




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
        draft = _normalize_strategy_assessments(
            draft,
            result.fcv_strategy_assessments,
        )
        content = draft.model_dump(exclude={"coverage_note"})
        metadata = result.metadata.model_copy(update={"repair_count": 1})
        return ReviewResult(
            metadata=metadata,
            document_coverage=coverage,
            **content,
        )
