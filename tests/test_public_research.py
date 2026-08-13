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
        publisher="World Bank",
        source_title="Country context update",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Tests whether the contextual assumption remains plausible.",
        relationship="establishes",
        context_kind="current_development",
        licensed_data_required=False,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == (claim,)
    assert rejected == {}


def test_rejects_claims_requiring_licensed_data():
    claim = CurrentContextClaim(
        claim_id="c2",
        text="A licensed event-level dataset would be required to substantiate this claim.",
        publisher="Public analytics provider",
        source_title="Conflict events",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Would otherwise inform the current context.",
        relationship="corroborates",
        context_kind="current_development",
        licensed_data_required=True,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"c2": "licensed data is not permitted"}


def test_rejects_claim_without_a_public_source_url():
    claim = CurrentContextClaim(
        claim_id="c3",
        text="The source reference was omitted.",
        publisher="World Bank",
        source_title="Unlinked source",
        source_url=None,
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="Would otherwise inform the current context.",
        relationship="unresolved",
        context_kind="structural_dynamic",
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
            publisher="World Bank",
            source_title="Public source",
            source_date=date(2026, 8, 1),
            source_type="public analysis",
            relevance="Tests the public-source contract.",
            relationship="unresolved",
            context_kind="structural_dynamic",
            licensed_data_required=False,
        )


def test_rejects_claim_without_material_relevance():
    claim = CurrentContextClaim(
        claim_id="c5",
        text="The source is not materially tied to the review question.",
        publisher="World Bank",
        source_title="Public source",
        source_url="https://example.org/context-update",
        source_date=date(2026, 8, 1),
        source_type="public analysis",
        relevance="   ",
        relationship="unresolved",
        context_kind="implementation_condition",
        licensed_data_required=False,
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"c5": "material relevance is required"}


def test_anthropic_gateway_parses_concatenated_json_claim_text(monkeypatch):
    calls: list[dict[str, object]] = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="text",
                        text='[{"claim_id":"c1","text":"A current development.",',
                    ),
                    SimpleNamespace(
                        type="text",
                        text=(
                            '"publisher":"World Bank","source_title":"Update",'
                            '"source_url":"https://example.org/update",'
                            '"source_date":"2026-08-01","source_type":"public report",'
                            '"relevance":"Tests recency.","relationship":"establishes",'
                            '"context_kind":"current_development",'
                            '"licensed_data_required":false}]'
                        ),
                    ),
                    SimpleNamespace(type="web_search_result", text="ignored"),
                )
            )

    fake_client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=12.5
    )

    response = gateway.search("Use this prompt exactly.")

    assert calls[0]["messages"] == [
        {"role": "user", "content": "Use this prompt exactly."}
    ]
    assert isinstance(response, tuple)
    assert response[0].publisher == "World Bank"
    assert response[0].context_kind == "current_development"
    assert response[0].relationship == "establishes"
    assert calls[0]["tools"][0]["name"] == "web_search"


def test_anthropic_gateway_configures_timeout_and_disables_retries(monkeypatch):
    captured = {}

    def fake_anthropic(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(public_research, "Anthropic", fake_anthropic)

    public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=7.25
    )

    assert captured == {"api_key": "test-key", "timeout": 7.25, "max_retries": 0}


@pytest.mark.parametrize("response_text", ["{\"claim_id\": \"c1\"}", "not json"])
def test_anthropic_gateway_rejects_non_array_or_malformed_json(monkeypatch, response_text):
    class FakeMessages:
        def create(self, **kwargs):
            return SimpleNamespace(content=(SimpleNamespace(type="text", text=response_text),))

    fake_client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=10
    )

    with pytest.raises(ValueError, match="could not be parsed"):
        gateway.search("Use this prompt exactly.")


def test_load_research_prompt_remains_available_separately():
    prompt = public_research.load_research_prompt()
    assert "bounded, source-linked current-country evidence check" in prompt


