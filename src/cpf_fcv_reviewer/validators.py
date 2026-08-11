from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import DiagnosticMode, ReviewResult

DETERMINATION_PATTERNS = (
    r"\beligible for\b",
    r"\beligibility for\b",
    r"\bis triggered\b",
    r"\bcomplies? with\b",
    r"\bcriteria are met\b",
    r"\bhas cleared\b",
    r"\bconstitutes clearance\b",
)
LIMITED_MODE_ALIGNMENT_PATTERN = re.compile(
    r"\b(?:rra(?:[-\s]+[a-z0-9]+){0,3}[-\s]+alignment|"
    r"alignment\s+with\s+(?:the\s+)?rra)\b",
    re.IGNORECASE,
)
FINALIZATION_OVERREACH_TERMS = (
    "replace all",
    "rebuild the entire",
    "redesign the whole",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def result_text(result: ReviewResult) -> str:
    """Return every user-facing review field that can carry a policy claim."""
    parts = [result.executive_judgment, result.diagnostic_title]
    for finding in result.findings:
        parts.extend((finding.title, finding.narrative))
    for recommendation in result.recommendations:
        parts.extend(
            (
                recommendation.action,
                recommendation.why_it_matters,
                recommendation.stage_behavior,
            )
        )
    for response in result.priority_question_responses:
        parts.extend((response.question, response.direct_answer))
        if response.limitation is not None:
            parts.append(response.limitation)
    return "\n".join(parts)


def assert_no_unsupported_policy_claims(text: str, prohibited_terms: set[str]) -> None:
    lowered = text.casefold()
    if any(re.search(pattern, lowered) for pattern in DETERMINATION_PATTERNS):
        raise ValueError("Unsupported policy or determination language.")
    if any(term.casefold() in lowered for term in prohibited_terms):
        raise ValueError("Unsupported policy or determination language.")


def validate_review(
    result: ReviewResult,
    *,
    evidence_ids: set[str],
    prohibited_terms: set[str],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    text = result_text(result)

    if result.metadata.diagnostic_mode == DiagnosticMode.LIMITED_FRAMING:
        if LIMITED_MODE_ALIGNMENT_PATTERN.search(text):
            issues.append(
                ValidationIssue(
                    "limited_mode_overclaim",
                    "Limited mode must not claim RRA alignment.",
                )
            )

    finding_ids = {finding.finding_id for finding in result.findings}
    for finding in result.findings:
        _append_unknown_evidence_issue(
            issues, finding.finding_id, finding.evidence_ids, evidence_ids
        )

    for recommendation in result.recommendations:
        if recommendation.finding_id not in finding_ids:
            issues.append(
                ValidationIssue(
                    "unknown_finding",
                    f"{recommendation.recommendation_id} cites unknown finding: "
                    f"{recommendation.finding_id}",
                )
            )
        if recommendation.sensitivity.value == "withhold":
            issues.append(
                ValidationIssue(
                    "withheld_drafting",
                    f"{recommendation.recommendation_id} cannot be ready-to-paste.",
                )
            )

    for response in result.priority_question_responses:
        _append_unknown_evidence_issue(
            issues, response.question_id, response.evidence_ids, evidence_ids
        )

    try:
        assert_no_unsupported_policy_claims(text, prohibited_terms)
    except ValueError as exc:
        issues.append(ValidationIssue("prohibited_policy_language", str(exc)))

    return tuple(issues)


def _append_unknown_evidence_issue(
    issues: list[ValidationIssue],
    item_id: str,
    cited_ids: tuple[str, ...],
    evidence_ids: set[str],
) -> None:
    unknown = sorted(set(cited_ids) - evidence_ids)
    if unknown:
        issues.append(
            ValidationIssue(
                "unknown_evidence",
                f"{item_id} cites unknown evidence: {unknown}",
            )
        )


def validate_stage_behavior(
    review_stage: str,
    action: str,
) -> tuple[ValidationIssue, ...]:
    if review_stage == "finalization" and any(
        term in action.casefold() for term in FINALIZATION_OVERREACH_TERMS
    ):
        return (
            ValidationIssue(
                "stage_overreach",
                "Finalization permits targeted edits, not wholesale redesign.",
            ),
        )
    return ()
