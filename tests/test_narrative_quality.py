import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DetailLevel,
    DiagnosticMode,
    DocumentCoverage,
    EvidenceLocator,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RecommendationScale,
    ReviewResult,
    RevisionSummaryItem,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.review_profiles import STAGE_PROFILES
from cpf_fcv_reviewer.validators import validate_review

CASES_PATH = Path(__file__).parent / "fixtures" / "narrative_review_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


def assert_narrative_quality(result: ReviewResult, case: dict) -> None:
    """Assert the user-facing result has the required note-first structure."""
    profile = STAGE_PROFILES[case["stage"]]
    assert [scale.value for scale in profile.allowed_scales] == case["allowed_scales"]
    assert profile.max_immediate_insertion_words == case["max_action_words"]
    assert result.metadata.review_stage == case["stage"]
    assert result.overall_read.strip()
    assert 1 <= len(result.revision_summary) <= len(result.priority_areas)

    area_ids = {area.priority_area_id for area in result.priority_areas}
    assert all(item.priority_area_id in area_ids for item in result.revision_summary), (
        "Every summary item must link to a priority area."
    )
    assert len({item.priority_area_id for item in result.revision_summary}) == len(
        result.revision_summary
    )
    assert all(len(item.title) <= 100 for item in result.revision_summary)
    allowed_scales = set(case["allowed_scales"])
    coordinate = case["required_target_coordinates"]
    expected_evidence_ids = set(case["evidence_ids"])
    for area in result.priority_areas:
        assert area.recommendation_scale.value in allowed_scales
        assert len(area.recommended_action.split()) <= case["max_action_words"]
        assert area.target_locator.document_title == coordinate["document_title"]
        assert area.target_locator.heading == coordinate["heading"]
        assert area.target_locator.element == coordinate["element"]
        assert (
            area.target_locator.page
            or area.target_locator.heading
            or area.target_locator.element
        ), (
            "Each priority area must identify a meaningful document coordinate."
        )
        assert area.evidence_ids
        assert set(area.evidence_ids) <= expected_evidence_ids
        heading = area.heading.casefold()
        assert all(term.casefold() not in heading for term in case["forbidden_headings"])


def strategy_rows() -> tuple[FCVStrategyAssessment, ...]:
    return tuple(
        FCVStrategyAssessment(
            assessment_id=f"strategy-{shift.value}",
            strategic_shift=shift,
            assessment="The supplied synthetic case does not support assessment of this shift.",
            status=AssessmentStatus.NOT_ASSESSABLE,
            confidence=AssessmentConfidence.LOW,
            evidence_ids=(),
        )
        for shift in FCVStrategicShift
    )


