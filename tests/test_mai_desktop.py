"""Provider-free contracts for the opt-in Desktop integration."""

import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from cpf_fcv_reviewer.config import build_config
from cpf_fcv_reviewer.contracts import CurrentEvidenceTier
from cpf_fcv_reviewer.mai_desktop import (
    MODEL_ID,
    InstitutionalResearchController,
    MaiDesktopGateway,
    MaiUnavailable,
)
from cpf_fcv_reviewer.model_gateway import ModelOutputUnavailable
from cpf_fcv_reviewer.research_controller import ResearchController, ResearchResult


class Answer(BaseModel):
    connected: bool


@pytest.mark.parametrize("prompt", ["review", "repair"])
def test_mai_schema_requires_source_selection_for_quotes_and_targets(prompt):
    from cpf_fcv_reviewer.contracts import ReviewDraft
    from cpf_fcv_reviewer.source_grounding import NO_CPF_QUOTE
    model = gateway(lambda r: httpx.Response(200, json=response('{}')))
    model._complete = Mock(return_value='{}')
    with pytest.raises(ValidationError):
        model.generate(prompt_name=prompt, payload={"cpf_quote_index": [{
            "quote_id": "CPF_QUOTE:primary-1:1", "evidence_id": "primary-1", "preview": "Source"}]},
            output_type=ReviewDraft)
    schema = model._complete.call_args.kwargs["schema"]
    definitions = schema["$defs"]
    assert definitions["CPFQuoteSelection"]["enum"] == ["CPF_QUOTE:primary-1:1"]
    response_schema = definitions["RRADriverAssessment"]["properties"]["cpf_response"]
    assert {"const": NO_CPF_QUOTE, "type": "string"} in response_schema["anyOf"]
    target = definitions["PriorityArea"]["properties"]["target_locator"]
    assert target["properties"]["excerpt"] == {"$ref": "#/$defs/CPFQuoteSelection"}
    assert "enum" not in definitions["EvidenceLocator"]["properties"]["excerpt"]


def response(text='{"connected":true}', stop="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stop}


def gateway(handler, token_provider=lambda: "test-token"):
    return MaiDesktopGateway(
        "test-team", token_provider=token_provider,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_converse_schema_and_fresh_token_for_each_call():
    requests = []
    tokens = iter(["first-token", "second-token"])

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response())

    model = gateway(handler, lambda: next(tokens))
    for _ in range(2):
        assert model.generate(prompt_name="review", payload={"text": "test"},
                              output_type=Answer).connected
    body = json.loads(requests[0].content)
    assert body["inferenceConfig"]["maxTokens"] == 20000
    assert body["messages"][0]["content"][0]["text"] == '{"text": "test"}'
    assert json.loads(body["outputConfig"]["textFormat"]["structure"]["jsonSchema"]["schema"])
    assert "output_config" not in body
    assert requests[0].headers["Authorization"] == "Bearer first-token"
    assert requests[1].headers["Authorization"] == "Bearer second-token"
    assert requests[0].headers["x-source-type"] == "interactive"
    assert requests[0].headers["x-team-name"] == "test-team"
    assert str(requests[0].url).endswith(f"/{MODEL_ID}/converse")


@pytest.mark.parametrize("stop", ["max_tokens", "guardrail_intervened", "tool_use", None])
def test_incomplete_output_is_withheld(stop):
    model = gateway(lambda request: httpx.Response(200, json=response(stop=stop)))
    with pytest.raises(ModelOutputUnavailable):
        model.generate(prompt_name="review", payload={}, output_type=Answer)


def test_invalid_schema_is_rejected_by_existing_validator():
    model = gateway(lambda request: httpx.Response(200, json=response('{"wrong":true}')))
    with pytest.raises(ValidationError):
        model.generate(prompt_name="review", payload={}, output_type=Answer)


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_no_retry_redirect_or_provider_error_leak(status):
    handler = Mock(return_value=httpx.Response(status, text="sensitive-provider-body"))
    model = gateway(handler)
    with pytest.raises(MaiUnavailable) as caught:
        model.generate(prompt_name="review", payload={}, output_type=Answer)
    assert "sensitive-provider-body" not in str(caught.value)
    assert handler.call_count == 1


def test_follow_on_returns_only_complete_response():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response("A complete answer."))

    assert list(gateway(handler).stream(review={}, evidence={}, history=(), message="Hi")) == [
        "A complete answer."
    ]
    assert captured[0]["inferenceConfig"]["maxTokens"] == 4000
    assert "outputConfig" not in captured[0]


