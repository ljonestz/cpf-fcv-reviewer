"""The shared assistant tailors the current email without changing findings."""
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_smoke_app
from cpf_fcv_reviewer.email_draft import validate_email_refinement


def test_results_offer_copy_and_one_shared_assistant():
    html = Path("src/cpf_fcv_reviewer/templates/index.html").read_text(encoding="utf-8")
    for removed in ("pilot-feedback", "feedback-form", "save-email-wording",
                    "download-email", "use-generated-email", "correction-text"):
        assert f'id="{removed}"' not in html
    assert 'id="copy-peer-email"' in html
    assert 'id="assistant-mode"' not in html
    assert 'id="assistant-suggestion"' not in html
    assert "FOLLOW-ON REVIEW ASSISTANT" not in html
    for choice in ("tone", "focus", "Condense", "Explain"):
        assert choice in html


def test_feedback_collection_is_removed(completed_coordinator_review):
    _, client, assessment_id = completed_coordinator_review
    assert client.post(f"/api/reviews/{assessment_id}/feedback", json={}).status_code == 404
    assert "feedback" not in client.get(f"/api/reviews/{assessment_id}/result").json


def test_tailoring_uses_current_email_and_keeps_findings(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    before = app.extensions["session_store"].get(assessment_id).payload["result"]
    calls = []
    revised = "Dear colleagues,\n\nPlease clarify the delivery logic."

    class Gateway:
        def stream(self, **kwargs):
            calls.append(kwargs)
            yield revised

    app.extensions["follow_on_gateway"] = Gateway()
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Make the tone more direct.", "mode": "tailor_email",
        "email_text": "Dear colleagues,\n\nCurrent coordinator wording.",
    })
    assert response.status_code == 200
    assert b"event: done" in response.data
    assert calls[0]["review"]["current_email"].endswith("Current coordinator wording.")
    assert calls[0]["review"]["follow_on_task"] == "tailor_email"
    after = client.get(f"/api/reviews/{assessment_id}/result").json
    assert after["email_text"] == revised
    assert app.extensions["session_store"].get(assessment_id).payload["result"] == before


@pytest.mark.parametrize("action", ["answer", "tailor_email", "correct_review"])
def test_prose_query_routes_in_one_call_and_hides_control_line(
    completed_coordinator_review, action,
):
    app, client, assessment_id = completed_coordinator_review
    before = app.extensions["session_store"].get(assessment_id).payload["result"]
    original = client.get(f"/api/reviews/{assessment_id}/result").json["email_text"]
    calls = []
    prose = "Dear colleagues,\n\nPlease clarify delivery arrangements."

    class Gateway:
        def stream(self, **kwargs):
            calls.append(kwargs)
            yield "ACT"
            yield f"ION: {action}\n" + prose[:8]
            yield prose[8:]

    app.extensions["follow_on_gateway"] = Gateway()
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Please reconsider this finding.", "mode": "query",
        "email_text": "Latest coordinator wording.",
    })
    assert b"event: done" in response.data
    assert b"ACTION:" not in response.data
    assert f'"action": "{action}"'.encode() in response.data
    assert len(calls) == 1
    assert calls[0]["review"]["current_email"] == "Latest coordinator wording."
    assert calls[0]["review"]["follow_on_task"] == "query"
    assert client.get(f"/api/reviews/{assessment_id}/result").json["email_text"] == (
        prose if action == "tailor_email" else original
    )
    assert app.extensions["session_store"].get(assessment_id).payload["result"] == before
    history = client.get(f"/api/reviews/{assessment_id}/assistant").json
    assert history[-1]["content"] == prose


@pytest.mark.parametrize("header", ["", "ACTION: deploy", "ACTION: tailor_email" + "x" * 200])
def test_query_with_invalid_action_preserves_comments(completed_coordinator_review, header):
    app, client, assessment_id = completed_coordinator_review
    original = client.get(f"/api/reviews/{assessment_id}/result").json["email_text"]

    class Gateway:
        def stream(self, **kwargs):
            yield header + "\nDraft response."

    app.extensions["follow_on_gateway"] = Gateway()
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Condense the comments.", "mode": "query",
    })
    assert b"event: error" in response.data
    assert client.get(f"/api/reviews/{assessment_id}/result").json["email_text"] == original


