"""Synthetic regressions for the dated-state and wrong-page audit failures."""
from cpf_fcv_reviewer.contracts import DocumentRole
from cpf_fcv_reviewer.validators import validate_review


def grounded_case(make_valid_result):
    result, evidence = make_valid_result
    item = evidence["ev-1"].model_copy(update={
        "document_role": DocumentRole.PRIMARY,
        "text": "The program will support access.",
    })
    return result, {"ev-1": item}


def codes(result, evidence):
    return {issue.code for issue in validate_review(result, evidence_ids=set(evidence),
                                                    evidence=evidence, prohibited_terms=set())}


def test_wrong_physical_page_for_quoted_target_is_blocked(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0]
    bad_locator = area.target_locator.model_copy(update={"page": 15})
    result = result.model_copy(update={"priority_areas": (
        area.model_copy(update={"target_locator": bad_locator}),)})
    assert "target_locator_mismatch" in codes(result, evidence)


def test_target_quote_must_occur_at_its_supplied_location(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0]
    result = result.model_copy(update={"priority_areas": (area.model_copy(update={
        "target_locator": area.target_locator.model_copy(update={"excerpt": "Invented promise."})}),)})
    assert "target_locator_mismatch" in codes(result, evidence)


def test_valid_target_remains_accepted(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    assert "target_locator_mismatch" not in codes(result, evidence)


def test_ongoing_transition_cannot_be_carried_forward_from_old_rra(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={
        "recommended_action": "Adapt delivery to the ongoing CNRD transition."})
    result = result.model_copy(update={"priority_areas": (area,)})
    issues = validate_review(result, evidence_ids=set(evidence), evidence=evidence, prohibited_terms=set())
    assert any(i.code == "unsupported_current_state" and i.severity == "fatal" for i in issues)


def test_historical_or_conditional_transition_is_not_a_current_assertion(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={
        "assessment": "The historical RRA describes the ongoing CNRD transition in 2023.",
        "recommended_action": "Verify whether the ongoing political transition remains relevant."})
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "unsupported_current_state" not in codes(result, evidence)


def test_unrelated_uncertainty_does_not_qualify_current_assertion(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={
        "assessment": "The ongoing CNRD transition creates uncertain delivery conditions."})
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "unsupported_current_state" in codes(result, evidence)


def test_unrelated_if_clause_does_not_qualify_current_assertion(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={
        "assessment": "During the ongoing CNRD transition, increase coverage if unrest intensifies."})
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "unsupported_current_state" in codes(result, evidence)
