"""Coordinator findings must stay qualitative, complete and evidence-linked."""

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer import contracts
from cpf_fcv_reviewer.validators import result_text, validate_review


def finding(**overrides):
    assert hasattr(contracts, "CoreFinding"), "Coordinator finding contract is missing"
    return contracts.CoreFinding(
        **{
            "question": "actions_commitment",
            "assessment": "Commitment is stated; supporting action is not established.",
            "basis": "assessed",
            "evidence_ids": ("ev-1",),
            **overrides,
        }
    )


def test_assessed_finding_requires_evidence():
    with pytest.raises(ValidationError):
        finding(evidence_ids=())


@pytest.mark.parametrize("field", ["assessment", "evidence_ids", "priority_area_ids"])
def test_finding_rejects_blank_fields(field):
    value = " " if field == "assessment" else (" ",)
    with pytest.raises(ValidationError):
        finding(**{field: value})


def test_core_findings_validate_real_evidence(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"core_findings": (finding(evidence_ids=("invented",)),)})
    issues = validate_review(result, evidence_ids=set(evidence), prohibited_terms=set())
    assert "unknown_assessment_evidence" in {i.code for i in issues}


def test_findings_and_framing_enter_policy_validation(make_valid_result):
    result, _ = make_valid_result
    result = result.model_copy(update={
        "core_findings": (finding(assessment="The country is eligible for the allocation."),)
    })
    assert "eligible for" in result_text(result)


def test_new_schema_requires_all_four_findings(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={
        "metadata": result.metadata.model_copy(update={"schema_version": "2.0.0"})
    })
    issues = validate_review(result, evidence_ids=set(evidence), prohibited_terms=set())
    assert "incomplete_core_findings" in {i.code for i in issues}


def test_legacy_review_does_not_invent_findings(make_valid_result):
    result, _ = make_valid_result
    assert getattr(result, "core_findings", None) == ()


def test_context_framing_requires_evidence_for_a_proposal():
    assert hasattr(contracts, "ContextFraming"), "Context framing contract is missing"
    with pytest.raises(ValidationError):
        contracts.ContextFraming(
            category="in_transition",
            rationale="There is a proposed transition window.",
            confidence="low",
            evidence_ids=(),
        )


def test_unrelated_repair_preserves_core_findings(make_valid_result):
    from cpf_fcv_reviewer.contracts import ReviewDraft
    from cpf_fcv_reviewer.review_engine import ReviewEngine

    result, evidence = make_valid_result
    result = result.model_copy(update={"core_findings": (finding(),)})
    payload = result.model_dump(exclude={"metadata", "document_coverage"})
    payload["coverage_note"] = result.document_coverage.coverage_note
    payload["core_findings"] = ()
    candidate = ReviewDraft.model_validate(payload)

    class Gateway:
        def generate(self, **kwargs):
            return candidate

    repaired = ReviewEngine(Gateway()).repair(
        result, [{"code": "unknown_evidence", "message": "Repair priority evidence."}],
        evidence_ids=set(evidence),
    )
    assert repaired.core_findings == result.core_findings


def test_export_rejects_unknown_core_evidence(make_valid_result):
    from cpf_fcv_reviewer.export_docx import (
        EvidenceCompletenessError,
        validate_evidence_completeness,
    )

    result, evidence = make_valid_result
    result = result.model_copy(update={"core_findings": (finding(evidence_ids=("missing",)),)})
    with pytest.raises(EvidenceCompletenessError):
        validate_evidence_completeness(result, evidence)


def test_core_finding_checks_present_day_claim_support(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"core_findings": (finding(
        assessment="Conflict has intensified across Benin and displacement is rising.",
    ),)})
    issues = validate_review(
        result, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    )
    assert "missing_current_context_support" in {issue.code for issue in issues}


def test_repair_cannot_invent_coordinator_framing_or_change_destination(make_valid_result):
    from cpf_fcv_reviewer.contracts import (
        ContextFraming,
        RecommendationDestination,
        ReviewDraft,
    )
    from cpf_fcv_reviewer.review_engine import ReviewEngine

    result, evidence = make_valid_result
    result = result.model_copy(update={"priority_areas": (
        result.priority_areas[0].model_copy(update={
            "destination": RecommendationDestination.MEETING_RECORD,
        }),
    )})
    payload = result.model_dump(exclude={"metadata", "document_coverage"})
    payload["coverage_note"] = result.document_coverage.coverage_note
    payload["priority_areas"][0]["destination"] = "cpf_text"
    payload["proposed_context_framing"] = ContextFraming(
        category="at_risk", rationale="A proposed framing.", confidence="low",
        origin="coordinator_override",
    )
    candidate = ReviewDraft.model_validate(payload)

    class Gateway:
        def generate(self, **kwargs):
            return candidate

    repaired = ReviewEngine(Gateway()).repair(
        result, [{"code": "unknown_evidence", "message": "Repair evidence only."}],
        evidence_ids=set(evidence),
    )
    assert repaired.proposed_context_framing is None
    assert repaired.priority_areas[0].destination == "meeting_record"