def test_mai_development_needs_no_anthropic_key_and_records_actual_model():
    config = build_config({"APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
                           "MAI_TEAM_NAME": "test-team"}, use_environment=False)
    assert config["ANTHROPIC_API_KEY"] == ""
    assert config["ANTHROPIC_MODEL_ID"] == MODEL_ID


@pytest.mark.parametrize("overrides", [
    {"APP_ENV": "production", "MAI_TEAM_NAME": "test-team"},
    {"APP_ENV": "development", "MAI_TEAM_NAME": ""},
    {"APP_ENV": "development", "MAI_TEAM_NAME": "bad\nheader"},
])
def test_mai_rejects_hosted_or_invalid_configuration(overrides):
    with pytest.raises((ValueError, RuntimeError)):
        build_config({"MODEL_PROVIDER": "mai_desktop", **overrides}, use_environment=False)


def test_institutional_research_cannot_claim_unqualified_full_coverage(monkeypatch):
    monkeypatch.setattr(ResearchController, "run", lambda *a, **kw: ResearchResult(
        claims=(), rejected={}, attempts=1, tier=CurrentEvidenceTier.FULL))
    result = InstitutionalResearchController(Mock()).run(Mock(), Mock())
    assert result.tier is CurrentEvidenceTier.REDUCED
    assert "institutional" in result.limitation
    assert "broad web search" in result.limitation


def test_runtime_never_constructs_direct_anthropic_clients(monkeypatch):
    from cpf_fcv_reviewer import runtime
    from cpf_fcv_reviewer.curated_research import CuratedResearchGateway
    from cpf_fcv_reviewer.mai_desktop import NoBroadWebSearch

    forbidden = Mock(side_effect=AssertionError("Direct paid provider must not be created"))
    for name in ("AnthropicModelGateway", "AnthropicFollowOnGateway",
                 "AnthropicPublicResearchGateway"):
        monkeypatch.setattr(runtime, name, forbidden)
    monkeypatch.setattr("cpf_fcv_reviewer.mai_desktop.MaiDesktopGateway", Mock())
    registry = Path(__file__).resolve().parents[1] / "registry_bundles" / (
        "cpf_fcv_reviewer_public_guardrails_v1.1.0.json")
    config = build_config({
        "MODEL_PROVIDER": "mai_desktop", "APP_ENV": "development",
        "MAI_TEAM_NAME": "test-team", "REGISTRY_BUNDLE_PATH": str(registry),
        "REGISTRY_BUNDLE_SHA256": registry.with_suffix(".sha256").read_text().split()[0],
    }, use_environment=False)
    services = runtime.build_runtime_services(config)
    controller = services["research_controller"]
    assert isinstance(controller, InstitutionalResearchController)
    assert isinstance(controller.gateway, NoBroadWebSearch)
    assert isinstance(controller.recovery_gateway, CuratedResearchGateway)
    assert controller.gateway.search("test") == ()
    assert controller.max_attempts == 1
    forbidden.assert_not_called()


def test_desktop_http_access_is_loopback_only():
    from cpf_fcv_reviewer.app import create_app

    app = create_app({
        "TESTING": True, "APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": "test-team", "START_BACKGROUND_RUNS": False,
    }, services={}, use_environment=False)
    client = app.test_client()
    page = client.get("/").get_data(as_text=True)
    assert "Local mAI development version" in page
    assert "Public pilot:" not in page
    assert "Institutional-source research only" in page
    assert client.get("/health").status_code == 200
    assert client.get("/health", environ_overrides={"REMOTE_ADDR": "192.0.2.10"}).status_code == 403
    assert client.get("/health", headers={"Origin": "https://example.org"}).status_code == 403
    assert client.get("/health", headers={"Host": "example.org"}).status_code == 403
    assert client.get("/health", headers={"X-Forwarded-For": "192.0.2.10"}).status_code == 403
    assert client.get("/health", headers={"Origin": "http://localhost"}).status_code == 200


def test_transport_failure_does_not_leak_token_or_retry():
    def handler(request):
        raise httpx.ConnectError("sensitive-token", request=request)

    model = gateway(handler)
    with pytest.raises(MaiUnavailable, match="no automatic retry") as caught:
        model.generate(prompt_name="review", payload={}, output_type=Answer)
    assert "sensitive-token" not in str(caught.value)


@pytest.mark.parametrize("body", [{}, {"stopReason": "end_turn"}, response("")])
def test_malformed_or_empty_response_fails_closed(body):
    model = gateway(lambda request: httpx.Response(200, json=body))
    with pytest.raises((MaiUnavailable, ModelOutputUnavailable)):
        model.generate(prompt_name="review", payload={}, output_type=Answer)
