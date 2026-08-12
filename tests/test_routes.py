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


def test_result_rejects_finding_with_unavailable_cited_evidence(make_valid_result):
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
