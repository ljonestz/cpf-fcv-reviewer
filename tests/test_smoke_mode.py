from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_smoke_app
from cpf_fcv_reviewer.config import build_config
from cpf_fcv_reviewer.contracts import ReviewDraft
from cpf_fcv_reviewer.public_research import retain_public_claims
from cpf_fcv_reviewer.research_controller import ResearchMode, ResearchRequest
from cpf_fcv_reviewer.routes import run_assessment
from cpf_fcv_reviewer.smoke import SmokeModelGateway, SmokeResearchGateway

FIXTURES = Path(__file__).parent / "fixtures"


def smoke_request(
    *,
    review_date: date = date(2026, 8, 14),
) -> ResearchRequest:
    return ResearchRequest("Benin", review_date, ResearchMode.HOLISTIC)


def test_smoke_research_gateway_returns_retained_synthetic_current_claims():
    claims = SmokeResearchGateway().search(smoke_request())

    assert len(claims) >= 4
    assert len({claim.publisher for claim in claims}) >= 2
    assert {claim.context_kind for claim in claims} >= {
        "structural_dynamic",
        "current_development",
    }
    assert all(claim.source_date <= date(2026, 8, 14) for claim in claims)
    assert all("SYNTHETIC" in claim.text.upper() for claim in claims)
    assert all("SYNTHETIC" in claim.source_title.upper() for claim in claims)

    retained, rejected = retain_public_claims(claims)

    assert retained == claims
    assert rejected == {}


def test_smoke_research_gateway_respects_rra_review_date_window():
    request = ResearchRequest(
        "Benin",
        date(2026, 8, 14),
        ResearchMode.RRA_UPDATE,
        diagnostic_title="Synthetic Benin RRA",
        diagnostic_date=date(2026, 1, 1),
    )

    claims = SmokeResearchGateway().search(request)

    assert all(
        request.diagnostic_date < claim.source_date <= request.review_date
        for claim in claims
    )


def _model_payload() -> dict:
    locator = {
        "document_title": "Benin CPF.txt",
        "heading": "Strategic context",
        "element": "paragraph 1",
        "excerpt": "Synthetic primary evidence.",
        "is_paraphrase": False,
    }
    return {
        "evidence_pack": {
            "evidence": [
                {
                    "evidence_id": "primary-001",
                    "evidence_type": "document_fact",
                    "text": "Synthetic primary evidence.",
                    "locator": locator,
                    "confidence": "high",
                    "document_role": "primary",
                },
                {
                    "evidence_id": "current-001",
                    "evidence_type": "current_context",
                    "text": "Synthetic current evidence.",
                    "source_url": "https://www.worldbank.org/synthetic-smoke/benin/current-1",
                    "confidence": "high",
                },
            ]
        },
        "stage_profile": {"allowed_scales": ["targeted_edit"]},
    }


def test_smoke_model_gateway_returns_schema_valid_review_and_repair_from_supplied_ids():
    gateway = SmokeModelGateway()
    payload = _model_payload()

    draft = gateway.generate(
        prompt_name="review",
        payload=payload,
        output_type=ReviewDraft,
    )

    supplied_ids = {
        item["evidence_id"] for item in payload["evidence_pack"]["evidence"]
    }
    assert set(draft.priority_areas[0].evidence_ids) <= supplied_ids
    assert "SYNTHETIC SMOKE" in draft.overall_read
    assert "SYNTHETIC SMOKE" in draft.limitations[0]

    repaired = gateway.generate(
        prompt_name="repair",
        payload={
            "draft": draft.model_dump(mode="json"),
            "validation_issues": [],
            "stage_profile": {"allowed_scales": ["targeted_edit"]},
        },
        output_type=ReviewDraft,
    )

    assert isinstance(repaired, ReviewDraft)
    assert set(repaired.priority_areas[0].evidence_ids) <= set(
        draft.priority_areas[0].evidence_ids
    )


def test_smoke_mode_is_rejected_with_production_environment():
    with pytest.raises(RuntimeError, match="development only"):
        build_config({"SMOKE_MODE": True, "APP_ENV": "production"})


def test_smoke_mode_rejects_truthy_string_ambiguity():
    with pytest.raises(ValueError, match="SMOKE_MODE"):
        build_config(
            {
                "SMOKE_MODE": "true",
                "APP_ENV": "development",
                "TESTING": True,
            }
        )


def test_smoke_app_completes_without_anthropic_key_or_provider_construction(monkeypatch):
    def forbidden_provider(*args, **kwargs):
        raise AssertionError("Anthropic provider construction is forbidden in smoke mode")

    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicModelGateway",
        forbidden_provider,
    )
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        forbidden_provider,
    )

    app = create_smoke_app(start_background_runs=False)
    client = app.test_client()
    response = client.post(
        "/api/reviews",
        data={
            "country": "Benin",
            "review_stage": "decision_review",
            "review_focus": "What should be strengthened?",
            "cpf": (
                BytesIO((FIXTURES / "synthetic_en.txt").read_bytes()),
                "Benin-synthetic-CPF.txt",
            ),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    created = response.get_json()

    run_assessment(app, created["assessment_id"])

    result_response = client.get(created["result_url"])
    assert result_response.status_code == 200
    result = result_response.get_json()
    assert result["metadata"]["model_id"] == "deterministic-smoke"
    assert result["metadata"]["current_evidence_tier"] == "full"
    assert "SYNTHETIC SMOKE" in result["overall_read"]
    assert all(
        evidence_id.startswith(("primary-", "current-", "registry-"))
        for area in result["priority_areas"]
        for evidence_id in area["evidence_ids"]
    )

    export = client.get(f"/api/reviews/{created['assessment_id']}/export.docx")
    assert export.status_code == 200
    assert "SYNTHETIC SMOKE" in "\n".join(
        paragraph.text for paragraph in Document(BytesIO(export.data)).paragraphs
    )


def test_smoke_launcher_is_repository_relative_and_fixed_to_local_debug_server():
    launcher = Path(__file__).parents[1] / "scripts" / "run_smoke.py"
    source = launcher.read_text(encoding="utf-8")

    assert "Path(__file__).resolve().parents[1]" in source
    assert "127.0.0.1" in source
    assert "58422" in source
    assert "debug=False" in source
    assert "C:\\Users\\" not in source
