"""Opt-in Anthropic research with mAI generation; all providers are test doubles."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.config import build_config
from cpf_fcv_reviewer.mai_desktop import MODEL_ID
from cpf_fcv_reviewer.research_controller import ResearchController


def hybrid_config(**overrides):
    return build_config({
        "APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": "test-team", "RESEARCH_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "synthetic-key", **overrides,
    }, use_environment=False)


def test_hybrid_research_requires_its_own_key_before_authentication():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        hybrid_config(ANTHROPIC_API_KEY="")


@pytest.mark.parametrize("provider", ["unknown", "", None])
def test_invalid_explicit_research_provider_fails_closed(provider):
    with pytest.raises(ValueError, match="RESEARCH_PROVIDER"):
        hybrid_config(RESEARCH_PROVIDER=provider)


def test_research_model_is_independent_of_mai_model_metadata():
    config = hybrid_config(RESEARCH_MODEL_ID="synthetic-research-model")
    assert config["RESEARCH_MODEL_ID"] == "synthetic-research-model"
    assert config["ANTHROPIC_MODEL_ID"] == MODEL_ID
    assert hybrid_config()["RESEARCH_MODEL_ID"] == "claude-sonnet-4-5"


def test_research_defaults_preserve_existing_provider_routes():
    mai = build_config({"MODEL_PROVIDER": "mai_desktop", "APP_ENV": "development",
                        "MAI_TEAM_NAME": "test-team"}, use_environment=False)
    direct = build_config({"TESTING": True, "ANTHROPIC_MODEL_ID": "custom-model"},
                          use_environment=False)
    assert mai["RESEARCH_PROVIDER"] == "institutional"
    assert direct["RESEARCH_PROVIDER"] == "anthropic"
    assert direct["RESEARCH_MODEL_ID"] == "custom-model"


def test_hybrid_runtime_constructs_only_research_on_direct_provider(monkeypatch):
    from cpf_fcv_reviewer import runtime
    from cpf_fcv_reviewer.curated_research import CuratedResearchGateway

    forbidden = Mock(side_effect=AssertionError("Direct generation must not be constructed"))
    monkeypatch.setattr(runtime, "AnthropicModelGateway", forbidden)
    monkeypatch.setattr(runtime, "AnthropicFollowOnGateway", forbidden)
    mai = Mock()
    monkeypatch.setattr("cpf_fcv_reviewer.mai_desktop.MaiDesktopGateway", Mock(return_value=mai))
    research = Mock()
    research_factory = Mock(return_value=research)
    monkeypatch.setattr(runtime, "AnthropicPublicResearchGateway", research_factory)
    registry = Path(__file__).resolve().parents[1] / "registry_bundles" / (
        "cpf_fcv_reviewer_public_guardrails_v1.1.0.json")
    config = hybrid_config(
        REGISTRY_BUNDLE_PATH=str(registry),
        REGISTRY_BUNDLE_SHA256=registry.with_suffix(".sha256").read_text().split()[0],
        RESEARCH_MODEL_ID="synthetic-research-model",
    )
    services = runtime.build_runtime_services(config)
    controller = services["research_controller"]
    assert type(controller) is ResearchController
    assert controller.gateway is research
    assert isinstance(controller.recovery_gateway, CuratedResearchGateway)
    assert controller.max_attempts == config["RESEARCH_MAX_ATTEMPTS"]
    assert controller.total_budget_seconds == config["RESEARCH_TOTAL_BUDGET_SECONDS"]
    assert services["follow_on_gateway"] is mai
    research_factory.assert_called_once_with(
        "synthetic-key", "synthetic-research-model",
        timeout_seconds=config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"],
    )
    research.search.assert_not_called()
    mai.generate.assert_not_called()
    forbidden.assert_not_called()


def test_hybrid_intake_discloses_separate_research_cost_and_keeps_local_guards():
    app = create_app(hybrid_config(TESTING=True, START_BACKGROUND_RUNS=False),
                     services={}, use_environment=False)
    client = app.test_client()
    page = client.get("/").get_data(as_text=True)
    assert "Public-web research uses Anthropic" in page
    assert "separate API charges" in page
    assert "Institutional-source research only" not in page
    assert "Local mAI development version" in page
    assert client.get("/health", environ_overrides={"REMOTE_ADDR": "192.0.2.10"}).status_code == 403
    assert client.get("/health", headers={"Origin": "https://example.org"}).status_code == 403
