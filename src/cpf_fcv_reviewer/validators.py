from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from .contracts import (
    AssessmentStatus,
    DiagnosticMode,
    DocumentRole,
    FCVStrategicShift,
    RecommendationScale,
    ReviewResult,
    RunMetadata,
)
from .review_profiles import STAGE_PROFILES

DETERMINATION_PATTERNS = (
    r"\beligible for\b",
    r"\beligibility for\b",
    r"\bis triggered\b",
    r"\bcomplies? with\b",
    r"\bcriteria are met\b",
    r"\bhas cleared\b",
    r"\bconstitutes clearance\b",
    r"\bis(?:\s+not|n't)?(?:\s+listed)?\s+on\s+(?:the\s+)?"
    r"(?:world\s+bank(?:\s+group)?\s+)?(?:fcv\s+list|list\s+of\s+"
    r"fcv(?:-affected)?\s+countries)\b",
)
LIMITED_MODE_ALIGNMENT_PATTERN = re.compile(
    r"\b(?:rra(?:[-\s]+[a-z0-9]+){0,3}[-\s]+alignment|"
    r"alignment\s+with\s+(?:the\s+)?rra)\b",
    re.IGNORECASE,
)
LIMITED_MODE_ABSTENTION_PATTERN = re.compile(
    rf"(?:{LIMITED_MODE_ALIGNMENT_PATTERN.pattern}\s+"
    r"(?:(?:was|is)\s+not|cannot|could\s+not)\s+(?:be\s+)?"
    r"(?:assessed|evaluated|rated)\b|(?:does|did)\s+not\s+"
    rf"(?:assess|evaluate|rate)\s+{LIMITED_MODE_ALIGNMENT_PATTERN.pattern})",
    re.IGNORECASE,
)
FINALIZATION_OVERREACH_TERMS = (
    "replace all",
    "rebuild the entire",
    "redesign the whole",
)
FINALIZATION_COMMITMENT_SUBJECT_PATTERN = (
    r"(?:world bank group|wbg|world bank|bank|government|cpf|"
    r"implementing partners?)"
)
FINALIZATION_FINANCIAL_TARGET_PATTERN = (
    r"(?:(?:the\s+)?project\s+)?"
    r"(?:financing|funding|disbursements?|support)"
)
FINALIZATION_ARCHITECTURE_NOUN_PATTERN = (
    r"(?:"
    r"(?:delivery|institutional|coordination)\s+"
    r"(?:unit|mechanism|architecture|platform|system|arrangement|body)|"
    r"architecture)"
)
FINALIZATION_NEW_ARCHITECTURE_CONTENT_PATTERN = re.compile(
    rf"(?:(?:a|an|the)\s+)?(?:[a-z-]+\s+)?new\s+"
    rf"{FINALIZATION_ARCHITECTURE_NOUN_PATTERN}\b",
    re.IGNORECASE,
)
FINALIZATION_FINANCIAL_CONTENT_PATTERN = re.compile(
    rf"(?:{FINALIZATION_FINANCIAL_TARGET_PATTERN}\s+"
    rf"(?:conditional|contingent)\s+(?:on|upon)\b|"
    rf"(?:condition|conditioning)\s+{FINALIZATION_FINANCIAL_TARGET_PATTERN}\s+"
    rf"(?:on|upon)\b|"
    rf"(?:tie|ties)\s+{FINALIZATION_FINANCIAL_TARGET_PATTERN}\s+to\b)",
    re.IGNORECASE,
)
FINALIZATION_NAMED_COMMITMENT_CONTENT_PATTERN = re.compile(
    rf"(?:(?:the\s+)?{FINALIZATION_COMMITMENT_SUBJECT_PATTERN}\s+commits?\s+to|"
    rf"commit\s+(?:the\s+)?{FINALIZATION_COMMITMENT_SUBJECT_PATTERN}\s+to)\s+"
    rf"(?:(?:a|an|the)\s+)?(?:[a-z-]+\s+)?new\s+"
    rf"(?:facility|architecture)\b",
    re.IGNORECASE,
)
FINALIZATION_COMMITMENT_CONTENT_PATTERN = re.compile(
    r"(?:new\s+(?:binding\s+)?commitments?\b|"
    r"new\s+reporting\s+(?:obligations?|requirements?)\b|"
    r"publish\s+(?:quarterly\s+)?reports?\b)",
    re.IGNORECASE,
)
FINALIZATION_PRESCRIPTIVE_OPENING_PATTERN = re.compile(
    rf"^\s*(?:(?:(?:the\s+)?(?:draft|cpf)\s+should\s+)?(?:"
    rf"(?:make|condition|tie|introduce|design|create|establish|build|develop|"
    rf"set\s+up|launch|put\s+in\s+place|commit|bind|add)\b|"
    rf"revise\s+the\s+cpf\s+to\b|"
    rf"add\s+(?:wording\s+that|a\s+sentence)\b|"
    rf"(?:require|mandate)\s+(?:the\s+)?{FINALIZATION_COMMITMENT_SUBJECT_PATTERN}\s+to\b)|"
    rf"(?:the\s+)?{FINALIZATION_COMMITMENT_SUBJECT_PATTERN}\s+commits?\s+to\b"
    rf")",
    re.IGNORECASE,
)
FINALIZATION_CONTENT_PATTERNS = (
    FINALIZATION_NEW_ARCHITECTURE_CONTENT_PATTERN,
    FINALIZATION_FINANCIAL_CONTENT_PATTERN,
    FINALIZATION_NAMED_COMMITMENT_CONTENT_PATTERN,
    FINALIZATION_COMMITMENT_CONTENT_PATTERN,
)

