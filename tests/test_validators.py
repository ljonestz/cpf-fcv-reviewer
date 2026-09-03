from datetime import UTC, datetime
from typing import get_args

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer import validators
from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DiagnosticMode,
    DocumentCoverage,
    DocumentRole,
    EvidenceLocator,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RecommendationScale,
    RRADriverAssessment,
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
        gap_locus=GapLocus.CPF_NARRATIVE,
        comment_reference=comment_reference,
    )


def strategy_rows(
    *,
    status: AssessmentStatus = AssessmentStatus.NOT_ASSESSABLE,
    evidence_ids: tuple[str, ...] = (),
    assessment_prefix: str = "Strategy assessment",
) -> tuple[FCVStrategyAssessment, ...]:
    return tuple(
        FCVStrategyAssessment(
            assessment_id=f"strategy-{strategic_shift.value}",
            strategic_shift=strategic_shift,
            assessment=f"{assessment_prefix} {strategic_shift.value}.",
            status=status,
            confidence=AssessmentConfidence.MEDIUM,
            gap_locus=(
                GapLocus.CPF_NARRATIVE
                if status
                in {AssessmentStatus.PARTIALLY_ALIGNED, AssessmentStatus.NOT_EVIDENCED}
                else None
            ),
            evidence_ids=evidence_ids,
        )
        for strategic_shift in FCVStrategicShift
    )


def rra_row(
    *,
    evidence_ids: tuple[str, ...] = ("ev-1",),
    assessment_prefix: str = "RRA assessment",
) -> RRADriverAssessment:
    return RRADriverAssessment(
        assessment_id="rra-1",
        driver=f"{assessment_prefix} driver",
        cpf_response=f"{assessment_prefix} CPF response",
        delivery_mechanism=f"{assessment_prefix} delivery mechanism",
        result_or_indicator=f"{assessment_prefix} result or indicator",
        remaining_gap=f"{assessment_prefix} remaining gap",
        status=AssessmentStatus.ALIGNED,
        confidence=AssessmentConfidence.MEDIUM,
        evidence_ids=evidence_ids,
    )


def result(
    *,
    stage: str = "finalization",
    mode: DiagnosticMode = DiagnosticMode.LIMITED_FRAMING,
    summaries: tuple[RevisionSummaryItem, ...] = (
        RevisionSummaryItem(priority_area_id="pa-1", title="Clarify the causal link."),
    ),
    areas: tuple[PriorityArea, ...] = (area(),),
    rra_assessments: tuple[RRADriverAssessment, ...] = (),
    strategy_assessments_override: tuple[FCVStrategyAssessment, ...] | None = None,
    limitations: tuple[str, ...] = ("No current RRA was available.",),
    overall_read: str = "The CPF has a useful foundation but needs a clearer delivery narrative.",
    strategy_readout: str = (
        "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
    ),
) -> ReviewResult:
    return ReviewResult(
        metadata=metadata(stage=stage, mode=mode),
        overall_read=overall_read,
        alignment_readout="The CPF shows partial alignment with relevant FCV priorities.",
        strategy_readout=strategy_readout,
        revision_summary=summaries,
        priority_areas=areas,
        rra_driver_assessments=rra_assessments,
        fcv_strategy_assessments=(
            strategy_rows()
            if strategy_assessments_override is None
            else strategy_assessments_override
        ),
        limitations=limitations,
        document_coverage=DocumentCoverage(
            primary_document="CPF",
            coverage_note="The review covers the primary CPF draft.",
        ),
    )