def _claim(claim_id: str = "claim-1", **overrides: object) -> CurrentContextClaim:
    fields: dict[str, object] = {
        "claim_id": claim_id,
        "text": "The contextual assumption needs a bounded public-source check.",
        "publisher": "World Bank",
        "source_title": "Context update",
        "source_url": "https://example.org/context-update",
        "source_date": date(2026, 8, 1),
        "source_type": "public analysis",
        "relevance": "Tests whether the claim remains plausible.",
        "relationship": "qualifies",
        "context_kind": "structural_dynamic",
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


@pytest.mark.parametrize(
    "field", ["claim_id", "text", "publisher", "source_title", "source_type"]
)
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
        "`claim_id`",
        "`text`",
        "`publisher`",
        "`source_title`",
        "`source_url`",
        "`source_date`",
        "`source_type`",
        "`relevance`",
        "`context_kind`",
        "`relationship`",
        "`licensed_data_required`",
        "strict JSON array only",
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
        "`claim_id`: unique nonblank string",
        "`text`: nonblank source-grounded claim",
        "`publisher`: nonblank publisher or institution name",
        "`source_title`: nonblank title of the cited source",
        "`source_url`: public HTTP(S) URL or null",
        "`source_date`: ISO YYYY-MM-DD publication date",
        "`source_type`: nonblank source type",
        "`relevance`: nonblank explanation",
        "`context_kind`: exactly",
        "`structural_dynamic`",
        "`current_development`",
        "`resilience_factor`",
        "`implementation_condition`",
        "`relationship`: exactly",
        "`corroborates`",
        "`qualifies`",
        "`contradicts`",
        "`unresolved`",
        "`establishes`",
        "`licensed_data_required`: boolean",
    )

    for term in expected_terms:
        assert term in prompt


def test_public_research_prompt_requires_exact_modes_and_source_hierarchy():
    prompt = public_research.load_research_prompt()

    for term in (
        "`rra_update`",
        "`holistic`",
        "focus on developments after its",
        "publication date",
        "Never call the output an RRA",
        "World Bank and other MDB sources",
        "UN reporting",
        "ICG or a comparable specialist source",
        "established public analytics",
        "trusted media only for genuinely recent developments",
        "Do not use licensed event-level data",
    ):
        assert term in prompt


def test_current_context_claim_rejects_unknown_context_kind():
    with pytest.raises(ValidationError):
        _claim(context_kind="unclassified")


@pytest.mark.parametrize(
    "source_url",
    [
        "https://127.1/context-update",
        "https://0177.0.0.1/context-update",
        "https://0x7f.0.0.1/context-update",
    ],
)
def test_rejects_dotted_legacy_numeric_source_authorities(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


def test_allows_ordinary_domains_with_numeric_subdomains():
    retained, rejected = retain_public_claims((_claim(source_url="https://2026.example.org/update"),))

    assert len(retained) == 1
    assert rejected == {}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://224.0.0.1/context-update",
        "https://239.255.255.250/context-update",
        "https://[ff02::1]/context-update",
    ],
)
def test_rejects_multicast_literal_source_urls(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://example.org/context\nupdate",
        "https://example.org/context\rupdate",
        "https://example.org/context\tupdate",
        "https://example.org/context\x00update",
    ],
)
def test_rejects_source_urls_containing_c0_controls(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://source.example/context-update",
        "https://source.onion/context-update",
        "https://source.localhost/context-update",
        "https://source.local/context-update",
        "https://source.internal/context-update",
        "https://source.home.arpa/context-update",
        "https://source.test/context-update",
        "https://source.invalid/context-update",
    ],
)
def test_rejects_all_special_use_hostname_suffixes(source_url: str):
    retained, rejected = retain_public_claims((_claim(source_url=source_url),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


def test_rejects_deprecated_ipv6_site_local_source_url():
    retained, rejected = retain_public_claims((_claim(source_url="https://[fec0::1]/context-update"),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}
