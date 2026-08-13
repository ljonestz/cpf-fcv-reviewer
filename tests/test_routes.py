from io import BytesIO

import pytest

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.country_detection import (
    COUNTRY_DETECTION_MAX_ARCHIVE_MEMBERS,
    COUNTRY_DETECTION_MAX_CHARACTERS,
    COUNTRY_DETECTION_MAX_PDF_PAGES,
    COUNTRY_DETECTION_MAX_SEGMENTS,
    COUNTRY_DETECTION_MAX_UNCOMPRESSED_BYTES,
    COUNTRY_DETECTION_MAX_UPLOAD_BYTES,
)
from cpf_fcv_reviewer.extraction import (
    ExtractedDocument,
    ExtractedSegment,
    ExtractionLimitExceeded,
)
from cpf_fcv_reviewer.research_controller import (
    InsufficientResearch,
    MalformedResearch,
    ResearchConfigurationError,
    ResearchProviderFailure,
    ResearchSourceRejected,
    ResearchTimeout,
)
from cpf_fcv_reviewer.routes import run_assessment


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


class FailingOrchestrator:
    def __init__(self, error):
        self.error = error

    def run(self, context, emit):
        context["result"] = {"sensitive": "partial result"}
        context["evidence_by_id"] = {"secret": "partial evidence"}
        context["validation_issues"] = ["secret validation detail"]
        emit("run_failed", {"error": "research_provider_failed"})
        raise self.error


def failed_assessment(app, error=None):
    if error is None:
        error = ResearchProviderFailure("provider secret")
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "created",
            "country": "Testland",
            "cpf": {"name": "cpf.txt", "bytes": b"original upload"},
            "corrections": [{"correction_id": "correction-1"}],
        }
    )
    app.extensions["review_orchestrator"] = FailingOrchestrator(error)
    run_assessment(app, assessment_id)
    return assessment_id


def test_failed_research_stores_only_safe_code_and_preserves_uploads():
    app = make_app()
    assessment_id = failed_assessment(app)

    payload = app.extensions["session_store"].get(assessment_id).payload
    assert payload["status"] == "failed"
    assert payload["failure_code"] == "research_provider_failed"
    assert payload["cpf"]["bytes"] == b"original upload"
    assert "result" not in payload
    assert "evidence_by_id" not in payload
    assert "validation_issues" not in payload
    assert "provider secret" not in repr(payload)


def test_retry_research_resets_failed_state_without_reupload():
    app = make_app()
    assessment_id = failed_assessment(app)
    app.extensions["session_store"].update(
        assessment_id,
        result={"stale": True},
        evidence_by_id={"stale": True},
        validation_issues=["stale"],
        partial_research={"stale": True},
    )

    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/retry-research"
    )

    assert response.status_code == 202
    assert response.get_json() == {
        "assessment_id": assessment_id,
        "event_url": f"/api/reviews/{assessment_id}/events",
        "result_url": f"/api/reviews/{assessment_id}/result",
    }
    payload = app.extensions["session_store"].get(assessment_id).payload
    assert payload["status"] == "created"
    assert payload["cpf"]["bytes"] == b"original upload"
    assert payload["corrections"] == [{"correction_id": "correction-1"}]
    for key in (
        "failure_code",
        "result",
        "evidence_by_id",
        "validation_issues",
        "partial_research",
    ):
        assert key not in payload
    assert app.extensions["session_store"].next_event(assessment_id) == {
        "type": "run_started",
        "data": {},
    }
    assert app.extensions["session_store"].next_event(assessment_id) is None


def test_failed_and_retried_research_never_exposes_partial_result():
    app = make_app()
    assessment_id = failed_assessment(app)
    client = app.test_client()

    failed_result = client.get(f"/api/reviews/{assessment_id}/result")
    retry = client.post(f"/api/reviews/{assessment_id}/retry-research")
    retried_result = client.get(f"/api/reviews/{assessment_id}/result")

    assert failed_result.status_code == 202
    assert failed_result.get_json() == {"status": "failed"}
    assert retry.status_code == 202
    assert retried_result.status_code == 202
    assert retried_result.get_json() == {"status": "created"}
    assert "result" not in failed_result.get_data(as_text=True)
    assert "result" not in retried_result.get_data(as_text=True)


