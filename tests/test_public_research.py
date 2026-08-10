from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer import public_research
from cpf_fcv_reviewer.public_research import CurrentContextClaim, retain_public_claims


def test_retains_qualifying_public_claim_without_licensed_data():
    claim = CurrentContextClaim(
        claim_id="c1",
        text="The operating context may have changed since the CPF was drafted.",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Tests whether the contextual assumption remains plausible.",
        relationship="qualifies",
        licensed_data_required=False,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == (claim,)
    assert rejected == {}


def test_rejects_claims_requiring_licensed_data():
    claim = CurrentContextClaim(
        claim_id="c2",
        text="A licensed event-level dataset would be required to substantiate this claim.",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Would otherwise inform the current context.",
        relationship="corroborates",
        licensed_data_required=True,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"c2": "licensed data is not permitted"}


def test_rejects_claim_without_a_public_source_url():
    claim = CurrentContextClaim(
        claim_id="c3",
        text="The source reference was omitted.",
        source_url=None,
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Would otherwise inform the current context.",
        relationship="unresolved",
        licensed_data_required=False,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"c3": "public source URL is required"}


def test_current_context_claim_requires_a_source_url_field_even_when_null():
    with pytest.raises(ValidationError):
        CurrentContextClaim(
            claim_id="c4",
            text="The source URL field must be included.",
            source_date=date(2026, 8, 1),
            source_type="public analysis",
            relevance="Tests the public-source contract.",
            relationship="unresolved",
            licensed_data_required=False,
        )


def test_rejects_claim_without_material_relevance():
    claim = CurrentContextClaim(
        claim_id="c5",
        text="The source is not materially tied to the review question.",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="   ",
        relationship="unresolved",
        licensed_data_required=False,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"c5": "material relevance is required"}


def test_anthropic_gateway_passes_prompt_through_and_strips_text(monkeypatch):
    calls: list[dict[str, object]] = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=(
                    SimpleNamespace(type="text", text="  public result  "),
                    SimpleNamespace(type="web_search_result", text="ignored"),
                )
            )

    fake_client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    monkeypatch.setattr(public_research, "Anthropic", lambda api_key: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("test-key", "test-model")

    response = gateway.search("Use this prompt exactly.")

    assert calls[0]["messages"] == [
        {"role": "user", "content": "Use this prompt exactly."}
    ]
    assert response == "public result"


def test_load_research_prompt_remains_available_separately():
    prompt = public_research.load_research_prompt()
    assert "bounded public-source recency and plausibility check" in prompt
