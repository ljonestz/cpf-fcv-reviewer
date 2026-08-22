import os
import subprocess
import sys
from datetime import date
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_smoke_app
from cpf_fcv_reviewer.config import build_config
from cpf_fcv_reviewer.contracts import ReviewDraft, ReviewResult
from cpf_fcv_reviewer.public_research import retain_public_claims
from cpf_fcv_reviewer.research_controller import ResearchMode, ResearchRequest
from cpf_fcv_reviewer.review_profiles import STAGE_PROFILES
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


def _model_payload(diagnostic_mode: str = "limited_framing") -> dict:
    locator = {
        "document_title": "Benin CPF.txt",
        "heading": "Strategic context",
        "element": "paragraph 1",
        "excerpt": "Synthetic primary evidence.",
        "is_paraphrase": False,
    }
    return {
        "evidence_pack": {
            "metadata": {"diagnostic_mode": diagnostic_mode},
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
                *[
                    {
                        "evidence_id": f"registry-SYN-PUB-FCV-STRAT-{index:03d}",
                        "evidence_type": "registry_language",
                        "text": f"Synthetic Strategy shift {index}.",
                        "confidence": "high",
                    }
                    for index in range(1, 5)
                ],
            ]
        },
        "stage_profile": {"allowed_scales": ["targeted_edit"]},
    }


