from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.export_docx import build_docx
from cpf_fcv_reviewer.registry import load_registry_bundle


def test_docx_contains_same_result_and_source_locator(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(
        result,
        evidence=evidence,
        hydrated_referrals=(
            {
                "entry_id": "SYN-REF-001",
                "approved_text": "Consult the designated policy owner.",
                "version": "1.0.0-test",
            },
        ),
    )
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.executive_judgment in text
    assert "CPF.docx | Results framework | paragraph 12" in text
    assert "Frame cautiously" in text
    assert "Consult the designated policy owner." in text
    assert "fake-model" in text
    assert "No RRA was available." in text


def test_withheld_content_is_not_rendered_as_draft_language(make_valid_result):
    result, _ = make_valid_result
    data = build_docx(result, evidence={}, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Suggested ready-to-paste text" not in text


def test_export_route_requires_a_completed_traceable_result(make_valid_result):
    result, evidence = make_valid_result
    registry = load_registry_bundle(
        Path("tests/fixtures/registry_bundle.synthetic.json"),
        allow_synthetic=True,
    )
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"registry_bundle": registry},
    )
    assessment_id = app.extensions["session_store"].create({"status": "created"})
    client = app.test_client()

    pending = client.get(f"/api/reviews/{assessment_id}/export.docx")
    assert pending.status_code == 202

    app.extensions["session_store"].update(
        assessment_id,
        status="complete",
        result=result.model_dump(mode="json"),
        evidence_by_id={key: item.model_dump(mode="json") for key, item in evidence.items()},
    )
    response = client.get(f"/api/reviews/{assessment_id}/export.docx")

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "filename=CPF-FCV-Review.docx" in response.headers["Content-Disposition"]


def test_background_run_persists_traceable_evidence(make_valid_result):
    result, evidence = make_valid_result

    class FakeOrchestrator:
        def run(self, context, emit):
            return {
                **context,
                "result": result,
                "evidence_pack": SimpleNamespace(evidence=tuple(evidence.values())),
            }

    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"review_orchestrator": FakeOrchestrator()},
    )
    assessment_id = app.extensions["session_store"].create({"status": "created", "corrections": []})

    from cpf_fcv_reviewer.routes import run_assessment

    run_assessment(app, assessment_id)

    state = app.extensions["session_store"].get(assessment_id)
    assert state.payload["status"] == "complete"
    assert state.payload["evidence_by_id"]["ev-1"]["evidence_id"] == "ev-1"
