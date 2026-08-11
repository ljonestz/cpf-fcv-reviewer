from io import BytesIO

from cpf_fcv_reviewer.app import create_app


def create_review(client):
    response = client.post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.get_json()


def make_app():
    return create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})


def test_create_review_returns_assessment_and_event_urls():
    payload = create_review(make_app().test_client())

    assert payload["assessment_id"]
    assert payload["event_url"].endswith("/events")
    assert payload["result_url"].endswith("/result")


def test_primary_document_is_required():
    response = (
        make_app()
        .test_client()
        .post(
            "/api/reviews",
            data={"country": "Testland", "review_stage": "concept_review"},
        )
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "A primary CPF/CEN is required."


def test_reset_removes_active_review():
    client = make_app().test_client()
    created = create_review(client)

    assert client.delete(f"/api/reviews/{created['assessment_id']}").status_code == 204
    assert client.get(created["result_url"]).status_code == 410


def test_correction_is_labelled_and_persisted_in_child_state():
    app = make_app()
    client = app.test_client()
    created = create_review(client)

    response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json={
            "text": "  Correct the delivery-risk description.  ",
            "affected_finding_id": "f-1",
        },
    )

    assert response.status_code == 201
    child = response.get_json()
    state = app.extensions["session_store"].get(child["assessment_id"])
    assert state.payload["corrections"][-1]["label"] == "User-provided correction"
    assert state.payload["corrections"][-1]["text"] == "Correct the delivery-risk description."
    assert state.payload["parent_assessment_id"] == created["assessment_id"]
    assert state.payload["status"] == "created"


def test_blank_correction_is_rejected_without_mutating_state():
    app = make_app()
    client = app.test_client()
    created = create_review(client)

    response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json={"text": "   "},
    )

    assert response.status_code == 400
    state = app.extensions["session_store"].get(created["assessment_id"])
    assert state.payload["corrections"] == []


def test_event_stream_stops_after_terminal_event():
    app = make_app()
    client = app.test_client()
    created = create_review(client)
    app.extensions["session_store"].emit(
        created["assessment_id"],
        "run_complete",
        {"repair_count": 0},
    )

    response = client.get(created["event_url"])

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: run_complete" in response.get_data(as_text=True)