SUMMARY_TITLE_LOCATOR_PATTERN = re.compile(
    r"\b(?:pages?|p\.?|pp\.?|sections?|paras?|paragraphs?)\s*"
    r"(?:no\.?\s*)?\d+(?:\.\d+)*(?:\s*[-–]\s*\d+(?:\.\d+)*)?\b",
    re.IGNORECASE,
)
SUMMARY_TITLE_DRAFTING_INSTRUCTION_PATTERN = re.compile(
    r"\b\d+\s+(?:short\s+)?sentences?\b|\b(?:in|under)\s+the\s+[\w -]{1,60}\s+section\b",
    re.IGNORECASE,
)
STRATEGY_REGISTRY_EVIDENCE_IDS = {
    shift: f"registry-PUB-FCV-STRAT-{index:03d}"
    for index, shift in enumerate(FCVStrategicShift, start=1)
}



@dataclass(frozen=True)
class ValidationIssue:
    code: ValidationIssueCode
    message: str


ValidationIssueCode = Literal[
    "incomplete_reproducibility_metadata",
    "limited_mode_overclaim",
    "unknown_priority_area",
    "unknown_evidence",
    "invalid_revision_summary_title",
    "unknown_assessment_evidence",
    "missing_rra_driver_assessment",
    "incomplete_strategy_assessment",
    "stage_overreach",
    "stage_length_overreach",
    "withheld_drafting",
    "missing_comment_reference",
    "missing_current_context_support",
    "missing_registry_support",
    "raw_evidence_id_in_narrative",
    "unknown_institutional_referral",
    "incomplete_coverage_absence_claim",
    "prohibited_policy_language",
]