@pytest.mark.parametrize(
    "status,failure_code",
    [
        ("complete", "research_timeout"),
        ("created", "research_timeout"),
        ("running", "research_timeout"),
        ("failed", "review_failed"),
        ("failed", ResearchConfigurationError.failure_code),
        ("failed", ResearchSourceRejected.failure_code),
    ],
)
def test_retry_research_rejects_unavailable_states(status, failure_code):
    app = make_app()
    assessment_id = app.extensions["session_store"].create(
        {"status": status, "failure_code": failure_code}
    )

    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/retry-research"
    )

    assert response.status_code == 409
    assert response.get_json() == {"error": "Research retry is unavailable."}


def test_retry_research_missing_assessment_uses_expired_response():
    response = make_app().test_client().post(
        "/api/reviews/missing/retry-research"
    )

    assert response.status_code == 410
    assert response.get_json() == {"error": "Assessment expired."}


def test_retry_research_duplicate_request_is_rejected():
    app = make_app()
    assessment_id = failed_assessment(app)
    client = app.test_client()

    assert client.post(f"/api/reviews/{assessment_id}/retry-research").status_code == 202
    response = client.post(f"/api/reviews/{assessment_id}/retry-research")

    assert response.status_code == 409
    assert response.get_json() == {"error": "Research retry is unavailable."}


def test_retry_research_starts_daemon_with_same_assessment_when_enabled(monkeypatch):
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": True})
    assessment_id = failed_assessment(app)
    started = []

    class RecordingThread:
        def __init__(self, *, target, args, daemon):
            started.append((target, args, daemon))

        def start(self):
            started.append("started")

    monkeypatch.setattr("cpf_fcv_reviewer.routes.Thread", RecordingThread)

    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/retry-research"
    )

    assert response.status_code == 202
    assert started[0][0] is run_assessment
    assert started[0][1] == (app, assessment_id)
    assert started[0][2] is True
    assert started[1] == "started"


@pytest.mark.parametrize(
    "error",
    [
        InsufficientResearch("secret"),
        MalformedResearch("secret"),
        ResearchTimeout("secret"),
    ],
)
def test_retryable_research_failures_are_recorded_without_exception_text(error):
    app = make_app()
    assessment_id = failed_assessment(app, error)
    payload = app.extensions["session_store"].get(assessment_id).payload

    assert payload["failure_code"].startswith("research_")
    assert "secret" not in repr(payload)


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


