"""Feedback is optional evaluation material with the review's lifecycle."""
from datetime import timedelta
from io import BytesIO

import pytest

from cpf_fcv_reviewer.routes import run_assessment
from cpf_fcv_reviewer.session_store import SessionExpired


def test_feedback_accepts_comment_only(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    response = client.post(f"/api/reviews/{assessment_id}/feedback", json={
        "comment": "Useful, but the selectivity point needs qualification.",
    })
    assert response.status_code == 200
    assert app.extensions["session_store"].get(assessment_id).payload["feedback"]["comment"]
    assert client.get(f"/api/reviews/{assessment_id}/export.docx").status_code == 200


def test_feedback_rejects_invalid_rating(completed_coordinator_review):
    _, client, assessment_id = completed_coordinator_review
    response = client.post(f"/api/reviews/{assessment_id}/feedback", json={"accuracy": "perfect"})
    assert response.status_code == 400


def test_final_comments_do_not_enter_corrected_review(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    final = b"Final departmental comments. SENTINEL_FEEDBACK_ONLY.\n" * 10
    response = client.post(f"/api/reviews/{assessment_id}/feedback", data={
        "final_comments": (BytesIO(final), "Final comments.txt"),
    })
    assert response.status_code == 200
    feedback = app.extensions["session_store"].get(assessment_id).payload["feedback"]
    assert feedback["final_comments"]["bytes"] == final
    child = client.post(f"/api/reviews/{assessment_id}/corrections", json={
        "text": "Please qualify this assessment.",
    })
    child_id = child.json["assessment_id"]
    run_assessment(app, child_id)
    child_payload = app.extensions["session_store"].get(child_id).payload
    assert "feedback" not in child_payload
    assert all(
        "SENTINEL_FEEDBACK_ONLY" not in item["text"]
        for item in child_payload["evidence_by_id"].values()
    )


def test_feedback_rejects_unusable_final_file(completed_coordinator_review):
    _, client, assessment_id = completed_coordinator_review
    response = client.post(f"/api/reviews/{assessment_id}/feedback", data={
        "final_comments": (BytesIO(b"binary"), "final.exe"),
    })
    assert response.status_code == 400


def test_feedback_expires_with_the_review(completed_coordinator_review):
    app, client, assessment_id = completed_coordinator_review
    assert client.post(f"/api/reviews/{assessment_id}/feedback", json={
        "usefulness": "useful",
    }).status_code == 200
    store = app.extensions["session_store"]
    expiry = store.get(assessment_id).expires_at
    store._clock = lambda: expiry + timedelta(seconds=1)
    assert client.get(f"/api/reviews/{assessment_id}/result").status_code == 410
    with pytest.raises(SessionExpired):
        store.get(assessment_id)
