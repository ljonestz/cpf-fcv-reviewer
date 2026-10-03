"""Provider-free source-selection recovery and safe diagnostic boundaries."""
import pytest

from cpf_fcv_reviewer.contracts import DocumentRole, EvidencePack
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.validators import validate_review
from test_reference_resolution import FixedGateway, reference_case


@pytest.mark.parametrize("operation", ["review", "repair"])
def test_quote_selection_copies_source_and_preserves_analysis(make_valid_result, operation):
    result, draft, evidence = reference_case(make_valid_result)
    text = "A first sentence. The CPF supports women’s jobs through local firms. Final sentence."
    evidence["ev-2"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "ev-2", "document_role": DocumentRole.PACKAGE, "text": text,
    })
    original = result.rra_driver_assessments[0]
    candidate = original.model_copy(update={
        "cpf_response": "CPF_QUOTE:ev-2:2", "evidence_ids": ("ev-2",),
    })
    draft = draft.model_copy(update={"rra_driver_assessments": (candidate,)})
    gateway = FixedGateway(draft)
    if operation == "review":
        actual = ReviewEngine(gateway).review(EvidencePack(
            metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
        ))
        assert gateway.calls[0]["payload"]["evidence_pack"]["evidence"][1]["text"] == text
    else:
        actual = ReviewEngine(gateway).repair(
            result, [{"code": "unsupported_cpf_response"}],
            evidence_ids=set(evidence), evidence=evidence,
        )
        assert actual.rra_driver_assessments[0].evidence_ids == ("ev-1", "ev-2")
    row = actual.rra_driver_assessments[0]
    assert row.cpf_response == "The CPF supports women’s jobs through local firms"
    assert row.cpf_response in text
    assert row.driver == original.driver and row.status == original.status
    assert row.delivery_mechanism == original.delivery_mechanism
    assert row.result_or_indicator == original.result_or_indicator
    assert row.remaining_gap == original.remaining_gap
    options = gateway.calls[0]["payload"]["cpf_quote_index"]
    assert any(o["quote_id"] == "CPF_QUOTE:ev-2:2" and o["evidence_id"] == "ev-2" for o in options)
    assert len(gateway.calls) == 1
    assert not any(i.code == "unsupported_cpf_response" for i in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ))


@pytest.mark.parametrize("selection,ids,role", [
    ("CPF_QUOTE:ev-1:99", ("ev-1",), DocumentRole.PRIMARY),
    ("CPF_QUOTE:missing:1", ("ev-1",), DocumentRole.PRIMARY),
    ("CPF_QUOTE:ev-1:1", ("unrelated",), DocumentRole.PRIMARY),
    ("CPF_QUOTE:ev-1:1", ("ev-1",), DocumentRole.CONTEXT),
    ("CPF_QUOTE:ev-1:1 then fund prosecutions", ("ev-1",), DocumentRole.PRIMARY),
])
def test_invalid_or_uncited_selection_never_becomes_a_quote(make_valid_result, selection, ids, role):
    result, draft, evidence = reference_case(make_valid_result)
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"document_role": role})
    # Retain a primary so initial review can proceed with an ineligible candidate.
    evidence["primary-other"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "primary-other", "document_role": DocumentRole.PRIMARY,
    })
    row = draft.rra_driver_assessments[0].model_copy(update={
        "cpf_response": selection, "evidence_ids": ids,
    })
    draft = draft.model_copy(update={"rra_driver_assessments": (row,)})
    actual = ReviewEngine(FixedGateway(draft)).review(EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
    ))
    assert actual.rra_driver_assessments[0].cpf_response == selection
    assert any(i.code == "unsupported_cpf_response" for i in validate_review(
        actual, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set(),
    ))


def test_quote_index_is_bounded_preview_with_full_original_text_preserved(make_valid_result):
    result, draft, evidence = reference_case(make_valid_result)
    text = "A long sentence " + "with material source detail " * 40 + "."
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": text})
    evidence["context"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "context", "document_role": DocumentRole.CONTEXT,
    })
    gateway = FixedGateway(draft)
    ReviewEngine(gateway).review(EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=(),
    ))
    payload = gateway.calls[0]["payload"]
    assert payload["evidence_pack"]["evidence"][0]["text"] == text
    options = payload["cpf_quote_index"]
    assert len(options) == 1 and len(options[0]["preview"]) <= 160
    assert options[0]["evidence_id"] == "ev-1"


