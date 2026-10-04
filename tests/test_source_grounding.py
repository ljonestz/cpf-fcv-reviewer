"""Synthetic regressions for the dated-state and wrong-page audit failures."""
import pytest

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


def test_selected_target_copies_exact_source_and_coordinates(make_valid_result):
    from cpf_fcv_reviewer.review_engine import _resolve_cited_sources
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0]
    selected = area.target_locator.model_copy(update={
        "excerpt": "CPF_QUOTE:ev-1:1", "page": 99, "document_title": "Wrong.pdf"})
    result = result.model_copy(update={"priority_areas": (area.model_copy(
        update={"target_locator": selected}),)})
    resolved = _resolve_cited_sources(result, evidence)
    target = resolved.priority_areas[0].target_locator
    assert target.excerpt == "The program will support access."
    assert target.page == evidence["ev-1"].locator.page
    assert target.document_title == evidence["ev-1"].locator.document_title
    assert "target_locator_mismatch" not in codes(resolved, evidence)


@pytest.mark.parametrize("selection", ["CPF_QUOTE:uncited:1", "CPF_QUOTE:ev-1:99"])
def test_unknown_or_uncited_target_selection_remains_blocking(make_valid_result, selection):
    from cpf_fcv_reviewer.review_engine import _resolve_cited_sources
    result, evidence = grounded_case(make_valid_result)
    evidence["uncited"] = evidence["ev-1"].model_copy(update={"evidence_id": "uncited"})
    area = result.priority_areas[0]
    result = result.model_copy(update={"priority_areas": (area.model_copy(update={
        "target_locator": area.target_locator.model_copy(update={"excerpt": selection})}),)})
    assert "target_locator_mismatch" in codes(_resolve_cited_sources(result, evidence), evidence)


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


