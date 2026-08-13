from datetime import UTC, datetime
from typing import get_args

import pytest

from cpf_fcv_reviewer import validators
from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    DocumentCoverage,
    EvidenceLocator,
    PriorityArea,
    RecommendationScale,
    ReviewResult,
    RevisionSummaryItem,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.review_profiles import STAGE_PROFILES
from cpf_fcv_reviewer.validators import (
    ValidationIssueCode,
    result_text,
    validate_review,
    validate_stage_behavior,
)


def metadata(*, stage: str = "finalization", mode: DiagnosticMode = DiagnosticMode.LIMITED_FRAMING):
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage=stage,
        diagnostic_mode=mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"opcs": "1.0.0-test"},
        model_id="fake",
    )


def locator(excerpt: str = "Outcome framework"):
    return EvidenceLocator(
        document_title="CPF",
        page=1,
        excerpt=excerpt,
    )


def area(
    *,
    area_id: str = "pa-1",
    scale: RecommendationScale = RecommendationScale.FINE_TUNING,
    evidence_ids: tuple[str, ...] = ("ev-1",),
    sensitivity: SensitivityCategory = SensitivityCategory.CAUTIOUS,
    comment_reference: str | None = None,
    recommended_action: str = "Clarify the causal link.",
    heading: str = "Strengthen the causal link",
    assessment: str = "The link remains implicit.",
    why_it_matters: str = "The results chain is not explicit.",
) -> PriorityArea:
    return PriorityArea(
        priority_area_id=area_id,
        heading=heading,
        assessment=assessment,
        why_it_matters=why_it_matters,
        recommended_action=recommended_action,
        target_locator=locator("SECRET RAW EVIDENCE EXCERPT"),
        recommendation_scale=scale,
        evidence_ids=evidence_ids,
        sensitivity=sensitivity,
        comment_reference=comment_reference,
    )


def result(
    *,
    stage: str = "finalization",
    mode: DiagnosticMode = DiagnosticMode.LIMITED_FRAMING,
    summaries: tuple[RevisionSummaryItem, ...] = (
        RevisionSummaryItem(priority_area_id="pa-1", action="Clarify the causal link."),
    ),
    areas: tuple[PriorityArea, ...] = (area(),),
    limitations: tuple[str, ...] = ("No current RRA was available.",),
    overall_read: str = "The CPF has a useful foundation but needs a clearer delivery narrative.",
) -> ReviewResult:
    return ReviewResult(
        metadata=metadata(stage=stage, mode=mode),
        overall_read=overall_read,
        alignment_readout="The CPF shows partial alignment with relevant FCV priorities.",
        revision_summary=summaries,
        priority_areas=areas,
        limitations=limitations,
        document_coverage=DocumentCoverage(
            primary_document="CPF",
            coverage_note="The review covers the primary CPF draft.",
        ),
    )


def test_result_text_covers_model_authored_narrative_without_metadata_or_raw_evidence():
    reviewed = result(
        summaries=(RevisionSummaryItem(priority_area_id="pa-1", action="SUMMARY ACTION"),),
        areas=(
            area(
                comment_reference="COMMENT REF",
                recommended_action="RECOMMENDED ACTION",
            ).model_copy(
                update={
                    "heading": "HEADING",
                    "assessment": "ASSESSMENT",
                    "why_it_matters": "WHY IT MATTERS",
                }
            ),
        ),
        limitations=("LIMITATION",),
        overall_read="OVERALL READ",
    )

    text = result_text(reviewed)

    for expected in (
        "OVERALL READ",
        "SUMMARY ACTION",
        "HEADING",
        "ASSESSMENT",
        "WHY IT MATTERS",
        "RECOMMENDED ACTION",
        "COMMENT REF",
        "LIMITATION",
        "The review covers the primary CPF draft.",
    ):
        assert expected in text
    assert "SECRET RAW EVIDENCE EXCERPT" not in text
    assert "app_release" not in text
    assert "registry_bundle_hash" not in text