@pytest.mark.parametrize("response,ids,status,reason", [
    ("!!!", ("ev-1",), "aligned", "empty_response"),
    ("An invented commitment.", ("ev-1",), "aligned", "quote_not_in_cited_text"),
    ("The program will support access.", (), "aligned", "no_cited_primary_package"),
    ("No verified CPF/package quotation is available for this driver.", ("ev-1",), "aligned", "absence_status_conflict"),
    ("CPF_QUOTE:ev-1:99", ("ev-1",), "aligned", "invalid_quote_selection"),
    ("CPF_QUOTE:ev-1:1", (), "aligned", "uncited_quote_selection"),
])
def test_quote_diagnostics_identify_reason_and_row_without_content(
    make_valid_result, response, ids, status, reason,
):
    result, _, evidence = reference_case(make_valid_result)
    row = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": response, "evidence_ids": ids, "status": status,
    })
    issues = validate_review(result.model_copy(update={"rra_driver_assessments": (row,)}),
        evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set())
    issue = next(i for i in issues if i.code == "unsupported_cpf_response")
    assert getattr(issue, "quote_reason", None) == reason
    assert getattr(issue, "assessment_index", None) == 0


def test_orchestrator_exposes_only_allowlisted_quote_reason_counts():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator
    events = []
    issues = [
        {"code": "unsupported_cpf_response", "quote_reason": "quote_not_in_cited_text", "assessment_index": 2, "message": "PRIVATE CONTENT"},
        {"code": "unsupported_cpf_response", "quote_reason": "PRIVATE CONTENT"},
    ]
    def validate(context):
        context["validation_issues"] = issues
        return context
    def repair(context, supplied):
        return context
    with pytest.raises(ValueError):
        ReviewOrchestrator(steps=(("validate", validate),), repair=repair).run(
            {}, lambda kind, data: events.append((kind, data)))
    for name in ("repair_start", "repair_failed"):
        data = next(data for kind, data in events if kind == name)
        assert data.get("quote_diagnostics") == [{"reason": "quote_not_in_cited_text", "count": 1}]
        assert "PRIVATE CONTENT" not in str(data)
        assert "assessment_index" not in data


@pytest.mark.parametrize("operation", ["review", "repair"])
def test_quote_index_overflow_falls_back_without_removing_source_text(make_valid_result, monkeypatch, operation):
    import cpf_fcv_reviewer.review_engine as engine
    result, draft, evidence = reference_case(make_valid_result)
    gateway = FixedGateway(draft)
    monkeypatch.setattr(engine, "_estimated_input_tokens", lambda payload:
                        160_001 if "cpf_quote_index" in payload else 100)
    reviewer = ReviewEngine(gateway)
    if operation == "review":
        reviewer.review(EvidencePack(metadata=result.metadata, evidence=tuple(evidence.values()),
                                    diagnostic_entries=()))
        source = gateway.calls[0]["payload"]["evidence_pack"]["evidence"][0]
    else:
        reviewer.repair(result, [{"code": "unsupported_cpf_response"}],
                        evidence_ids=set(evidence), evidence=evidence)
        source = gateway.calls[0]["payload"]["source_grounding_evidence"][0]
    assert source["text"] == evidence["ev-1"].text
    assert "cpf_quote_index" not in gateway.calls[0]["payload"]
    assert len(gateway.calls) == 1


def test_runtime_forwards_safe_quote_diagnostics_to_repair(make_valid_result, monkeypatch):
    from test_runtime_wiring import _runtime_services
    result, _, evidence = reference_case(make_valid_result)
    services = _runtime_services(monkeypatch)
    validate = dict(services["review_orchestrator"].steps)["validate"]
    context = validate({"result": result, "evidence_pack": EvidencePack(
        metadata=result.metadata, evidence=tuple(evidence.values()), diagnostic_entries=()),
        "payload": {}})
    issue = next(i for i in context["validation_issues"] if i["code"] == "unsupported_cpf_response")
    assert issue["quote_reason"] == "quote_not_in_cited_text"
    assert issue["assessment_index"] == 0


def test_oversized_passages_are_not_offered_or_materialized(make_valid_result):
    from cpf_fcv_reviewer.source_grounding import cpf_quote_index, resolve_cpf_response
    result, _, evidence = reference_case(make_valid_result)
    text = "The CPF supports " + "delivery " * 10000
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": text})
    assert cpf_quote_index(evidence) == []
    row = result.rra_driver_assessments[0].model_copy(update={"cpf_response": "CPF_QUOTE:ev-1:1"})
    assert resolve_cpf_response(row, evidence) is None
    assert evidence["ev-1"].text == text