def _submit_smoke_review(client, review_stage: str = "decision_review") -> dict:
    response = client.post(
        "/api/reviews",
        data={
            "country": "Benin",
            "review_stage": review_stage,
            "review_focus": "Synthetic smoke review focus.",
            "cpf": (
                BytesIO((FIXTURES / "synthetic_en.txt").read_bytes()),
                "Benin-synthetic-CPF.txt",
            ),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.get_json()


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
    assert draft.revision_summary[0].title
    assert draft.rra_driver_assessments == ()
    assert len(draft.fcv_strategy_assessments) == 4
    assert {
        row.strategic_shift.value for row in draft.fcv_strategy_assessments
    } == {
        "anticipate_better",
        "differentiated_approach",
        "one_wbg_jobs",
        "toolkit_partnerships_staffing",
    }
    assert all(
        any(
            evidence_id.startswith("registry-SYN-PUB-FCV-STRAT-")
            for evidence_id in row.evidence_ids
        )
        for row in draft.fcv_strategy_assessments
    )

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
    assert repaired.rra_driver_assessments == draft.rra_driver_assessments
    assert repaired.fcv_strategy_assessments == draft.fcv_strategy_assessments


def test_smoke_model_gateway_adds_one_rra_row_only_in_rra_alignment_mode():
    payload = _model_payload("rra_alignment")

    draft = SmokeModelGateway().generate(
        prompt_name="review",
        payload=payload,
        output_type=ReviewDraft,
    )

    assert len(draft.rra_driver_assessments) == 1
    assert draft.rra_driver_assessments[0].evidence_ids


def test_smoke_model_gateway_adds_synthetic_comment_reference_for_comment_responses():
    payload = _model_payload()
    payload["stage_profile"]["allowed_scales"] = ["comment_response"]

    draft = SmokeModelGateway().generate(
        prompt_name="review",
        payload=payload,
        output_type=ReviewDraft,
    )

    assert draft.priority_areas[0].comment_reference == (
        "[SYNTHETIC SMOKE] Synthetic comment fixture"
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


@pytest.mark.parametrize("value", ["false", "0", "no", "off"])
def test_smoke_mode_parses_false_environment_values(monkeypatch, value):
    monkeypatch.setenv("SMOKE_MODE", value)

    config = build_config({"TESTING": True})

    assert config["SMOKE_MODE"] is False


@pytest.mark.parametrize("value", ["true", "1", "yes", "on"])
def test_smoke_mode_parses_true_environment_values_in_development(monkeypatch, value):
    monkeypatch.setenv("SMOKE_MODE", value)

    config = build_config({"TESTING": True, "APP_ENV": "development"})

    assert config["SMOKE_MODE"] is True


@pytest.mark.parametrize("value", ["", "2", "enabled", "true-ish"])
def test_smoke_mode_rejects_invalid_environment_values_without_echo(monkeypatch, value):
    monkeypatch.setenv("SMOKE_MODE", value)

    with pytest.raises(ValueError) as exc_info:
        build_config({"TESTING": True})

    assert str(exc_info.value) == "SMOKE_MODE environment value is invalid."
    if value:
        assert value not in str(exc_info.value)


def test_smoke_model_output_has_no_cross_country_claim_for_non_benin_payload():
    payload = _model_payload()
    evidence = payload["evidence_pack"]["evidence"]
    evidence[0]["locator"]["document_title"] = "Nepal synthetic CPF.txt"
    evidence[1]["source_url"] = "https://www.worldbank.org/synthetic-smoke/nepal/current-1"

    draft = SmokeModelGateway().generate(
        prompt_name="review",
        payload=payload,
        output_type=ReviewDraft,
    )

    assert "benin" not in draft.model_dump_json().casefold()


def test_smoke_app_import_and_creation_succeed_when_anthropic_import_is_blocked():
    project_root = Path(__file__).parents[1]
    script = dedent(
        """
        import importlib.abc
        import sys

        class BlockAnthropic(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "anthropic" or fullname.startswith("anthropic."):
                    raise ModuleNotFoundError("provider import blocked for smoke test")
                return None

        sys.meta_path.insert(0, BlockAnthropic())
        from cpf_fcv_reviewer.app import create_smoke_app

        app = create_smoke_app(start_background_runs=False)
        assert app.config["SMOKE_MODE"] is True
        assert not any(
            name == "anthropic" or name.startswith("anthropic.")
            for name in sys.modules
        )
        print("SMOKE_IMPORT_OK")
        """
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(project_root / "src")

    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "SMOKE_IMPORT_OK"


def test_smoke_app_configuration_ignores_poisoned_environment(monkeypatch):
    poisoned = {
        "APP_RELEASE": "poison-release",
        "APP_ENV": "production",
        "SMOKE_MODE": "not-a-boolean",
        "ANTHROPIC_API_KEY": "poison-secret",
        "ANTHROPIC_MODEL_ID": "poison-model",
        "REGISTRY_BUNDLE_PATH": "poison-path",
        "REGISTRY_BUNDLE_SHA256": "poison-hash",
        "RESEARCH_MAX_ATTEMPTS": "invalid",
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": "invalid",
        "RESEARCH_TOTAL_BUDGET_SECONDS": "invalid",
        "RESEARCH_MINIMUM_CLAIMS": "invalid",
        "RESEARCH_MINIMUM_PUBLISHERS": "invalid",
        "RESEARCH_RETRY_BACKOFF_SECONDS": "invalid",
        "RESEARCH_RECOVERY_TIMEOUT_SECONDS": "invalid",
        "RESEARCH_RECOVERY_MAX_BYTES": "invalid",
        "RELIEFWEB_APP_NAME": "poison-app-name",
        "SESSION_TTL_SECONDS": "invalid",
    }
    for name, value in poisoned.items():
        monkeypatch.setenv(name, value)

    app = create_smoke_app(start_background_runs=False)
    expected = {
        "APP_RELEASE": "deterministic-smoke",
        "APP_ENV": "development",
        "SMOKE_MODE": True,
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_MODEL_ID": "deterministic-smoke",
        "ALLOW_SYNTHETIC_REGISTRY": True,
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "RESEARCH_MAX_ATTEMPTS": 1,
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 5.0,
        "RESEARCH_TOTAL_BUDGET_SECONDS": 15.0,
        "RESEARCH_MINIMUM_CLAIMS": 4,
        "RESEARCH_MINIMUM_PUBLISHERS": 2,
        "RESEARCH_RETRY_BACKOFF_SECONDS": 0.0,
        "RESEARCH_RECOVERY_TIMEOUT_SECONDS": 1.0,
        "RESEARCH_RECOVERY_MAX_BYTES": 500_000,
        "RELIEFWEB_APP_NAME": "",
        "SESSION_TTL_SECONDS": 3_600,
        "START_BACKGROUND_RUNS": False,
        "TESTING": False,
    }
    assert {name: app.config[name] for name in expected} == expected

    client = app.test_client()
    created = _submit_smoke_review(client)
    run_assessment(app, created["assessment_id"])
    result = client.get(created["result_url"]).get_json()
    assert result["metadata"]["model_id"] == "deterministic-smoke"
    assert result["metadata"]["current_evidence_tier"] == "full"


@pytest.mark.parametrize("review_stage", tuple(STAGE_PROFILES))
def test_smoke_routes_complete_with_schema_for_every_review_stage(review_stage):
    app = create_smoke_app(start_background_runs=False)
    client = app.test_client()
    created = _submit_smoke_review(client, review_stage)

    run_assessment(app, created["assessment_id"])

    response = client.get(created["result_url"])
    assert response.status_code == 200
    payload = response.get_json()
    evidence_by_id = payload.pop("evidence_by_id")
    result = ReviewResult.model_validate(payload)
    assert evidence_by_id
    assert result.metadata.review_stage == review_stage
    assert result.metadata.model_id == "deterministic-smoke"
    assert result.metadata.current_evidence_tier.value == "full"
    if review_stage == "response_to_comments":
        assert result.priority_areas[0].comment_reference


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
