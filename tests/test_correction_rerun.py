from cpf_fcv_reviewer.app import create_app
from tests.test_routes import create_review


def test_correction_creates_child_run_with_label_parent_and_no_stale_result():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    client = app.test_client()
    parent = create_review(client)
    app.extensions["session_store"].update(
        parent["assessment_id"],
        result={"stale": True},
        evidence_by_id={"stale": {"evidence_id": "stale"}},
        status="complete",
    )

    response = client.post(
        f"/api/reviews/{parent['assessment_id']}/corrections",
        json={
            "text": "The cited reform was adopted in July.",
            "affected_priority_area_id": "pa-1",
            "rationale": "Country-team update",
        },
    )

    assert response.status_code == 201
    child = response.get_json()
    assert child["assessment_id"] != parent["assessment_id"]
    assert child["parent_assessment_id"] == parent["assessment_id"]
    assert child["event_url"].endswith("/events")
    assert child["result_url"].endswith("/result")

    state = app.extensions["session_store"].get(child["assessment_id"])
    correction = state.payload["corrections"][-1]
    assert correction["label"] == "User-provided correction"
    assert correction["independently_supported"] is False
    assert correction["text"] == "The cited reform was adopted in July."
    assert correction["affected_priority_area_id"] == "pa-1"
    assert correction["correction_id"]
    assert correction["created_at"].endswith("+00:00")
    assert state.payload["parent_assessment_id"] == parent["assessment_id"]
    assert state.payload["status"] == "created"
    assert "result" not in state.payload
    assert "evidence_by_id" not in state.payload

    parent_state = app.extensions["session_store"].get(parent["assessment_id"])
    assert parent_state.payload["result"] == {"stale": True}
