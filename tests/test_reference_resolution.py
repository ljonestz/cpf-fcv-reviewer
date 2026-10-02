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


@pytest.mark.parametrize("quote_valid", [True, False])
def test_renamed_cpf_quote_repair_keeps_original_driver_identity(make_valid_result, quote_valid):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0]
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The CPF supports procurement reform.",
    })
    candidate = original.model_copy(update={
        "assessment_id": "renamed-rra-row",
        "cpf_response": evidence["ev-2"].text if quote_valid else "Unsupported claim.",
        "evidence_ids": ("ev-2",),
        "remaining_gap": "An unrelated replacement gap.",
    })
    gateway = FixedGateway(draft.model_copy(update={"rra_driver_assessments": (candidate,)}))
    actual = ReviewEngine(gateway).repair(
        result, [{"code": "unsupported_cpf_response"}],
        evidence_ids=set(evidence), evidence=evidence,
    )
    assert len(actual.rra_driver_assessments) == 1
    row = actual.rra_driver_assessments[0]
    for field in ("assessment_id", "driver", "delivery_mechanism", "result_or_indicator",
                  "remaining_gap", "status", "confidence", "gap_locus"):
        assert getattr(row, field) == getattr(original, field)
    assert row.cpf_response == ("The CPF supports procurement reform" if quote_valid
                                else original.cpf_response)
    assert row.evidence_ids == (("ev-1", "ev-2") if quote_valid else original.evidence_ids)
    issues = validate_review(actual, evidence_ids=set(evidence), evidence=evidence,
                             prohibited_terms=set())
    assert any(issue.code == "unsupported_cpf_response" for issue in issues) == (not quote_valid)
    assert len(gateway.calls) == 1


@pytest.mark.parametrize("duplicate_side", ["original", "repaired"])
def test_renamed_cpf_quote_repair_does_not_guess_ambiguous_identity(make_valid_result, duplicate_side):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0]
    candidate = original.model_copy(update={
        "assessment_id": "renamed-rra-row", "cpf_response": evidence["ev-1"].text,
    })
    if duplicate_side == "original":
        result = result.model_copy(update={"rra_driver_assessments": (
            original, original.model_copy(update={"assessment_id": "another-original"}),
        )})
        candidates = (candidate,)
    else:
        candidates = (candidate, candidate.model_copy(update={"assessment_id": "another-repaired"}))
    actual = ReviewEngine(FixedGateway(draft.model_copy(update={
        "rra_driver_assessments": candidates,
    }))).repair(result, [{"code": "unsupported_cpf_response"}],
               evidence_ids=set(evidence), evidence=evidence)
    assert actual.rra_driver_assessments[:len(result.rra_driver_assessments)] == result.rra_driver_assessments
    assert any(issue.code == "unsupported_cpf_response" for issue in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ))


@pytest.mark.parametrize("renamed", [True, False])
def test_cpf_quote_repair_does_not_cross_wire_duplicate_original_ids(make_valid_result, renamed):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0]
    second = original.model_copy(update={"driver": "A different RRA driver."})
    result = result.model_copy(update={"rra_driver_assessments": (original, second)})
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The CPF supports procurement reform.",
    })
    candidates = (
        original.model_copy(update={"assessment_id": "renamed-first" if renamed else original.assessment_id,
                                    "cpf_response": evidence["ev-1"].text}),
        second.model_copy(update={"assessment_id": "renamed-second" if renamed else second.assessment_id,
                                  "cpf_response": evidence["ev-2"].text,
                                  "evidence_ids": ("ev-2",)}),
    )
    actual = ReviewEngine(FixedGateway(draft.model_copy(update={
        "rra_driver_assessments": candidates,
    }))).repair(result, [{"code": "unsupported_cpf_response"}],
               evidence_ids=set(evidence), evidence=evidence)
    assert actual.rra_driver_assessments[:2] == (original, second)
    assert sum(issue.code == "unsupported_cpf_response" for issue in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    )) == 2


def test_cpf_quote_repair_does_not_guess_between_duplicate_candidate_ids(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0]
    first = original.model_copy(update={"cpf_response": evidence["ev-1"].text})
    second = first.model_copy(update={"driver": "A different RRA driver."})
    actual = ReviewEngine(FixedGateway(draft.model_copy(update={
        "rra_driver_assessments": (first, second),
    }))).repair(result, [{"code": "unsupported_cpf_response"}],
               evidence_ids=set(evidence), evidence=evidence)
    assert actual.rra_driver_assessments == (original,)
    assert any(issue.code == "unsupported_cpf_response" for issue in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ))