def test_result_text_covers_model_authored_narrative_without_metadata_or_raw_evidence():
    reviewed = result(
        summaries=(RevisionSummaryItem(priority_area_id="pa-1", title="SUMMARY TITLE"),),
        rra_assessments=(rra_row(assessment_prefix="RRA NARRATIVE"),),
        strategy_assessments_override=strategy_rows(
            assessment_prefix="STRATEGY NARRATIVE"
        ),
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
        "SUMMARY TITLE",
        "RRA NARRATIVE driver",
        "RRA NARRATIVE remaining gap",
        "STRATEGY NARRATIVE anticipate_better.",
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


def test_strategy_readout_prohibited_policy_language_is_rejected():
    reviewed = result().model_copy(
        update={"strategy_readout": "The CPF is eligible for expedited support."}
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms={"expedited support"},
    )

    assert [issue.code for issue in issues] == ["prohibited_policy_language"]


def test_supplied_evidence_ids_are_structured_not_user_facing_narrative():
    baseline = validate_review(result(), evidence_ids={"ev-1"}, prohibited_terms=set())
    assert "raw_evidence_id_in_narrative" not in {issue.code for issue in baseline}

    reviewed = result(overall_read="The review cites ev-1.")
    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [
        issue.message
        for issue in issues
        if issue.code == "raw_evidence_id_in_narrative"
    ] == ["User-facing narrative must not include raw evidence IDs: ['ev-1']."]


def test_strategy_readout_raw_evidence_id_is_rejected_from_narrative():
    reviewed = result(strategy_readout="The strategy readout cites ev-1.")
    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [
        issue.code for issue in issues if issue.code == "raw_evidence_id_in_narrative"
    ] == ["raw_evidence_id_in_narrative"]


def test_correction_evidence_id_is_rejected_from_narrative():
    reviewed = result(overall_read="The review cites correction-C1.")
    issues = validate_review(
        reviewed, evidence_ids={"correction-C1"}, prohibited_terms=set()
    )
    assert [
        issue.code for issue in issues if issue.code == "raw_evidence_id_in_narrative"
    ] == ["raw_evidence_id_in_narrative"]


@pytest.mark.parametrize(
    "statement",
    (
        "Guinea is on the FCV list.",
        "Guinea is not on the FCV list.",
        "Guinea is on the World Bank FCV list.",
        "Guinea is listed on the FCV list.",
        "Côte d’Ivoire is on the World Bank Group FCV list.",
        "Guinea is on the list of FCV-affected countries.",
    ),
)
def test_country_fcv_list_classification_is_rejected(statement):
    reviewed = result(overall_read=statement)

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [issue.code for issue in issues] == ["prohibited_policy_language"]


def test_unknown_institutional_referral_is_rejected():
    reviewed = result().model_copy(update={"institutional_referral_ids": ("missing",)})
    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms=set(),
        registry_entry_ids={"known"},
    )
    assert [
        issue.message
        for issue in issues
        if issue.code == "unknown_institutional_referral"
    ] == ["institutional_referral_ids cite unknown registry entries: ['missing']"]