def test_create_review_rejects_blank_country():
    response = make_app().test_client().post(
        "/api/reviews",
        data={
            "country": "   ",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Country is required."}


@pytest.mark.parametrize("country", ["x" * 101, "Chad\x00"])
def test_create_review_rejects_unsafe_confirmed_country(country):
    response = make_app().test_client().post(
        "/api/reviews",
        data={
            "country": country,
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Country is invalid."}


def test_detect_country_uses_only_primary_upload_without_creating_state():
    app = make_app()
    client = app.test_client()
    secret = "DO NOT RETURN THIS SUPPORTING CONTENT"

    response = client.post(
        "/api/detect-country",
        data={
            "cpf": (
                BytesIO(
                    b"Country Partnership Framework for the Republic of Chad for FY26-FY30\n"
                    + b"Readable CPF content " * 20
                ),
                "chad-cpf.txt",
            ),
            "package_documents": [(BytesIO(secret.encode()), "secret.txt")],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "country": "Chad",
        "requires_confirmation": False,
    }
    assert secret not in response.get_data(as_text=True)
    assert app.extensions["session_store"].count() == 0


def test_detect_country_rejects_missing_or_unreadable_primary():
    app = make_app()
    client = app.test_client()

    for data in (
        {},
        {"cpf": (BytesIO(b"too short"), "cpf.txt")},
        {"cpf": (BytesIO(b"not a valid PDF"), "cpf.pdf")},
    ):
        response = client.post(
            "/api/detect-country",
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "A readable primary CPF/CEN is required."
        }
        assert "too short" not in response.get_data(as_text=True)
        assert app.extensions["session_store"].count() == 0


def test_detect_country_rejects_detector_oversized_upload():
    response = make_app().test_client().post(
        "/api/detect-country",
        data={
            "cpf": (
                BytesIO(b"x" * (COUNTRY_DETECTION_MAX_UPLOAD_BYTES + 1)),
                "cpf.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "A readable primary CPF/CEN is required."
    }


def test_detect_country_passes_detector_extraction_budgets(monkeypatch):
    captured = {}

    def fake_extract(data, name, **kwargs):
        captured.update(kwargs)
        return ExtractedDocument(
            name,
            (
                ExtractedSegment(
                    "Country Partnership Framework for Chad for FY26\n" + "x" * 120,
                    None,
                    None,
                    "full text",
                ),
            ),
            (),
        )

    monkeypatch.setattr("cpf_fcv_reviewer.routes.extract_document", fake_extract)
    response = make_app().test_client().post(
        "/api/detect-country",
        data={"cpf": (BytesIO(b"bounded input"), "cpf.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {"country": "Chad", "requires_confirmation": False}
    assert captured == {
        "max_pdf_pages": COUNTRY_DETECTION_MAX_PDF_PAGES,
        "max_segments": COUNTRY_DETECTION_MAX_SEGMENTS,
        "max_characters": COUNTRY_DETECTION_MAX_CHARACTERS,
        "max_uncompressed_bytes": COUNTRY_DETECTION_MAX_UNCOMPRESSED_BYTES,
        "max_archive_members": COUNTRY_DETECTION_MAX_ARCHIVE_MEMBERS,
    }


def test_detect_country_returns_generic_error_when_extraction_budget_is_exceeded(
    monkeypatch,
):
    def limited_extract(*args, **kwargs):
        raise ExtractionLimitExceeded("internal detail must not be exposed")

    monkeypatch.setattr("cpf_fcv_reviewer.routes.extract_document", limited_extract)
    response = make_app().test_client().post(
        "/api/detect-country",
        data={"cpf": (BytesIO(b"bounded input"), "cpf.docx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "A readable primary CPF/CEN is required."
    }


def test_create_review_preserves_upload_buckets_and_detail_level():
    app = make_app()
    response = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "detail_level": "in_depth",
            "cpf": (BytesIO(b"CPF text " * 30), "cpf.txt"),
            "package_documents": [
                (BytesIO(b"Results matrix"), "results.txt"),
                (BytesIO(b"Learning review"), "learning.txt"),
            ],
            "context_documents": [(BytesIO(b"RRA context"), "rra.txt")],
            "review_focus": "Pay particular attention to delivery arrangements.",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    state = app.extensions["session_store"].get(
        response.get_json()["assessment_id"]
    )
    assert state.payload["detail_level"] == "in_depth"
    assert [item["name"] for item in state.payload["package_documents"]] == [
        "results.txt",
        "learning.txt",
    ]
    assert state.payload["context_documents"][0]["name"] == "rra.txt"
    assert "delivery arrangements" in state.payload["review_focus"]
    assert "priority_questions" not in state.payload


def test_create_review_rejects_unsupported_detail_level():
    response = make_app().test_client().post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "detail_level": "verbose",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported detail level."}


def test_reset_removes_active_review():
    client = make_app().test_client()
    created = create_review(client)

    assert client.delete(f"/api/reviews/{created['assessment_id']}").status_code == 204
    assert client.get(created["result_url"]).status_code == 410


def test_reset_after_correction_purges_the_entire_assessment_lineage():
    app = make_app()
    client = app.test_client()
    parent = create_review(client)
    child = client.post(
        f"/api/reviews/{parent['assessment_id']}/corrections",
        json={"text": "Correct the delivery-risk description."},
    ).get_json()
    grandchild = client.post(
        f"/api/reviews/{child['assessment_id']}/corrections",
        json={"text": "Correct the implementation-risk description."},
    ).get_json()
    unrelated = create_review(client)

    response = client.delete(f"/api/reviews/{grandchild['assessment_id']}")

    assert response.status_code == 204
    assert app.extensions["session_store"].count() == 1
    assert client.get(parent["result_url"]).status_code == 410
    assert client.get(child["result_url"]).status_code == 410
    assert client.get(grandchild["result_url"]).status_code == 410
    assert client.get(unrelated["result_url"]).status_code == 202


def test_correction_is_labelled_and_persisted_in_child_state():
    app = make_app()
    client = app.test_client()
    created = create_review(client)

    response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json={
            "text": "  Correct the delivery-risk description.  ",
            "affected_priority_area_id": "  pa-1  ",
            "rationale": "  Country-team update  ",
        },
    )

    assert response.status_code == 201
    child = response.get_json()
    state = app.extensions["session_store"].get(child["assessment_id"])
    assert state.payload["corrections"][-1]["label"] == "User-provided correction"
    assert state.payload["corrections"][-1]["text"] == "Correct the delivery-risk description."
    assert state.payload["corrections"][-1]["affected_priority_area_id"] == "pa-1"
    assert state.payload["corrections"][-1]["rationale"] == "Country-team update"
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


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"text": "valid", "affected_priority_area_id": 17}, "Correction details are invalid."),
        ({"text": "valid", "rationale": ["not a string"]}, "Correction details are invalid."),
        (
            {"text": "valid", "affected_priority_area_id": "x" * 201},
            "Correction details are invalid.",
        ),
        ({"text": "valid", "rationale": "x" * 1001}, "Correction details are invalid."),
        ({"text": "x" * 2001}, "Correction text is too long."),
        (
            {"text": "valid", "affected_finding_id": "f-1"},
            "Legacy correction fields are not supported.",
        ),
    ],
)
def test_invalid_correction_details_are_rejected_without_child_or_mutation(
    payload, error
):
    app = make_app()
    client = app.test_client()
    created = create_review(client)
    parent_state = app.extensions["session_store"].get(created["assessment_id"])
    count_before = app.extensions["session_store"].count()

    response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json=payload,
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": error}
    assert "f-1" not in response.get_data(as_text=True)
    assert app.extensions["session_store"].count() == count_before
    assert parent_state.payload["corrections"] == []


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


def test_result_includes_validated_traceable_evidence_for_browser_expansion(
    make_valid_result,
):
    result, evidence = make_valid_result
    app = make_app()
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {
                evidence_id: item.model_dump(mode="json")
                for evidence_id, item in evidence.items()
            },
        }
    )

    response = app.test_client().get(f"/api/reviews/{assessment_id}/result")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["evidence_by_id"]["ev-1"]["locator"]["heading"] == "Results framework"
    assert payload["evidence_by_id"]["ev-1"]["locator"]["excerpt"]


def test_result_rejects_evidence_mapping_key_that_differs_from_item_id(
    make_valid_result,
):
    result, evidence = make_valid_result
    app = make_app()
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {
                "ev-1": evidence["ev-1"]
                .model_copy(update={"evidence_id": "ev-2"})
                .model_dump(mode="json"),
            },
        }
    )

    response = app.test_client().get(f"/api/reviews/{assessment_id}/result")

    assert response.status_code == 409
    assert response.get_json() == {"error": "Traceable evidence is invalid."}


def test_result_rejects_priority_area_with_unavailable_cited_evidence(make_valid_result):
    result, _ = make_valid_result
    app = make_app()
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {},
        }
    )

    response = app.test_client().get(f"/api/reviews/{assessment_id}/result")

    assert response.status_code == 409
    assert response.get_json() == {"error": "Traceable evidence is invalid."}