def validate_reproducibility_metadata(
    metadata: RunMetadata,
) -> tuple[ValidationIssue, ...]:
    def is_sha256(value: str) -> bool:
        return len(value) == 64 and all(character in "0123456789abcdef" for character in value)

    invalid: list[str] = []
    source_scan_at = metadata.source_scan_at
    if (
        source_scan_at is None
        or source_scan_at.tzinfo is None
        or source_scan_at.utcoffset() is None
    ):
        invalid.append("source_scan_at")
    if not metadata.document_fingerprints or any(
        not is_sha256(value) for value in metadata.document_fingerprints.values()
    ):
        invalid.append("document_fingerprints")
    if not is_sha256(metadata.registry_bundle_hash):
        invalid.append("registry_bundle_hash")
    if not is_sha256(metadata.guidance_hash):
        invalid.append("guidance_hash")
    if not metadata.prompt_hashes or any(
        not is_sha256(value) for value in metadata.prompt_hashes.values()
    ):
        invalid.append("prompt_hashes")
    if not invalid:
        return ()
    return (
        ValidationIssue(
            "incomplete_reproducibility_metadata",
            f"Missing or invalid reproducibility fields: {', '.join(invalid)}",
        ),
    )


def result_text(result: ReviewResult) -> str:
    """Return every user-facing review field that can carry a policy claim."""
    parts = [result.overall_read, result.alignment_readout, result.strategy_readout]
    parts.extend(summary.title for summary in result.revision_summary)
    for assessment in result.rra_driver_assessments:
        parts.extend(
            (
                assessment.driver,
                assessment.cpf_response,
                assessment.delivery_mechanism,
                assessment.result_or_indicator,
                assessment.remaining_gap,
            )
        )
    parts.extend(assessment.assessment for assessment in result.fcv_strategy_assessments)
    for priority_area in result.priority_areas:
        parts.extend(
            (
                priority_area.heading,
                priority_area.assessment,
                priority_area.why_it_matters,
                priority_area.recommended_action,
            )
        )
        if priority_area.comment_reference is not None:
            parts.append(priority_area.comment_reference)
    parts.extend(result.limitations)
    parts.append(result.document_coverage.coverage_note)
    return "\n".join(parts)


def assert_no_unsupported_policy_claims(text: str, prohibited_terms: set[str]) -> None:
    lowered = text.casefold()
    if any(re.search(pattern, lowered) for pattern in DETERMINATION_PATTERNS):
        raise ValueError("Unsupported policy or determination language.")
    if any(term.casefold() in lowered for term in prohibited_terms):
        raise ValueError("Unsupported policy or determination language.")


def matched_prohibited_policy_phrases(
    text: str,
    prohibited_terms: set[str],
) -> tuple[str, ...]:
    """Return only forbidden phrases present in model-authored review text."""
    lowered = text.casefold()
    matches = [
        match.group(0)
        for pattern in DETERMINATION_PATTERNS
        for match in re.finditer(pattern, lowered)
    ]
    matches.extend(
        term.casefold()
        for term in sorted(prohibited_terms, key=str.casefold)
        if term.casefold() in lowered
    )
    return tuple(dict.fromkeys(matches))


