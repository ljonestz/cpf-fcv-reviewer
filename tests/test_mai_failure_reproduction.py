"""Synthetic controls for the safe 4 October failure categories; no provider calls."""

from collections import Counter

import pytest

from cpf_fcv_reviewer.contracts import AssessmentStatus, ReviewDraft
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.public_research import ResearchSource, _source_supports_country
from cpf_fcv_reviewer.validators import validate_review
from test_reference_resolution import FixedGateway, reference_case


def grounding_issues(result, evidence):
    return [issue for issue in validate_review(
        result, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ) if issue.code in {
        "unsupported_cpf_response", "unknown_assessment_evidence",
        "unknown_evidence", "target_locator_mismatch",
    }]


@pytest.mark.parametrize("corrected", [False, True])
def test_six_residual_grounding_issues_require_real_source_corrections(
    make_valid_result, corrected,
):
    result, _, evidence = reference_case(make_valid_result)
    rows = tuple(result.rra_driver_assessments[0].model_copy(update={
        "assessment_id": f"rra-{index}", "driver": f"Synthetic driver {index}",
        "cpf_response": "The program promises an invented commitment.",
        "evidence_ids": ("ev-1", f"invented-{index}"),
    }) for index in range(2))
    areas = tuple(result.priority_areas[0].model_copy(update={
        "priority_area_id": f"pa-{index}",
        "target_locator": evidence["ev-1"].locator.model_copy(update={
            "excerpt": "A fabricated target excerpt.",
        }),
    }) for index in range(2))
    result = result.model_copy(update={
        "rra_driver_assessments": rows, "priority_areas": areas,
        "revision_summary": tuple(result.revision_summary[0].model_copy(update={
            "priority_area_id": area.priority_area_id,
        }) for area in areas),
        "fcv_strategy_assessments": tuple(row.model_copy(update={
            "status": AssessmentStatus.NOT_ASSESSABLE, "evidence_ids": (),
        }) for row in result.fcv_strategy_assessments),
    })
    issues = grounding_issues(result, evidence)
    expected = Counter(unsupported_cpf_response=2, unknown_assessment_evidence=2,
                       target_locator_mismatch=2)
    assert Counter(issue.code for issue in issues) == expected
    candidate = result
    if corrected:
        candidate = result.model_copy(update={
            "rra_driver_assessments": tuple(row.model_copy(update={
                "cpf_response": "CPF_QUOTE:ev-1:1", "evidence_ids": ("ev-1",),
            }) for row in rows),
            "priority_areas": tuple(area.model_copy(update={
                "target_locator": evidence["ev-1"].locator.model_copy(update={
                    "excerpt": evidence["ev-1"].text,
                }),
            }) for area in areas),
        })
    draft = ReviewDraft.model_validate({
        **candidate.model_dump(exclude={"metadata", "document_coverage"}),
        "coverage_note": "Synthetic six-error reproduction.",
    })
    gateway = FixedGateway(draft)
    actual = ReviewEngine(gateway).repair(
        result, [{"code": issue.code} for issue in issues],
        evidence_ids=set(evidence), evidence=evidence,
    )
    assert Counter(issue.code for issue in grounding_issues(actual, evidence)) == (
        Counter() if corrected else expected
    )
    assert len(gateway.calls) == 1
    for original, repaired in zip(rows, actual.rra_driver_assessments, strict=True):
        for field in ("assessment_id", "driver", "delivery_mechanism", "result_or_indicator",
                      "remaining_gap", "status", "confidence", "gap_locus"):
            assert getattr(repaired, field) == getattr(original, field)


def test_unknown_priority_reference_alone_receives_source_grounding_evidence(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={"evidence_ids": ("invented-source",)})
    result = result.model_copy(update={"priority_areas": (area,)})
    gateway = FixedGateway(draft)
    ReviewEngine(gateway).repair(result, [{"code": "unknown_evidence"}],
                                evidence_ids=set(evidence), evidence=evidence)
    supplied = gateway.calls[0]["payload"]["source_grounding_evidence"]
    assert supplied == [{
        "evidence_id": "ev-1", "text": evidence["ev-1"].text,
        "document_role": evidence["ev-1"].document_role,
        "locator": evidence["ev-1"].locator.model_dump(mode="json"),
    }]


@pytest.mark.parametrize("other_country", [
    "Guinea-Bissau", "Equatorial Guinea", "Papua New Guinea", "Somalia",
])
def test_country_title_fallback_rejects_a_quote_about_another_country(other_country):
    source = ResearchSource(
        title="Guinea election delays threaten the political transition",
        url="https://www.crisisgroup.org/africa/guinea/synthetic-report",
        excerpt=f"Political violence displaced families in {other_country}.",
    )
    assert not _source_supports_country(source, "Guinea")