@pytest.mark.parametrize("fields", [
    {"mode": "unknown"}, {"mode": "tailor_email", "email_text": 3},
    {"mode": "tailor_email", "email_text": "x" * 12001},
])
def test_assistant_validates_refinement_inputs(completed_coordinator_review, fields):
    _, client, assessment_id = completed_coordinator_review
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Condense the email.", **fields,
    })
    assert response.status_code == 400


@pytest.mark.parametrize("draft", [
    "The CPF complies with PC14.", "Allocate 987654 grants.",
    "Thank you.\nShubham", "Replace all objectives and rebuild the entire delivery model.",
    "Refer to primary-001.", "Dear colleagues,\n\nCreate a new delivery mechanism for the program.",
])
def test_invalid_refinement_preserves_existing_comments(completed_coordinator_review, draft):
    app, client, assessment_id = completed_coordinator_review
    before = client.get(f"/api/reviews/{assessment_id}/result").json["email_text"]

    class Gateway:
        def stream(self, **kwargs):
            yield draft

    app.extensions["follow_on_gateway"] = Gateway()
    state = app.extensions["session_store"].get(assessment_id)
    result = state.payload["result"]
    result["metadata"]["review_stage"] = "finalization"
    app.extensions["session_store"].update(assessment_id, result=result)
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Revise these comments.", "mode": "tailor_email",
    })
    assert b"event: error" in response.data
    assert client.get(f"/api/reviews/{assessment_id}/result").json["email_text"] == before


def test_refinement_allows_numbered_comments(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    numbered = "Dear colleagues,\n\n901. Clarify delivery.\n902. Connect the diagnostics."

    class Gateway:
        def stream(self, **kwargs):
            yield numbered

    app.extensions["follow_on_gateway"] = Gateway()
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Use numbered comments.", "mode": "tailor_email",
    })
    assert b"event: done" in response.data
    assert client.get(f"/api/reviews/{assessment_id}/result").json["email_text"] == numbered


def test_refinement_rejects_invalid_cached_draft_safely(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    app.extensions["session_store"].update(assessment_id, peer_email={"opening": 3})
    response = client.post(f"/api/reviews/{assessment_id}/assistant", json={
        "message": "Condense the comments.", "mode": "tailor_email",
    })
    assert response.status_code == 409


def test_disclaimer_matches_screener_opening_and_is_exported(completed_coordinator_review):
    _, client, assessment_id = completed_coordinator_review
    html = create_smoke_app(start_background_runs=False).test_client().get("/").text
    assert "Be aware: LLMs are not magic, and neither is the CPF FCV Reviewer." in html
    assert "review stage" in html and "OPCS" in html
    for view in ("detailed", "summary"):
        response = client.get(f"/api/reviews/{assessment_id}/export.docx?view={view}")
        text = "\n".join(p.text for p in Document(BytesIO(response.data)).paragraphs)
        assert "LLMs are not magic" in text
        assert "review stage" in text


def test_refinement_checks_claims_against_applicable_current_sources(make_valid_result):
    from datetime import date

    from cpf_fcv_reviewer.contracts import EvidenceItem

    result, evidence = make_valid_result
    for key, quote in (
        ("current-conflict", "Conflict increased in Benin."),
        ("current-displacement", "Displacement increased in Benin."),
    ):
        evidence[key] = EvidenceItem(
            evidence_id=key, evidence_type="current_context", text=quote,
            supporting_quote=quote, source_title="Synthetic source",
            source_publisher="World Bank", source_date=date(2026, 10, 1),
            source_url="https://example.org/" + key, confidence="high",
        )
    validate_email_refinement(
        result, "Dear colleagues,\n\nConflict increased in Benin. Clarify existing delivery.",
        evidence=evidence,
    )
    for unsupported in (
        "Conflict decreased in Benin.", "Political tensions increased in Benin.",
        "Conflict increased in Benin. Displacement decreased in Benin.",
    ):
        with pytest.raises(ValueError):
            validate_email_refinement(result, unsupported, evidence=evidence)


@pytest.mark.parametrize("prefix", ["Dear colleagues,\n\n", "Thank you for sharing the draft. "])
def test_refinement_rejects_architecture_changes_after_opening(make_valid_result, prefix):
    result, evidence = make_valid_result
    with pytest.raises(ValueError):
        validate_email_refinement(
            result, prefix + "Create a new delivery mechanism for the program.", evidence=evidence,
        )
