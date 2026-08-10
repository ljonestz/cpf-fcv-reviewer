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


def _claim(claim_id: str = "claim-1", **overrides: object) -> CurrentContextClaim:
    fields: dict[str, object] = {
        "claim_id": claim_id,
        "text": "The contextual assumption needs a bounded public-source check.",
        "source_url": "https://example.org/context-update",
        "source_date": date(2026, 8, 1),
        "source_type": "public analysis",
        "relevance": "Tests whether the claim remains plausible.",
        "relationship": "qualifies",
        "licensed_data_required": False,
    }
    fields.update(overrides)
    return CurrentContextClaim(**fields)


@pytest.mark.parametrize("licensed_data_required", ["false", 0])
def test_current_context_claim_requires_a_strict_boolean_license_flag(
    licensed_data_required: object,
):
    with pytest.raises(ValidationError):
        _claim(licensed_data_required=licensed_data_required)


@pytest.mark.parametrize("field", ["claim_id", "text", "source_type"])
def test_current_context_claim_rejects_blank_required_text(field: str):
    with pytest.raises(ValidationError):
        _claim(**{field: "   "})


@pytest.mark.parametrize(
    "source_url",
    [
        "https://user:password@example.org/context-update",
        "https://localhost/context-update",
        "https://localhost./context-update",
        "https://service.local/context-update",
        "https://127.0.0.1/context-update",
        "https://10.0.0.1/context-update",
        "https://172.16.0.1/context-update",
        "https://192.168.0.1/context-update",
        "https://169.254.0.1/context-update",
        "https://0.0.0.0/context-update",
        "https://192.0.2.1/context-update",
        "https://[::1]/context-update",
        "https://[fc00::1]/context-update",
        "https://[fe80::1]/context-update",
        "https://[::]/context-update",
        "https://[2001:db8::1]/context-update",
    ],
)
def test_rejects_nonpublic_or_credential_bearing_source_urls(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


def test_accepts_and_normalizes_an_ordinary_public_source_url():
    claim = _claim(source_url="  https://example.org/context-update  ")

    retained, rejected = retain_public_claims((claim,))

    assert claim.source_url == "https://example.org/context-update"
    assert retained == (claim,)
    assert rejected == {}


def test_rejects_all_claims_with_a_duplicate_claim_id():
    first = _claim("duplicate-claim")
    second = first.model_copy(update={"text": "A second claim with the same identifier."})

    retained, rejected = retain_public_claims((first, second))

    assert retained == ()
    assert rejected == {"duplicate-claim": "duplicate claim ID is not permitted"}


def test_public_research_prompt_enumerates_the_json_contract():
    prompt = public_research.load_research_prompt()

    expected_terms = (
        "claim_id:",
        "text:",
        "source_url:",
        "source_date:",
        "source_type:",
        "relevance:",
        "relationship: corroborates | qualifies | contradicts | unresolved",
        "licensed_data_required: boolean",
        "JSON array only",
    )

    for term in expected_terms:
        assert term in prompt


@pytest.mark.parametrize(
    "source_url",
    [
        "https://foo.localhost/context-update",
        "https://intranet/context-update",
        "https://2130706433/context-update",
        "https://0x7f000001/context-update",
        "https://example..org/context-update",
        "https://example.org:99999/context-update",
        "https://-bad.example.org/context-update",
        "https://bad-.example.org/context-update",
        "https://bad_.example.org/context-update",
        "https://service.internal/context-update",
        "https://service.home.arpa/context-update",
        "https://example.test/context-update",
        "https://example.invalid/context-update",
    ],
)
def test_rejects_non_fqdn_and_special_use_public_source_urls(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://example.org/context-update",
        "https://subdomain.example.org/context-update",
        "https://8.8.8.8/context-update",
    ],
)
def test_accepts_fqdn_and_global_literal_ip_source_urls(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert len(retained) == 1
    assert rejected == {}


def test_normalizes_claim_identity_and_required_text_fields():
    claim = _claim(
        claim_id="  normalized-id  ",
        text="  A normalized claim.  ",
        source_type="  public analysis  ",
    )

    assert claim.claim_id == "normalized-id"
    assert claim.text == "A normalized claim."
    assert claim.source_type == "public analysis"


def test_duplicate_detection_uses_normalized_claim_ids():
    first = _claim(claim_id=" duplicate-id ")
    second = _claim(claim_id="duplicate-id")

    retained, rejected = retain_public_claims((first, second))

    assert retained == ()
    assert rejected == {"duplicate-id": "duplicate claim ID is not permitted"}


def test_public_research_prompt_specifies_authority_field_constraints():
    prompt = public_research.load_research_prompt()

    expected_terms = (
        "claim_id: unique nonblank string",
        "text: nonblank string",
        "source_url: public HTTP(S) URL or null",
        "source_date: ISO YYYY-MM-DD date",
        "source_type: nonblank string",
        "relevance: nonblank string",
        "licensed_data_required: boolean",
    )

    for term in expected_terms:
        assert term in prompt