def test_alignment_readout_prohibited_policy_language_is_rejected():
    reviewed = result().model_copy(
        update={"alignment_readout": "The CPF is eligible for expedited support."}
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms={"expedited support"},
    )

    assert [issue.code for issue in issues] == ["prohibited_policy_language"]


def test_summary_unknown_link_is_rejected():
    reviewed = result(
        summaries=(RevisionSummaryItem(priority_area_id="missing", action="Revise it."),)
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "unknown_priority_area" in {issue.code for issue in issues}


def test_duplicate_priority_ids_and_summary_linkage_are_rejected_with_repairable_code():
    reviewed = result(
        summaries=(
            RevisionSummaryItem(priority_area_id="pa-1", action="First action."),
            RevisionSummaryItem(priority_area_id="pa-1", action="Second action."),
        ),
        areas=(area(), area()),
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    unknown_area_issues = [issue for issue in issues if issue.code == "unknown_priority_area"]
    assert len(unknown_area_issues) >= 2
    assert any("Duplicate priority area IDs" in issue.message for issue in unknown_area_issues)
    assert any(
        "Duplicate revision summary linkages" in issue.message
        for issue in unknown_area_issues
    )


def test_priority_area_unknown_evidence_is_rejected():
    reviewed = result(areas=(area(evidence_ids=("ev-2", "ev-1")),))

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [issue.message for issue in issues if issue.code == "unknown_evidence"] == [
        "pa-1 cites unknown evidence: ['ev-2']"
    ]


def test_actionable_priority_requires_current_context_when_available():
    reviewed = result(areas=(area(),))

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "current-1"},
        prohibited_terms=set(),
    )

    assert [
        issue.message
        for issue in issues
        if issue.code == "missing_current_context_support"
    ] == [
        "pa-1 requires current-context evidence support."
    ]


def test_current_context_citation_satisfies_actionable_priority_support():
    reviewed = result(areas=(area(evidence_ids=("ev-1", "current-1")),))

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "current-1"},
        prohibited_terms=set(),
    )

    assert "missing_current_context_support" not in {issue.code for issue in issues}


def test_withheld_priority_is_exempt_from_current_context_support():
    reviewed = result(
        areas=(area(sensitivity=SensitivityCategory.WITHHOLD),),
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "current-1"},
        prohibited_terms=set(),
    )

    assert "missing_current_context_support" not in {issue.code for issue in issues}


def test_no_current_context_available_does_not_require_current_support():
    reviewed = result(areas=(area(),))

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "missing_current_context_support" not in {issue.code for issue in issues}


def test_explicit_fc_strategy_claim_requires_registry_evidence():
    reviewed = result(
        areas=(
            area(
                heading="FCV Strategy pillar for delivery",
                evidence_ids=("ev-1",),
            ),
        )
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "registry-1"},
        prohibited_terms=set(),
    )

    assert [issue.message for issue in issues if issue.code == "missing_registry_support"] == [
        "pa-1 makes an FCV Strategy or Strategy pillar claim without registry-language evidence."
    ]


def test_registry_evidence_satisfies_explicit_fc_strategy_claim():
    reviewed = result(
        areas=(
            area(
                assessment="The FCV Strategy is reflected in the delivery approach.",
                evidence_ids=("ev-1", "registry-1"),
            ),
        )
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "registry-1"},
        prohibited_terms=set(),
    )

    assert "missing_registry_support" not in {issue.code for issue in issues}


def test_generic_strategy_language_does_not_require_registry_evidence():
    reviewed = result(
        areas=(area(heading="Strengthen the strategy"),),
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1", "registry-1"},
        prohibited_terms=set(),
    )

    assert "missing_registry_support" not in {issue.code for issue in issues}