def build_result(case: dict) -> ReviewResult:
    """Build a deterministic valid result with one stage-appropriate action."""
    stage = case["stage"]
    scale_by_stage = {
        "early_drafting": RecommendationScale.PREPARATION_PRIORITY,
        "decision_review": RecommendationScale.SUBSTANTIVE_REVISION,
        "finalization": RecommendationScale.FINE_TUNING,
    }
    action_by_stage = {
        "early_drafting": (
            "Carry the missing conflict-sensitive results pathway as a preparation priority "
            "for the next CPF draft."
        ),
        "decision_review": (
            "Revise the results framework to state how the conflict-sensitive diagnosis "
            "changes objectives, indicators, and delivery choices."
        ),
        "finalization": (
            "Add one sentence linking the conflict-sensitive diagnosis to the results framework."
        ),
    }
    coordinate = case["required_target_coordinates"]
    locator = EvidenceLocator(
        document_title=coordinate["document_title"],
        heading=coordinate["heading"],
        element=coordinate["element"],
        excerpt="The results framework states the proposed outcomes without the diagnostic link.",
    )
    metadata = RunMetadata(
        run_id=f"synthetic-{stage}",
        created_at=datetime(2026, 8, 12, tzinfo=UTC),
        review_stage=stage,
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="test",
        schema_version="test",
        rubric_version="test",
        prompt_bundle_version="test",
        registry_versions={"synthetic": "1"},
        model_id="synthetic-model",
        detail_level=DetailLevel.STANDARD,
    )
    area_id = f"pa-{stage}"
    action = action_by_stage[stage]
    return ReviewResult(
        metadata=metadata,
        overall_read=(
            "The draft has a credible foundation, but the conflict-sensitive diagnosis is not yet "
            "translated into an explicit results pathway."
        ),
        alignment_readout="The draft shows partial alignment with the FCV framing.",
        revision_summary=(
            RevisionSummaryItem(
                priority_area_id=area_id,
                title="Make the conflict-sensitive results pathway explicit",
            ),
        ),
        priority_areas=(
            PriorityArea(
                priority_area_id=area_id,
                heading="Make the conflict-sensitive results pathway explicit",
                assessment=case["core_weakness"],
                why_it_matters=(
                    "Without the link, the CPF cannot show how context changes the "
                    "proposed response."
                ),
                recommended_action=action,
                target_locator=locator,
                recommendation_scale=scale_by_stage[stage],
                evidence_ids=tuple(case["evidence_ids"]),
                sensitivity=SensitivityCategory.CAUTIOUS,
                gap_locus=GapLocus.RESULTS_FRAMEWORK,
            ),
        ),
        fcv_strategy_assessments=strategy_rows(),
        limitations=("Synthetic case; no external context documents were supplied.",),
        document_coverage=DocumentCoverage(
            primary_document=coordinate["document_title"],
            coverage_note="Synthetic primary CPF draft only.",
        ),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stage"])
def test_synthetic_stage_cases_meet_narrative_quality_rubric(case: dict) -> None:
    result = build_result(case)

    assert_narrative_quality(result, case)
    assert validate_review(
        result,
        evidence_ids=set(case["evidence_ids"]),
        prohibited_terms=set(),
    ) == ()


def test_fixture_cases_preserve_one_core_weakness() -> None:
    assert {case["core_weakness"] for case in CASES} == {
        CASES[0]["core_weakness"]
    }


def test_stage_results_change_scale_and_action_but_share_evidence_basis() -> None:
    results = [build_result(case) for case in CASES]

    assert len({result.priority_areas[0].recommendation_scale for result in results}) == 3
    assert len({result.priority_areas[0].recommended_action for result in results}) == 3
    assert {result.priority_areas[0].assessment for result in results} == {
        CASES[0]["core_weakness"]
    }
    assert {
        result.priority_areas[0].target_locator.model_dump_json() for result in results
    } == {results[0].priority_areas[0].target_locator.model_dump_json()}


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case['stage']}-scale")
def test_validate_review_rejects_invalid_stage_scale(case: dict) -> None:
    result = build_result(case)
    bad_area = result.priority_areas[0].model_copy(
        update={"recommendation_scale": RecommendationScale.COMMENT_RESPONSE}
    )
    bad_result = result.model_copy(update={"priority_areas": (bad_area,)})

    issues = validate_review(
        bad_result,
        evidence_ids=set(case["evidence_ids"]),
        prohibited_terms=set(),
    )

    assert "stage_overreach" in {issue.code for issue in issues}


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case['stage']}-length")
def test_validate_review_rejects_over_limit_action(case: dict) -> None:
    result = build_result(case)
    over_limit_action = " ".join(
        f"word-{index}" for index in range(case["max_action_words"] + 1)
    )
    bad_area = result.priority_areas[0].model_copy(
        update={"recommended_action": over_limit_action}
    )
    bad_result = result.model_copy(update={"priority_areas": (bad_area,)})

    issues = validate_review(
        bad_result,
        evidence_ids=set(case["evidence_ids"]),
        prohibited_terms=set(),
    )

    assert "stage_length_overreach" in {issue.code for issue in issues}


@pytest.mark.parametrize(
    "forbidden_term",
    CASES[0]["forbidden_headings"],
    ids=lambda term: term.replace(" ", "-").lower(),
)
def test_rubric_rejects_case_insensitive_forbidden_generic_heading(forbidden_term: str) -> None:
    case = CASES[0]
    result = build_result(case)
    bad_area = result.priority_areas[0].model_copy(update={"heading": forbidden_term.swapcase()})
    bad_result = result.model_copy(update={"priority_areas": (bad_area,)})

    with pytest.raises(AssertionError):
        assert_narrative_quality(bad_result, case)