@pytest.mark.parametrize("codes", [
    ["prohibited_policy_language"],
    ["prohibited_policy_language", "unsupported_cpf_response"],
])
def test_policy_quote_repair_keeps_the_verified_replacement_source(make_valid_result, codes):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The country is not on the list of FCV-affected countries.",
    })
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": original.cpf_response})
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The CPF supports local procurement reform.",
        "locator": evidence["ev-1"].locator.model_copy(update={"page": 8}),
    })
    evidence["context-1"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
    })
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    candidate = original.model_copy(update={
        "cpf_response": evidence["ev-2"].text, "evidence_ids": ("ev-2",),
    })
    gateway = FixedGateway(draft.model_copy(update={"rra_driver_assessments": (candidate,)}))
    actual = ReviewEngine(gateway).repair(
        result, [{"code": code} for code in codes],
        forbidden_phrases=("is not on the list of fcv-affected countries",),
        evidence_ids=set(evidence), evidence=evidence,
    )
    row = actual.rra_driver_assessments[0]
    assert row.evidence_ids == ("ev-1", "ev-2")
    assert row.cpf_response == "The CPF supports local procurement reform"
    assert row.driver == original.driver and row.status == original.status
    assert gateway.calls[0]["payload"]["source_grounding_evidence"]
    if codes == ["prohibited_policy_language"]:
        assert {item["evidence_id"] for item in
                gateway.calls[0]["payload"]["source_grounding_evidence"]} == {"ev-1", "ev-2"}
    assert len(gateway.calls) == 1
    assert not {"unsupported_cpf_response", "prohibited_policy_language"} & {
        issue.code for issue in validate_review(
            actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
        )
    }


@pytest.mark.parametrize("context_quote", [False, True])
def test_policy_quote_repair_rejects_paraphrases_and_context(make_valid_result, context_quote):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The country is eligible for support.",
    })
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": original.cpf_response})
    result = result.model_copy(update={"rra_driver_assessments": (original,)})
    candidate = original.model_copy(update={"cpf_response": "The CPF considers support."})
    if context_quote:
        evidence["context-1"] = evidence["ev-1"].model_copy(update={
            "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
            "text": candidate.cpf_response,
        })
        candidate = candidate.model_copy(update={"evidence_ids": ("context-1",)})
    actual = ReviewEngine(FixedGateway(draft.model_copy(update={
        "rra_driver_assessments": (candidate,),
    }))).repair(result, [{"code": "prohibited_policy_language"}],
               forbidden_phrases=("eligible for",), evidence_ids=set(evidence), evidence=evidence)
    assert actual.rra_driver_assessments[0].cpf_response == "The country is eligible for support"
    assert actual.rra_driver_assessments[0].evidence_ids == original.evidence_ids
    codes = {issue.code for issue in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    )}
    assert "prohibited_policy_language" in codes
    assert "unsupported_cpf_response" not in codes


@pytest.mark.parametrize("duplicate_side", ["original", "repaired"])
def test_policy_repair_cannot_bypass_ambiguous_quote_identity(make_valid_result, duplicate_side):
    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The CPF is eligible for unsupported financing.",
    })
    candidate = original.model_copy(update={"cpf_response": evidence["ev-1"].text})
    originals = (original,)
    candidates = (candidate,)
    if duplicate_side == "original":
        originals += (original.model_copy(update={"driver": "A different original driver."}),)
    else:
        candidates += (candidate.model_copy(update={"driver": "A different candidate driver."}),)
    result = result.model_copy(update={"rra_driver_assessments": originals})
    actual = ReviewEngine(FixedGateway(draft.model_copy(update={
        "rra_driver_assessments": candidates,
    }))).repair(result, [{"code": "unsupported_cpf_response"}, {"code": "prohibited_policy_language"}],
               forbidden_phrases=("eligible for",), evidence_ids=set(evidence), evidence=evidence)
    assert actual.rra_driver_assessments == originals


def test_date_quote_repair_keeps_its_source_and_publication_provenance(make_valid_result):
    from datetime import date
    from cpf_fcv_reviewer.contracts import DiagnosticProvenance

    result, draft, evidence = reference_case(make_valid_result)
    original = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The June 2022 RRA identifies unequal access.",
    })
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": original.cpf_response})
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "text": "The June 2023 RRA identifies unequal access.",
    })
    provenance = DiagnosticProvenance(
        document_title="Public RRA.pdf", publication_date=date(2023, 6, 1), date_basis="cover",
        locator=evidence["ev-1"].locator.model_copy(update={"document_title": "Public RRA.pdf"}),
    )
    result = result.model_copy(update={
        "rra_driver_assessments": (original,),
        "metadata": result.metadata.model_copy(update={"diagnostic_provenance": provenance}),
    })
    candidate = original.model_copy(update={"cpf_response": evidence["ev-2"].text,
                                             "evidence_ids": ("ev-2",)})
    gateway = FixedGateway(draft.model_copy(update={"rra_driver_assessments": (candidate,)}))
    actual = ReviewEngine(gateway).repair(
        result, [{"code": "diagnostic_date_conflict"}],
        evidence_ids=set(evidence), evidence=evidence,
    )
    assert actual.rra_driver_assessments[0].evidence_ids == ("ev-1", "ev-2")
    assert actual.rra_driver_assessments[0].cpf_response == evidence["ev-2"].text.rstrip(".")
    assert actual.metadata.diagnostic_provenance == provenance
    assert gateway.calls[0]["payload"]["source_grounding_evidence"]
