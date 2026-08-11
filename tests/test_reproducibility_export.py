from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.export_docx import build_docx
from cpf_fcv_reviewer.registry import load_registry_bundle
from cpf_fcv_reviewer.validators import validate_reproducibility_metadata


def complete_metadata(metadata):
    return metadata.model_copy(
        update={
            "source_scan_at": datetime(2026, 8, 10, tzinfo=UTC),
            "output_language": "en",
            "document_fingerprints": {"CPF draft": "a" * 64},
            "registry_bundle_hash": "b" * 64,
            "guidance_hash": "c" * 64,
            "prompt_hashes": {"review": "d" * 64},
            "validation_outcomes": (
                "contract_valid",
                "policy_guardrails_passed",
            ),
            "correction_ids": ("c-1",),
            "parent_run_id": "run-0",
        }
    )


def incomplete_metadata(metadata):
    return metadata.model_copy(
        update={
            "source_scan_at": None,
            "document_fingerprints": {},
            "registry_bundle_hash": "",
            "guidance_hash": "",
            "prompt_hashes": {},
        }
    )


def test_complete_reproducibility_metadata_passes_and_defaults_fail(make_valid_result):
    result, _ = make_valid_result

    complete = validate_reproducibility_metadata(complete_metadata(result.metadata))
    incomplete = validate_reproducibility_metadata(incomplete_metadata(result.metadata))

    assert complete == ()
    assert {issue.code for issue in incomplete} == {"incomplete_reproducibility_metadata"}


def test_docx_lists_reproducibility_hashes_labels_and_lineage(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"metadata": complete_metadata(result.metadata)})

    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    for expected in (
        "Source scan: 2026-08-10T00:00:00+00:00",
        f"Document CPF draft: {'a' * 64}",
        f"Registry bundle hash: {'b' * 64}",
        f"Guidance hash: {'c' * 64}",
        f"Prompt review: {'d' * 64}",
        "Validation: contract_valid",
        "Validation: policy_guardrails_passed",
        "Correction: c-1",
        "Parent run: run-0",
        "Output language: en",
    ):
        assert expected in text


def test_export_route_rejects_incomplete_reproducibility_metadata(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"metadata": incomplete_metadata(result.metadata)})
    registry = load_registry_bundle(
        Path("tests/fixtures/registry_bundle.synthetic.json"),
        allow_synthetic=True,
    )
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"registry_bundle": registry},
    )
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {key: item.model_dump(mode="json") for key, item in evidence.items()},
        }
    )

    response = app.test_client().get(f"/api/reviews/{assessment_id}/export.docx")

    assert response.status_code == 409
    assert response.get_json() == {"error": "Reproducibility metadata is incomplete."}


def test_result_route_rejects_incomplete_reproducibility_metadata(make_valid_result):
    result, _ = make_valid_result
    result = result.model_copy(update={"metadata": incomplete_metadata(result.metadata)})
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
        }
    )

    response = app.test_client().get(f"/api/reviews/{assessment_id}/result")

    assert response.status_code == 409
    assert response.get_json() == {"error": "Reproducibility metadata is incomplete."}


def test_docx_rendering_failure_returns_only_a_safe_error(monkeypatch, make_valid_result):
    result, evidence = make_valid_result
    registry = load_registry_bundle(
        Path("tests/fixtures/registry_bundle.synthetic.json"),
        allow_synthetic=True,
    )
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"registry_bundle": registry},
    )
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {key: item.model_dump(mode="json") for key, item in evidence.items()},
        }
    )

    def fail_render(*args, **kwargs):
        raise RuntimeError("sensitive renderer path and source excerpt")

    monkeypatch.setattr("cpf_fcv_reviewer.routes.build_docx", fail_render)

    response = app.test_client().get(f"/api/reviews/{assessment_id}/export.docx")

    assert response.status_code == 500
    assert response.get_json() == {"error": "DOCX export failed."}
    assert "sensitive" not in response.get_data(as_text=True)