def test_integrated_support_issue_codes_are_declared_in_validation_code_type():
    declared_codes = set(get_args(ValidationIssueCode))

    assert {"missing_current_context_support", "missing_registry_support"} <= declared_codes


def test_finalization_requires_fine_tuning_scale():
    reviewed = result(areas=(area(scale=RecommendationScale.TARGETED_EDIT),))

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "stage_overreach" in {issue.code for issue in issues}


@pytest.mark.parametrize(
    ("stage", "scale"),
    [
        ("early_drafting", RecommendationScale.TARGETED_EDIT),
        ("decision_review", RecommendationScale.SUBSTANTIVE_REVISION),
        ("finalization", RecommendationScale.FINE_TUNING),
    ],
)
def test_known_stage_recommended_action_uses_profile_word_limit(stage, scale):
    limit = STAGE_PROFILES[stage].max_immediate_insertion_words

    for word_count, expected in ((limit, False), (limit + 1, True)):
        action = " ".join(f"word-{index}" for index in range(word_count))
        issues = validate_stage_behavior(stage, action, scale)

        assert ("stage_length_overreach" in {issue.code for issue in issues}) is expected


def test_early_drafting_accumulates_scale_and_length_violations():
    action = " ".join(f"word-{index}" for index in range(81))

    issues = validate_stage_behavior(
        "early_drafting",
        action,
        RecommendationScale.SUBSTANTIVE_REVISION,
    )

    assert {issue.code for issue in issues} == {
        "stage_overreach",
        "stage_length_overreach",
    }


def test_finalization_preserves_wholesale_redesign_guard_with_valid_length():
    issues = validate_stage_behavior(
        "finalization",
        "Replace all outcome areas.",
        RecommendationScale.FINE_TUNING,
    )

    assert [issue.code for issue in issues] == ["stage_overreach"]


def test_later_stages_use_their_own_profile_length_limits():
    action = " ".join(f"word-{index}" for index in range(141))
    issues = validate_stage_behavior(
        "decision_review",
        action,
        RecommendationScale.SUBSTANTIVE_REVISION,
    )

    assert "stage_length_overreach" in {issue.code for issue in issues}


def test_response_to_comments_requires_comment_reference():
    reviewed = result(
        stage="response_to_comments",
        areas=(area(scale=RecommendationScale.COMMENT_RESPONSE),),
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "missing_comment_reference" in {issue.code for issue in issues}


def test_withheld_narrative_is_not_ready_to_draft():
    reviewed = result(areas=(area(sensitivity=SensitivityCategory.WITHHOLD),))

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "withheld_drafting" in {issue.code for issue in issues}


def test_unknown_evidence_and_alignment_claim_fail():
    reviewed = result(
        overall_read="The CPF review claims RRA alignment.",
        areas=(area(evidence_ids=("missing",)),),
    )

    issues = validate_review(reviewed, evidence_ids=set(), prohibited_terms={"implicit"})

    assert {issue.code for issue in issues} == {
        "limited_mode_overclaim",
        "unknown_evidence",
        "prohibited_policy_language",
    }


def test_finalization_rejects_wholesale_redesign():
    issues = validate_stage_behavior(
        "finalization",
        "Replace all CPF outcome areas and rebuild the entire theory of change.",
    )

    assert issues[0].code == "stage_overreach"


def test_repair_can_receive_exact_forbidden_phrases_without_source_content():
    assert hasattr(validators, "matched_prohibited_policy_phrases")
    matches = validators.matched_prohibited_policy_phrases(
        "The draft complies with an internal threshold.",
        {"internal threshold"},
    )

    assert matches == ("complies with", "internal threshold")


def test_registry_only_prohibited_phrase_is_rejected():
    with pytest.raises(ValueError, match="Unsupported policy"):
        validators.assert_no_unsupported_policy_claims(
            "The draft relies on an internal threshold.",
            {"internal threshold"},
        )


def test_priority_question_validation_was_removed():
    assert not hasattr(validators, "validate_priority_questions")
