"""Exact cited-source resolution through the real initial/repair engine paths."""

import pytest

from cpf_fcv_reviewer.contracts import DocumentRole, EvidencePack, ReviewDraft
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.validators import validate_review


class FixedGateway:
    def __init__(self, draft):
        self.draft = draft
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.draft


def reference_case(make_valid_result):
    result, evidence = make_valid_result
    source = evidence["ev-1"].model_copy(update={
        "document_role": DocumentRole.PRIMARY,
        "text": "The program will support access.",
        "locator": evidence["ev-1"].locator.model_copy(update={
            "page": 7, "heading": "Verified heading",
        }),
    })
    area = result.priority_areas[0].model_copy(update={
        "target_locator": result.priority_areas[0].target_locator.model_copy(update={
            "document_title": "Guessed title.pdf", "page": 999,
            "excerpt": "THE program will support access.",
        }),
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    draft = ReviewDraft.model_validate({
        **result.model_dump(exclude={"metadata", "document_coverage"}),
        "coverage_note": "Synthetic fixture.",
    })
    return result, draft, {"ev-1": source}


@pytest.mark.parametrize("operation", ["review", "repair"])
def test_engine_copies_unique_cited_source_location(make_valid_result, operation):
    result, draft, evidence = reference_case(make_valid_result)
    gateway = FixedGateway(draft)
    engine = ReviewEngine(gateway)
    if operation == "review":
        actual = engine.review(EvidencePack(
            metadata=result.metadata, evidence=tuple(evidence.values()),
            diagnostic_entries=(),
        ))
    else:
        actual = engine.repair(result, [{"code": "target_locator_mismatch"}],
                               evidence_ids=set(evidence), evidence=evidence)
    target = actual.priority_areas[0].target_locator
    assert target.document_title == "CPF.docx"
    assert target.page == 7
    assert target.heading == "Verified heading"
    assert target.excerpt == "The program will support access"
    assert target.excerpt in evidence["ev-1"].text
    assert target.is_paraphrase is False
    assert len(gateway.calls) == 1
    issues = validate_review(actual, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    assert not any(i.code == "target_locator_mismatch" for i in issues)


def test_ambiguous_cited_passage_does_not_move_the_target(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2",
        "locator": evidence["ev-1"].locator.model_copy(update={"page": 8}),
    })
    area = draft.priority_areas[0].model_copy(update={"evidence_ids": ("ev-1", "ev-2")})
    draft = draft.model_copy(update={"priority_areas": (area,)})
    actual = ReviewEngine(FixedGateway(draft)).review(EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
    ))
    assert actual.priority_areas[0].target_locator == area.target_locator
    issues = validate_review(actual, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    assert any(i.code == "target_locator_mismatch" for i in issues)


def test_an_uncited_quote_is_not_used_to_relocate_a_target(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={"evidence_id": "ev-2"})
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": "Unrelated text."})
    actual = ReviewEngine(FixedGateway(draft)).review(EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
    ))
    assert actual.priority_areas[0].target_locator == draft.priority_areas[0].target_locator


def test_locator_repair_can_add_its_known_source_without_losing_original_links(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "A different source defines the delivery arrangement.",
        "locator": evidence["ev-1"].locator.model_copy(update={"page": 8}),
    })
    candidate = draft.priority_areas[0].model_copy(update={
        "evidence_ids": ("ev-2",),
        "target_locator": evidence["ev-2"].locator.model_copy(update={
            "excerpt": "A different source defines the delivery arrangement.",
        }),
    })
    draft = draft.model_copy(update={"priority_areas": (candidate,)})
    gateway = FixedGateway(draft)
    actual = ReviewEngine(gateway).repair(
        result, [{"code": "target_locator_mismatch"}],
        evidence_ids=set(evidence), evidence=evidence,
    )
    area = actual.priority_areas[0]
    assert area.evidence_ids == ("ev-1", "ev-2")
    assert area.target_locator.page == 8
    assert area.target_locator.excerpt in evidence["ev-2"].text
    assert len(gateway.calls) == 1
    issues = validate_review(actual, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    assert not any(i.code == "target_locator_mismatch" for i in issues)


def test_repeated_passage_with_a_valid_coordinate_keeps_the_chosen_page(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2",
        "locator": evidence["ev-1"].locator.model_copy(update={"page": 8}),
    })
    area = draft.priority_areas[0].model_copy(update={
        "evidence_ids": ("ev-1", "ev-2"), "target_locator": evidence["ev-2"].locator,
    })
    draft = draft.model_copy(update={"priority_areas": (area,)})
    actual = ReviewEngine(FixedGateway(draft)).review(EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
    ))
    assert actual.priority_areas[0].target_locator.page == 8
    assert actual.priority_areas[0].target_locator.excerpt in evidence["ev-2"].text


@pytest.mark.parametrize("operation", ["review", "repair"])
def test_cpf_quote_is_copied_and_repair_keeps_analytical_fields(make_valid_result, operation):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The CPF supports local procurement reform.",
    })
    candidate = draft.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "THE CPF supports local procurement reform.",
        "evidence_ids": ("ev-2",),
        "driver": "An unrelated replacement driver.",
        "delivery_mechanism": "An unrelated replacement mechanism.",
        "remaining_gap": "An unrelated replacement gap.",
    })
    draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})
    gateway = FixedGateway(draft)
    if operation == "review":
        actual = ReviewEngine(gateway).review(EvidencePack(
            metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
        ))
    else:
        actual = ReviewEngine(gateway).repair(
            result, [{"code": "unsupported_cpf_response"}],
            evidence_ids=set(evidence), evidence=evidence,
        )
        for name in ("driver", "delivery_mechanism", "result_or_indicator", "remaining_gap",
                     "status", "confidence", "gap_locus", "assessment_id"):
            assert getattr(actual.rra_driver_assessments[0], name) == getattr(
                result.rra_driver_assessments[0], name)
        assert actual.rra_driver_assessments[0].evidence_ids == ("ev-1", "ev-2")
        assert gateway.calls[0]["payload"]["source_grounding_evidence"]
    response = actual.rra_driver_assessments[0].cpf_response
    assert response == "The CPF supports local procurement reform"
    assert response in evidence["ev-2"].text
    assert len(gateway.calls) == 1


def test_cpf_response_repair_preserves_an_already_verified_quote(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The program will support access.",
    })
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The CPF supports procurement reform.",
    })
    candidate = draft.rra_driver_assessments[0].model_copy(update={
        "cpf_response": evidence["ev-2"].text, "evidence_ids": ("ev-2",),
    })
    draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})
    actual = ReviewEngine(FixedGateway(draft)).repair(
        result, [{"code": "unsupported_cpf_response"}],
        evidence_ids=set(evidence), evidence=evidence,
    )
    assert actual.rra_driver_assessments[0].cpf_response == "The program will support access"


def test_invalid_cpf_quote_repair_remains_fatal(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["context-1"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
        "text": "The government initiated prosecutions.",
    })
    candidate = draft.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The government initiated prosecutions.",
        "evidence_ids": ("context-1", "invented-source"),
    })
    draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})
    actual = ReviewEngine(FixedGateway(draft)).repair(
        result, [{"code": "unsupported_cpf_response"}],
        evidence_ids=set(evidence), evidence=evidence,
    )
    assert actual.rra_driver_assessments == result.rra_driver_assessments
    assert any(i.code == "unsupported_cpf_response" for i in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ))
