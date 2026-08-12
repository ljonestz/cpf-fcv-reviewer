from io import BytesIO

from cpf_fcv_reviewer.app import create_app


def test_review_focus_is_one_bounded_untrusted_intake_value():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    focus = "  Please inspect delivery arrangements.  " + ("x" * 5000)

    response = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
            "review_focus": focus,
            "priority_questions": "Is delivery feasible?",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    state = app.extensions["session_store"].get(
        response.get_json()["assessment_id"]
    )
    assert state.payload["review_focus"] == focus.strip()[:4000]
    assert len(state.payload["review_focus"]) == 4000
    assert "priority_questions" not in state.payload