def validate_review(
    result: ReviewResult,
    *,
    evidence_ids: set[str],
    prohibited_terms: set[str],
    incomplete_document_roles: set[DocumentRole] | frozenset[DocumentRole] = frozenset(),
    registry_entry_ids: set[str] | None = None,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    text = result_text(result)
    _append_raw_evidence_id_issue(issues, text, evidence_ids)
    if registry_entry_ids is not None:
        _append_unknown_institutional_referral_issue(
            issues,
            result.institutional_referral_ids,
            registry_entry_ids,
        )
    incomplete_optional_roles = frozenset(incomplete_document_roles) & {
        DocumentRole.PACKAGE,
        DocumentRole.CONTEXT,
    }

    if result.metadata.diagnostic_mode == DiagnosticMode.LIMITED_FRAMING:
        text_without_abstentions = LIMITED_MODE_ABSTENTION_PATTERN.sub("", text)
        if LIMITED_MODE_ALIGNMENT_PATTERN.search(text_without_abstentions):
            issues.append(
                ValidationIssue(
                    "limited_mode_overclaim",
                    "Limited mode must not claim RRA alignment.",
                )
            )

    if (
        result.metadata.diagnostic_mode == DiagnosticMode.RRA_ALIGNMENT
        and not result.rra_driver_assessments
    ):
        issues.append(
            ValidationIssue(
                "missing_rra_driver_assessment",
                "RRA alignment mode requires at least one RRA driver assessment.",
            )
        )

    shift_counts = Counter(
        assessment.strategic_shift
        for assessment in result.fcv_strategy_assessments
    )
    missing_shifts = [
        shift.value for shift in FCVStrategicShift if shift_counts[shift] == 0
    ]
    duplicate_shifts = [
        shift.value for shift in FCVStrategicShift if shift_counts[shift] > 1
    ]
    if missing_shifts or duplicate_shifts:
        issues.append(
            ValidationIssue(
                "incomplete_strategy_assessment",
                "FCV Strategy assessment requires each strategic shift exactly once; "
                f"missing={missing_shifts}, duplicate={duplicate_shifts}.",
            )
        )

    for assessment in result.rra_driver_assessments:
        _append_unknown_evidence_issue(
            issues,
            assessment.assessment_id,
            assessment.evidence_ids,
            evidence_ids,
            issue_code="unknown_assessment_evidence",
        )
        _append_incomplete_coverage_absence_issue(
            issues,
            assessment.assessment_id,
            assessment.status,
            incomplete_optional_roles,
        )

    for assessment in result.fcv_strategy_assessments:
        _append_unknown_evidence_issue(
            issues,
            assessment.assessment_id,
            assessment.evidence_ids,
            evidence_ids,
            issue_code="unknown_assessment_evidence",
        )
        _append_incomplete_coverage_absence_issue(
            issues,
            assessment.assessment_id,
            assessment.status,
            incomplete_optional_roles,
        )
        if assessment.status is not AssessmentStatus.NOT_ASSESSABLE:
            required_registry_id = STRATEGY_REGISTRY_EVIDENCE_IDS[
                assessment.strategic_shift
            ]
            if required_registry_id not in set(assessment.evidence_ids) & evidence_ids:
                issues.append(
                    ValidationIssue(
                        "incomplete_strategy_assessment",
                        f"{assessment.assessment_id} requires shift-specific FCV Strategy "
                        f"registry evidence: {required_registry_id}.",
                    )
                )

    priority_area_counts = Counter(
        priority_area.priority_area_id for priority_area in result.priority_areas
    )
    duplicate_priority_area_ids = sorted(
        area_id for area_id, count in priority_area_counts.items() if count > 1
    )
    if duplicate_priority_area_ids:
        issues.append(
            ValidationIssue(
                "unknown_priority_area",
                f"Duplicate priority area IDs: {duplicate_priority_area_ids}",
            )
        )

    summary_link_counts = Counter(
        summary.priority_area_id for summary in result.revision_summary
    )
    duplicate_summary_links = sorted(
        area_id for area_id, count in summary_link_counts.items() if count > 1
    )
    if duplicate_summary_links:
        issues.append(
            ValidationIssue(
                "unknown_priority_area",
                f"Duplicate revision summary linkages: {duplicate_summary_links}",
            )
        )

    summary_priority_area_ids = tuple(
        summary.priority_area_id for summary in result.revision_summary
    )
    priority_area_ids = tuple(
        priority_area.priority_area_id for priority_area in result.priority_areas
    )
    if summary_priority_area_ids != priority_area_ids:
        issues.append(
            ValidationIssue(
                "unknown_priority_area",
                "revision_summary priority_area_id order must exactly match "
                "priority_areas order.",
            )
        )

    for summary in result.revision_summary:
        if priority_area_counts.get(summary.priority_area_id, 0) != 1:
            issues.append(
                ValidationIssue(
                    "unknown_priority_area",
                    f"Revision summary title cites priority area that does not resolve uniquely: "
                    f"{summary.priority_area_id}",
                )
            )
        _append_invalid_summary_title_issue(issues, summary, evidence_ids)

    for priority_area in result.priority_areas:
        _append_unknown_evidence_issue(
            issues,
            priority_area.priority_area_id,
            priority_area.evidence_ids,
            evidence_ids,
        )
        if priority_area.sensitivity.value != "withhold":
            _append_missing_current_context_issue(
                issues,
                priority_area.priority_area_id,
                priority_area.evidence_ids,
                evidence_ids,
            )
        _append_missing_registry_issue(
            issues,
            priority_area.priority_area_id,
            priority_area,
            evidence_ids,
        )
        issues.extend(
            validate_stage_behavior(
                result.metadata.review_stage,
                priority_area.recommended_action,
                priority_area.recommendation_scale,
                priority_area_id=priority_area.priority_area_id,
            )
        )
        if priority_area.sensitivity.value == "withhold":
            issues.append(
                ValidationIssue(
                    "withheld_drafting",
                    f"{priority_area.priority_area_id} cannot be ready-to-paste.",
                )
            )
        if result.metadata.review_stage == "response_to_comments" and not (
            priority_area.comment_reference and priority_area.comment_reference.strip()
        ):
            issues.append(
                ValidationIssue(
                    "missing_comment_reference",
                    f"{priority_area.priority_area_id} requires a comment reference.",
                )
            )

    try:
        assert_no_unsupported_policy_claims(text, prohibited_terms)
    except ValueError as exc:
        issues.append(ValidationIssue("prohibited_policy_language", str(exc)))

    return tuple(issues)


def _append_raw_evidence_id_issue(
    issues: list[ValidationIssue], text: str, evidence_ids: set[str]
) -> None:
    raw_ids = sorted(
        evidence_id
        for evidence_id in evidence_ids
        if evidence_id
        and (
            re.search(r"[-_]\d", evidence_id)
            or evidence_id.casefold().startswith("correction-")
        )
        and re.search(
            rf"(?<![A-Za-z0-9_-]){re.escape(evidence_id)}(?![A-Za-z0-9_-])",
            text,
            re.IGNORECASE,
        )
    )
    if raw_ids:
        issues.append(
            ValidationIssue(
                "raw_evidence_id_in_narrative",
                f"User-facing narrative must not include raw evidence IDs: {raw_ids}.",
            )
        )


def _append_unknown_institutional_referral_issue(
    issues: list[ValidationIssue],
    cited_ids: tuple[str, ...],
    registry_entry_ids: set[str],
) -> None:
    unknown = sorted(set(cited_ids) - registry_entry_ids)
    if unknown:
        issues.append(
            ValidationIssue(
                "unknown_institutional_referral",
                f"institutional_referral_ids cite unknown registry entries: {unknown}",
            )
        )


def _append_incomplete_coverage_absence_issue(
    issues: list[ValidationIssue],
    item_id: str,
    status: AssessmentStatus,
    incomplete_optional_roles: frozenset[DocumentRole],
) -> None:
    if status is not AssessmentStatus.NOT_EVIDENCED or not incomplete_optional_roles:
        return
    role_names = ", ".join(
        role.value
        for role in sorted(incomplete_optional_roles, key=lambda item: item.value)
    )
    issues.append(
        ValidationIssue(
            "incomplete_coverage_absence_claim",
            f"{item_id} is marked not_evidenced while optional {role_names} coverage "
            "is incomplete; use not_assessable, or partially_aligned when supplied "
            "evidence shows relevant but scattered or weakly operationalized content.",
        )
    )


def _append_unknown_evidence_issue(
    issues: list[ValidationIssue],
    item_id: str,
    cited_ids: tuple[str, ...],
    evidence_ids: set[str],
    *,
    issue_code: ValidationIssueCode = "unknown_evidence",
) -> None:
    unknown = sorted(set(cited_ids) - evidence_ids)
    if unknown:
        issues.append(
            ValidationIssue(
                issue_code,
                f"{item_id} cites unknown evidence: {unknown}",
            )
        )


def _append_invalid_summary_title_issue(
    issues: list[ValidationIssue],
    summary,
    evidence_ids: set[str],
) -> None:
    title = summary.title.casefold()
    raw_ids = sorted(
        evidence_id
        for evidence_id in evidence_ids
        if (
            evidence_id
            and re.search(r"[-_]\d", evidence_id)
            and evidence_id.casefold() in title
        )
    )
    if raw_ids:
        message = (
            f"{summary.priority_area_id} revision summary title must not include raw "
            f"evidence IDs: {raw_ids}."
        )
    elif SUMMARY_TITLE_LOCATOR_PATTERN.search(summary.title):
        message = (
            f"{summary.priority_area_id} revision summary title must not include "
            "page, section, or paragraph locators."
        )
    elif SUMMARY_TITLE_DRAFTING_INSTRUCTION_PATTERN.search(summary.title):
        message = (
            f"{summary.priority_area_id} revision summary title must be thematic, "
            "not a sentence-count or section-placement instruction."
        )
    else:
        return
    issues.append(ValidationIssue("invalid_revision_summary_title", message))


def _has_finalization_binding_overreach(action: str) -> bool:
    if FINALIZATION_PRESCRIPTIVE_OPENING_PATTERN.match(action) is None:
        return False
    return any(pattern.search(action) for pattern in FINALIZATION_CONTENT_PATTERNS)


def validate_stage_behavior(
    review_stage: str,
    action: str,
    recommendation_scale: RecommendationScale | None = None,
    *,
    priority_area_id: str | None = None,
) -> tuple[ValidationIssue, ...]:
    profile = STAGE_PROFILES.get(review_stage)
    issues: list[ValidationIssue] = []
    if profile is not None and recommendation_scale not in (None, *profile.allowed_scales):
        issues.append(
            ValidationIssue(
                "stage_overreach",
                f"{recommendation_scale.value} is not allowed at {review_stage} stage.",
            )
        )
    if profile is not None and len(action.split()) > profile.max_immediate_insertion_words:
        word_count = len(action.split())
        target = priority_area_id or "Priority area"
        issues.append(
            ValidationIssue(
                "stage_length_overreach",
                f"{target} recommended_action has {word_count} whitespace-separated words; "
                f"{review_stage} allows at most {profile.max_immediate_insertion_words}.",
            )
        )
    if review_stage == "finalization" and any(
        term in action.casefold() for term in FINALIZATION_OVERREACH_TERMS
    ):
        issues.append(
            ValidationIssue(
                "stage_overreach",
                "Finalization permits targeted edits, not wholesale redesign.",
            )
        )
    if review_stage == "finalization" and _has_finalization_binding_overreach(
        action
    ):
        issues.append(
            ValidationIssue(
                "stage_overreach",
                "Finalization actions must stay within existing commitments and architecture.",
            )
        )
    return tuple(issues)


def _append_missing_current_context_issue(
    issues: list[ValidationIssue],
    item_id: str,
    cited_ids: tuple[str, ...],
    evidence_ids: set[str],
) -> None:
    available_current_ids = {
        evidence_id for evidence_id in evidence_ids if evidence_id.startswith("current-")
    }
    if available_current_ids and available_current_ids.isdisjoint(cited_ids):
        issues.append(
            ValidationIssue(
                "missing_current_context_support",
                f"{item_id} requires current-context evidence support.",
            )
        )


def _append_missing_registry_issue(
    issues: list[ValidationIssue],
    item_id: str,
    priority_area,
    evidence_ids: set[str],
) -> None:
    authored_text = " ".join(
        (
            priority_area.heading,
            priority_area.assessment,
            priority_area.why_it_matters,
            priority_area.recommended_action,
        )
    ).casefold()
    if not ("fcv strategy" in authored_text or "strategy pillar" in authored_text):
        return
    available_registry_ids = {
        evidence_id for evidence_id in evidence_ids if evidence_id.startswith("registry-")
    }
    if available_registry_ids.isdisjoint(priority_area.evidence_ids):
        issues.append(
            ValidationIssue(
                "missing_registry_support",
                f"{item_id} makes an FCV Strategy or Strategy pillar claim without "
                "registry-language evidence.",
            )
        )