def test_summary_unknown_link_is_rejected():
    reviewed = result(
        summaries=(RevisionSummaryItem(priority_area_id="missing", title="Revise it"),)
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "unknown_priority_area" in {issue.code for issue in issues}


def test_duplicate_priority_ids_and_summary_linkage_are_rejected_with_repairable_code():
    reviewed = result(
        summaries=(
            RevisionSummaryItem(priority_area_id="pa-1", title="First issue"),
            RevisionSummaryItem(priority_area_id="pa-1", title="Second issue"),
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


def test_mismatched_priority_order_emits_one_repairable_unknown_priority_area_issue():
    reviewed = result(
        summaries=(
            RevisionSummaryItem(priority_area_id="pa-2", title="Second issue"),
            RevisionSummaryItem(priority_area_id="pa-1", title="First issue"),
        ),
        areas=(area(), area(area_id="pa-2")),
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [
        issue.message
        for issue in issues
        if issue.code == "unknown_priority_area"
    ] == ["revision_summary priority_area_id order must exactly match priority_areas order."]


def test_priority_area_unknown_evidence_is_rejected():
    reviewed = result(areas=(area(evidence_ids=("ev-2", "ev-1")),))

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert [issue.message for issue in issues if issue.code == "unknown_evidence"] == [
        "pa-1 cites unknown evidence: ['ev-2']"
    ]


def test_assessment_collections_reject_unknown_evidence():
    reviewed = result(
        rra_assessments=(rra_row(evidence_ids=("missing-rra",)),),
        strategy_assessments_override=strategy_rows(
            status=AssessmentStatus.ALIGNED,
            evidence_ids=("registry-PUB-FCV-STRAT-missing",),
        ),
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms=set(),
    )

    messages = [
        issue.message
        for issue in issues
        if issue.code == "unknown_assessment_evidence"
    ]
    assert any("rra-1" in message and "missing-rra" in message for message in messages)
    assert len([message for message in messages if "strategy-" in message]) == 4
    assert "incomplete_strategy_assessment" in {issue.code for issue in issues}


def test_rra_alignment_requires_driver_assessment():
    reviewed = result(mode=DiagnosticMode.RRA_ALIGNMENT, rra_assessments=())

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "missing_rra_driver_assessment" in {issue.code for issue in issues}


def test_strategy_assessment_requires_each_shift_exactly_once():
    rows = strategy_rows()
    reviewed = result(
        strategy_assessments_override=(rows[0], rows[0], rows[1], rows[2]),
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "incomplete_strategy_assessment" in {issue.code for issue in issues}


def test_assessable_strategy_rows_require_strategy_registry_evidence():
    reviewed = result(
        strategy_assessments_override=strategy_rows(
            status=AssessmentStatus.ALIGNED,
            evidence_ids=("ev-1",),
        )
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "incomplete_strategy_assessment" in {issue.code for issue in issues}


def test_assessable_strategy_rows_require_shift_specific_registry_evidence():
    reviewed = result(
        strategy_assessments_override=strategy_rows(
            status=AssessmentStatus.ALIGNED,
            evidence_ids=("registry-PUB-FCV-STRAT-002",),
        )
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"registry-PUB-FCV-STRAT-002"},
        prohibited_terms=set(),
    )

    assert any(
        issue.code == "incomplete_strategy_assessment"
        and "strategy-anticipate_better" in issue.message
        for issue in issues
    )


def test_incomplete_optional_coverage_rejects_not_evidenced_assessments():
    reviewed = result(
        strategy_assessments_override=strategy_rows(
            status=AssessmentStatus.NOT_EVIDENCED,
            evidence_ids=("ev-1",),
        )
    )

    issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms=set(),
        incomplete_document_roles={DocumentRole.PACKAGE},
    )

    absence_issues = [
        issue for issue in issues if issue.code == "incomplete_coverage_absence_claim"
    ]
    assert len(absence_issues) == len(FCVStrategicShift)
    assert all("not_assessable" in issue.message for issue in absence_issues)
    assert all("partially_aligned" in issue.message for issue in absence_issues)

    complete_issues = validate_review(
        reviewed,
        evidence_ids={"ev-1"},
        prohibited_terms=set(),
        incomplete_document_roles=set(),
    )

    assert "incomplete_coverage_absence_claim" not in {
        issue.code for issue in complete_issues
    }


def test_not_assessable_rows_cannot_support_a_priority_by_themselves():
    reviewed = result(
        areas=(area(evidence_ids=("strategy-anticipate_better",)),),
    )

    issues = validate_review(reviewed, evidence_ids=set(), prohibited_terms=set())

    assert "unknown_evidence" in {issue.code for issue in issues}


def test_summary_titles_are_short_and_link_once_to_priority_areas():
    with pytest.raises(ValidationError):
        RevisionSummaryItem(priority_area_id="pa-1", title="x" * 101)

    reviewed = result(
        summaries=(
            RevisionSummaryItem(priority_area_id="pa-1", title="First issue"),
            RevisionSummaryItem(priority_area_id="pa-1", title="Second issue"),
        )
    )
    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "unknown_priority_area" in {issue.code for issue in issues}


@pytest.mark.parametrize(
    "title",
    (
        "Clarify ev-1",
        "Revise the delivery logic on page 4",
        "Clarify the section 2.1 narrative",
        "Tighten paragraph 12",
        "Add 2 sentences on adaptive delivery",
        "Clarify jobs in the objectives section",
    ),
)
def test_summary_titles_reject_raw_evidence_ids_and_locator_instructions(title):
    reviewed = result(
        summaries=(RevisionSummaryItem(priority_area_id="pa-1", title=title),)
    )

    issues = validate_review(reviewed, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert "invalid_revision_summary_title" in {issue.code for issue in issues}


def test_summary_titles_allow_ordinary_words_that_match_synthetic_evidence_ids():
    reviewed = result(
        summaries=(
            RevisionSummaryItem(
                priority_area_id="pa-1",
                title="Strengthen the regional narrative",
            ),
        )
    )

    issues = validate_review(reviewed, evidence_ids={"regional"}, prohibited_terms=set())

    assert "invalid_revision_summary_title" not in {issue.code for issue in issues}


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

    assert {
        "missing_current_context_support",
        "missing_registry_support",
        "missing_rra_driver_assessment",
        "incomplete_strategy_assessment",
        "unknown_assessment_evidence",
        "raw_evidence_id_in_narrative",
        "unknown_institutional_referral",
    } <= declared_codes


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


def test_stage_length_issue_identifies_priority_area_and_word_counts():
    action = " ".join(f"word-{index}" for index in range(61))

    issues = validate_stage_behavior(
        "finalization",
        action,
        RecommendationScale.FINE_TUNING,
        priority_area_id="pa-3",
    )

    issue = next(item for item in issues if item.code == "stage_length_overreach")
    assert issue.message == (
        "pa-3 recommended_action has 61 whitespace-separated words; "
        "finalization allows at most 60."
    )


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


@pytest.mark.parametrize(
    "action",
    [
        "Commit the WBG to a new delivery unit.",
        "Make financing conditional on quarterly reporting.",
        "Establish a new coordination unit.",
        "Create new delivery unit.",
        "Build a new delivery unit.",
        "Establish a new delivery system.",
        "Make financing contingent on quarterly reporting.",
        "Commit the CPF to a new delivery unit.",
        "The draft should establish a new coordination unit.",
        "Make project support conditional on results.",
        "Tie support to outcomes.",
        "Require the CPF to create a new delivery unit.",
        "Commit the World Bank Group to a new delivery unit.",
        "Create a new delivery arrangement.",
        "Add a new delivery unit.",
        "Develop a new delivery system.",
        "Put in place a new coordination mechanism.",
        "Make project disbursements conditional on results.",
        "The CPF commits to a new delivery unit.",
        "Add a sentence making funding conditional on results.",
        "The draft should introduce a new institutional arrangement.",
        "Design a new coordination mechanism.",
        "Revise the CPF to establish a new delivery unit.",
        "Add wording that creates a new delivery system.",
        "Add a sentence making project support conditional on results.",
        "The draft should tie project disbursements to outcomes.",
        "Commit the World Bank Group to a new facility.",
        "The CPF commits to a new architecture.",
        "Commit the WBG to a new binding commitment.",
        "Commit the WBG to new reporting obligations.",
        "Require the WBG to publish quarterly reports.",
        "Bind the government to a new reporting requirement.",
    ],
)
def test_finalization_rejects_imperative_binding_or_architecture_overreach(action):
    issues = validate_stage_behavior(
        "finalization",
        action,
        RecommendationScale.FINE_TUNING,
    )

    assert [issue.code for issue in issues] == ["stage_overreach"]


@pytest.mark.parametrize(
    "action",
    [
        "The CPF discusses establishing a new delivery unit.",
        "Discuss whether financing should be conditional on results.",
        "The CPF discusses making financing conditional on results.",
        "Consider making project support conditional on results.",
        "The draft does not make financing conditional on results.",
        "Make financing available on a targeted basis.",
        "Make the existing financing conditional wording clearer.",
        "Make support conditional wording clearer.",
        "Require the CPF to clarify existing wording.",
        "Clarify and fine-tune the existing wording.",
    ],
)
def test_finalization_allows_discussion_and_ordinary_fine_tuning(action):
    issues = validate_stage_behavior(
        "finalization",
        action,
        RecommendationScale.FINE_TUNING,
    )

    assert "stage_overreach" not in {issue.code for issue in issues}


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
