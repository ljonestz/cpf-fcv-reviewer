from io import BytesIO

from cpf_fcv_reviewer.app import create_app


def test_intake_stores_only_confirmed_deduplicated_questions():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    client = app.test_client()

    response = client.post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
            "priority_questions": [
                "Does the results framework track geographic distribution?",
                "Is the partnership logic credible?",
                "is the partnership logic credible?",
                "Please pay attention to spillovers.",
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assessment_id = response.get_json()["assessment_id"]
    state = app.extensions["session_store"].get(assessment_id)
    assert state.payload["priority_questions"] == (
        "Does the results framework track geographic distribution?",
        "Is the partnership logic credible?",
    )
