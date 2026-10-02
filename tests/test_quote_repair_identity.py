"""Regression coverage for quote repair identity and policy boundaries."""

from test_reference_resolution import FixedGateway, reference_case

from cpf_fcv_reviewer.contracts import AssessmentConfidence, AssessmentStatus, DocumentRole
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.validators import validate_review


def test_quote_repair_preserves_analysis_when_original_evidence_is_unknown(
    make_valid_result,
):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(
        update={
            "cpf_response": "An unsupported CPF response.",
            "evidence_ids": ("missing-evidence",),
        }
    )
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    evidence["ev-2"] = evidence["ev-1"].model_copy(
        update={
            "evidence_id": "ev-2",
            "text": "The CPF supports local procurement reform.",
        }
    )
    candidate = original.model_copy(
        update={
            "driver": "A model-mutated driver.",
            "cpf_response": evidence["ev-2"].text,
            "delivery_mechanism": "A model-mutated delivery mechanism.",
            "result_or_indicator": "A model-mutated indicator.",
            "remaining_gap": "A model-mutated gap.",
            "status": AssessmentStatus.ALIGNED,
            "confidence": AssessmentConfidence.LOW,
            "gap_locus": None,
            "evidence_ids": ("ev-2",),
        }
    )
    repaired_draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})

    actual = ReviewEngine(FixedGateway(repaired_draft)).repair(
        result,
        [
            {"code": "unsupported_cpf_response"},
            {"code": "unknown_assessment_evidence"},
        ],
        evidence_ids=set(evidence),
        evidence=evidence,
    )

    assert len(actual.rra_driver_assessments) == 1
    row = actual.rra_driver_assessments[0]
    for field in (
        "assessment_id",
        "driver",
        "delivery_mechanism",
        "result_or_indicator",
        "remaining_gap",
        "status",
        "confidence",
        "gap_locus",
    ):
        assert getattr(row, field) == getattr(original, field)
    assert row.cpf_response == "The CPF supports local procurement reform"
    assert row.evidence_ids == ("ev-2",)
    codes = {
        issue.code
        for issue in validate_review(
            actual,
            evidence_ids=set(evidence),
            evidence=evidence,
            prohibited_terms=set(),
        )
    }
    assert "unsupported_cpf_response" not in codes
    assert "unknown_assessment_evidence" not in codes


def test_policy_quote_repair_recovers_a_uniquely_renamed_row(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(
        update={"cpf_response": "The country is eligible for support."}
    )
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": original.cpf_response})
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    evidence["ev-2"] = evidence["ev-1"].model_copy(
        update={
            "evidence_id": "ev-2",
            "text": "The CPF supports local procurement reform.",
        }
    )
    candidate = original.model_copy(
        update={
            "assessment_id": "renamed-policy-row",
            "cpf_response": evidence["ev-2"].text,
            "evidence_ids": ("ev-2",),
            "remaining_gap": "A model-mutated gap.",
        }
    )
    repaired_draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})

    actual = ReviewEngine(FixedGateway(repaired_draft)).repair(
        result,
        [{"code": "prohibited_policy_language"}],
        forbidden_phrases=("eligible for",),
        evidence_ids=set(evidence),
        evidence=evidence,
    )

    assert len(actual.rra_driver_assessments) == 1
    row = actual.rra_driver_assessments[0]
    assert row.assessment_id == original.assessment_id
    assert row.driver == original.driver
    assert row.remaining_gap == original.remaining_gap
    assert row.status == original.status
    assert row.cpf_response == "The CPF supports local procurement reform"
    assert "ev-2" in row.evidence_ids
    codes = {
        issue.code
        for issue in validate_review(
            actual,
            evidence_ids=set(evidence),
            evidence=evidence,
            prohibited_terms={"eligible for"},
        )
    }
    assert "unsupported_cpf_response" not in codes
    assert "prohibited_policy_language" not in codes


def test_selected_quote_cannot_bypass_policy_validation(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    prohibited_quote = "The country is eligible for support."
    original = result.rra_driver_assessments[0].model_copy(
        update={"cpf_response": prohibited_quote}
    )
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": prohibited_quote})
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    candidate = original.model_copy(update={"cpf_response": "CPF_QUOTE:ev-1:1"})
    repaired_draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})

    actual = ReviewEngine(FixedGateway(repaired_draft)).repair(
        result,
        [{"code": "prohibited_policy_language"}],
        forbidden_phrases=("eligible for",),
        evidence_ids=set(evidence),
        evidence=evidence,
    )

    row = actual.rra_driver_assessments[0]
    assert row.cpf_response == "The country is eligible for support"
    codes = {
        issue.code
        for issue in validate_review(
            actual,
            evidence_ids=set(evidence),
            evidence=evidence,
            prohibited_terms={"eligible for"},
        )
    }
    assert "unsupported_cpf_response" not in codes
    assert "prohibited_policy_language" in codes


def test_quote_preservation_does_not_block_explicit_coverage_status_repair(
    make_valid_result,
):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(
        update={
            "cpf_response": "An unsupported CPF response.",
            "status": AssessmentStatus.NOT_EVIDENCED,
        }
    )
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    evidence["ev-2"] = evidence["ev-1"].model_copy(
        update={
            "evidence_id": "ev-2",
            "text": "The CPF supports local procurement reform.",
        }
    )
    candidate = original.model_copy(
        update={
            "cpf_response": evidence["ev-2"].text,
            "evidence_ids": ("ev-2",),
            "remaining_gap": "Existing support remains weakly operationalized.",
            "status": AssessmentStatus.PARTIALLY_ALIGNED,
        }
    )
    repaired_draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})

    actual = ReviewEngine(FixedGateway(repaired_draft)).repair(
        result,
        [
            {"code": "unsupported_cpf_response"},
            {"code": "incomplete_coverage_absence_claim"},
        ],
        evidence_ids=set(evidence),
        evidence=evidence,
    )

    assert len(actual.rra_driver_assessments) == 1
    row = actual.rra_driver_assessments[0]
    assert row.assessment_id == original.assessment_id
    assert row.status is AssessmentStatus.PARTIALLY_ALIGNED
    assert row.remaining_gap == candidate.remaining_gap
    assert row.cpf_response == "The CPF supports local procurement reform"
    assert row.evidence_ids == ("ev-1", "ev-2")
    codes = {
        issue.code
        for issue in validate_review(
            actual,
            evidence_ids=set(evidence),
            evidence=evidence,
            prohibited_terms=set(),
            incomplete_document_roles={DocumentRole.CONTEXT},
        )
    }
    assert "unsupported_cpf_response" not in codes
    assert "incomplete_coverage_absence_claim" not in codes