def test_target_cannot_borrow_an_uncited_primary_source(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    context = evidence["ev-1"].model_copy(update={
        "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
    })
    evidence["context-1"] = context
    area = result.priority_areas[0].model_copy(update={"evidence_ids": ("context-1",)})
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "target_locator_mismatch" in codes(result, evidence)


@pytest.mark.parametrize(
    ("excerpt", "is_paraphrase", "reason"),
    [
        ("An invented promise.", True, "paraphrase_unverified"),
        ("!!!", False, "empty_excerpt"),
        ("access", False, "excerpt_mismatch"),
    ],
)
def test_excerpt_cannot_bypass_grounding(make_valid_result, excerpt, is_paraphrase, reason):
    result, evidence = grounded_case(make_valid_result)
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={
        "text": "The program will support accessibility.",
    })
    area = result.priority_areas[0]
    area = area.model_copy(update={"target_locator": area.target_locator.model_copy(update={
        "excerpt": excerpt, "is_paraphrase": is_paraphrase,
    })})
    result = result.model_copy(update={"priority_areas": (area,)})
    issues = validate_review(result, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    issue = next((i for i in issues if i.code == "target_locator_mismatch"), None)
    assert issue is not None
    assert issue.locator_reason == reason


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"document_title": "Another document.pdf"}, "document_not_cited"),
        ({"page": 99}, "coordinate_not_cited"),
        ({"excerpt": "An invented promise."}, "excerpt_mismatch"),
    ],
)
def test_locator_failure_has_a_content_free_reason(make_valid_result, changes, reason):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0]
    area = area.model_copy(update={
        "target_locator": area.target_locator.model_copy(update=changes),
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    issues = validate_review(result, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    issue = next(i for i in issues if i.code == "target_locator_mismatch")
    assert issue.locator_reason == reason


@pytest.mark.parametrize("amount", ["3.0 percent", "30%"])
def test_invented_percentage_recommendation_is_fatal(make_valid_result, amount):
    result, evidence = grounded_case(make_valid_result)
    area = result.priority_areas[0].model_copy(update={
        "recommended_action": f"Set a trigger of {amount} for program recalibration.",
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    issues = validate_review(result, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    assert any(i.code == "unsupported_numeric_recommendation" and i.severity == "fatal"
               for i in issues)


def test_percentage_from_context_does_not_establish_a_cpf_target(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    evidence["context-1"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
        "text": "The historical diagnostic reports 30 percent.",
    })
    area = result.priority_areas[0].model_copy(update={
        "evidence_ids": ("ev-1", "context-1"),
        "recommended_action": "Set a 30 percent CPF target.",
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "unsupported_numeric_recommendation" in codes(result, evidence)


def test_source_percentage_and_target_setting_method_remain_allowed(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={
        "text": "The program will support access. The agreed target is 20 percent.",
    })
    area = result.priority_areas[0].model_copy(update={
        "recommended_action": "Clarify the existing 20.0% target and establish a baseline.",
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    assert "unsupported_numeric_recommendation" not in codes(result, evidence)


@pytest.mark.parametrize("role", [DocumentRole.PRIMARY, DocumentRole.PACKAGE])
def test_cpf_response_accepts_a_cited_program_quote(make_valid_result, role):
    result, evidence = grounded_case(make_valid_result)
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"document_role": role})
    row = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The program will support access.",
    })
    result = result.model_copy(update={"rra_driver_assessments": (row,)})
    assert "unsupported_cpf_response" not in codes(result, evidence)


@pytest.mark.parametrize("response", ["The CPF funds prosecutions.", "!!!"])
def test_cpf_response_rejects_unverified_claims(make_valid_result, response):
    result, evidence = grounded_case(make_valid_result)
    row = result.rra_driver_assessments[0].model_copy(update={"cpf_response": response})
    result = result.model_copy(update={"rra_driver_assessments": (row,)})
    issues = validate_review(result, evidence_ids=set(evidence),
                             evidence=evidence, prohibited_terms=set())
    assert any(i.code == "unsupported_cpf_response" and i.severity == "fatal" for i in issues)


def test_cpf_response_cannot_use_an_uncited_or_contextual_quote(make_valid_result):
    result, evidence = grounded_case(make_valid_result)
    evidence["context-1"] = evidence["ev-1"].model_copy(update={
        "evidence_id": "context-1", "document_role": DocumentRole.CONTEXT,
    })
    row = result.rra_driver_assessments[0].model_copy(update={
        "cpf_response": "The program will support access.", "evidence_ids": ("context-1",),
    })
    result = result.model_copy(update={"rra_driver_assessments": (row,)})
    assert "unsupported_cpf_response" in codes(result, evidence)


@pytest.mark.parametrize("status", ["aligned", "partially_aligned", "not_evidenced",
                                  "not_assessable"])
def test_only_absence_or_unassessable_rows_can_disclose_no_quote(make_valid_result, status):
    from cpf_fcv_reviewer.contracts import AssessmentStatus
    result, evidence = grounded_case(make_valid_result)
    row = result.rra_driver_assessments[0].model_copy(update={
        "status": AssessmentStatus(status),
        "cpf_response": "No verified CPF/package quotation is available for this driver.",
    })
    result = result.model_copy(update={"rra_driver_assessments": (row,)})
    assert ("unsupported_cpf_response" in codes(result, evidence)) == (
        status in {"aligned", "partially_aligned"}
    )


@pytest.mark.parametrize("response", [
    "No verified CPF/package quotation is available for this driver.",
    "NO VERIFIED CPF/package quotation is available for this driver",
])
def test_no_quote_disclosure_cannot_be_laundered_through_uploaded_text(
    make_valid_result, response,
):
    result, evidence = grounded_case(make_valid_result)
    evidence["ev-1"] = evidence["ev-1"].model_copy(update={"text": response})
    row = result.rra_driver_assessments[0].model_copy(update={
        "status": "aligned", "cpf_response": response,
    })
    result = result.model_copy(update={"rra_driver_assessments": (row,)})
    assert "unsupported_cpf_response" in codes(result, evidence)
