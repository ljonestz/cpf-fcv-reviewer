import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from anthropic import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import ValidationError

from cpf_fcv_reviewer import public_research
from cpf_fcv_reviewer.public_research import CurrentContextClaim, retain_public_claims


def test_retains_qualifying_public_claim_without_licensed_data():
    claim = CurrentContextClaim(
        claim_id="c1",
        text="The operating context may have changed since the CPF was drafted.",
        publisher="World Bank",
        source_title="Country context update",
        source_url="https://www.worldbank.org/context-update",
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
        source_url="https://www.worldbank.org/context-update",
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
        source_url="https://www.worldbank.org/context-update",
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


def test_anthropic_gateway_normalizes_only_final_cited_narrative(monkeypatch):
    beta_calls: list[dict[str, object]] = []
    parse_calls: list[dict[str, object]] = []
    source_url = "https://www.worldbank.org/update"

    class FakeBetaMessages:
        def create(self, **kwargs):
            beta_calls.append(kwargs)
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="text",
                        text="Preamble that must not reach normalization.",
                    ),
                    SimpleNamespace(
                        type="server_tool_use",
                        id="tool-1",
                        name="web_search",
                        input={"query": "country context"},
                    ),
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="World Bank update",
                                url=source_url,
                                published_at="April 30, 2025",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="The first cited narrative segment.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="World Bank update",
                                url=source_url,
                                encrypted_index="0",
                                cited_text="Source excerpt for the first segment.",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="The second cited narrative segment.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="World Bank update",
                                url=source_url,
                                encrypted_index="0",
                                cited_text="Source excerpt for the second segment.",
                            ),
                        ),
                    ),
                    SimpleNamespace(type="text", text="Uncited trailing block.", citations=()),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            parse_calls.append(kwargs)
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(
                    claims=(
                        _claim(
                            context_kind="current_development",
                            relationship="establishes",
                            text="The first cited narrative segment.",
                            source_title="World Bank update",
                            source_url=source_url,
                            source_date=date(2025, 4, 30),
                            supporting_quote="Source excerpt for the first segment.",
                        ),
                    )
                )
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=12.5
    )

    response = gateway.search("Use this prompt exactly.")

    assert len(beta_calls) == 1
    assert beta_calls[0]["messages"] == [
        {"role": "user", "content": "Use this prompt exactly."}
    ]
    assert isinstance(response, tuple)
    assert response[0].publisher == "World Bank"
    assert response[0].context_kind == "current_development"
    assert response[0].relationship == "establishes"
    assert beta_calls[0]["tools"][0]["name"] == "web_search"
    assert "concise cited synthesis" in beta_calls[0]["system"]
    search_tool = beta_calls[0]["tools"][0]
    assert search_tool["max_uses"] == 2
    assert search_tool["allowed_domains"] == list(public_research.SEARCH_ALLOWED_DOMAINS)
    allowed_domains = set(search_tool["allowed_domains"])
    # Reachable preferred sources are sent; crawler-blocked wires are excluded so
    # Anthropic does not reject the whole request with a 400.
    assert {"crisisgroup.org", "rescue.org", "acleddata.com"} <= allowed_domains
    assert public_research.CRAWLER_BLOCKED_SEARCH_DOMAINS.isdisjoint(allowed_domains)
    assert {"un.org", "reliefweb.int", "icrc.org", "issafrica.org"} <= allowed_domains
    assert {"worldbank.org", "imf.org", "oecd.org"}.isdisjoint(allowed_domains)
    assert beta_calls[0]["max_tokens"] == 2_000


    assert len(parse_calls) == 1
    parse_call = parse_calls[0]
    assert parse_call["output_format"].__name__ == "ResearchClaimBatch"
    assert "tools" not in parse_call
    assert parse_call["max_tokens"] == public_research.MAX_NORMALIZATION_OUTPUT_TOKENS
    assert public_research.MAX_NORMALIZATION_OUTPUT_TOKENS > public_research.MAX_SEARCH_OUTPUT_TOKENS
    normalized_payload = json.loads(parse_call["messages"][0]["content"])
    assert normalized_payload == {
        "narrative": "The first cited narrative segment.\nThe second cited narrative segment.",
        "sources": [
            {
                "title": "World Bank update",
                "url": source_url,
                "published_at": "2025-04-30",
                "excerpt": (
                    "Source excerpt for the first segment. [excerpt] "
                    "Source excerpt for the second segment."
                ),
                "publisher": "World Bank",
                "publication_date_basis": "provider_metadata",
            }
        ],
    }


def test_unresolved_citation_blocks_are_excluded_from_payload_and_salvage(monkeypatch):
    source_url = "https://www.worldbank.org/resolved"
    parse_calls: list[dict[str, object]] = []

    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Resolved update",
                                url=source_url,
                                published_at="2025-04-30",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="Unsupported narrative must not be grounded.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Unsupported update",
                                url="https://www.un.org/not-retrieved",
                                encrypted_index="1",
                                cited_text="Unsupported source excerpt.",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="Resolved narrative is grounded.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Resolved update",
                                url=source_url,
                                encrypted_index="0",
                                cited_text="Resolved source excerpt.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            parse_calls.append(kwargs)
            return SimpleNamespace(parsed_output=None)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    normalized_payload = json.loads(parse_calls[0]["messages"][0]["content"])
    assert normalized_payload["narrative"] == "Resolved narrative is grounded."
    assert all("Unsupported" not in claim.text for claim in result)
    assert [claim.text for claim in result] == ["Resolved source excerpt."]


def test_anthropic_gateway_continues_pause_turn_once_and_preserves_search_results(monkeypatch):
    beta_calls: list[dict[str, object]] = []
    parse_calls: list[dict[str, object]] = []
    source_url = "https://www.worldbank.org/continued-update"
    first_response = SimpleNamespace(
        content=(
            SimpleNamespace(
                type="text", text="Searching preamble that must be excluded."
            ),
            SimpleNamespace(
                type="server_tool_use", id="tool-1", name="web_search", input={"query": "context"}
            ),
            SimpleNamespace(
                type="web_search_tool_result",
                content=(
                    SimpleNamespace(
                        type="web_search_result",
                        title="Continued World Bank update",
                        url=source_url,
                        published_at="2025-04-30",
                    ),
                ),
            ),
        ),
        stop_reason="pause_turn",
    )
    second_response = SimpleNamespace(
        content=(
            SimpleNamespace(
                type="text",
                text="The continued cited narrative uses the prior search result.",
                citations=(
                    SimpleNamespace(
                        type="web_search_result_location",
                        title="Continued World Bank update",
                        url=source_url,
                        encrypted_index="0",
                        cited_text="Prior source excerpt, not assistant narrative.",
                    ),
                ),
            ),
        ),
        stop_reason="end_turn",
    )

    class FakeBetaMessages:
        def create(self, **kwargs):
            beta_calls.append(kwargs)
            return (first_response, second_response)[len(beta_calls) - 1]

    class FakeMessages:
        def parse(self, **kwargs):
            parse_calls.append(kwargs)
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(
                    claims=(
                        _claim(
                            source_url=source_url,
                            source_title="Continued World Bank update",
                            source_date=date(2025, 4, 30),
                            supporting_quote="Prior source excerpt, not assistant narrative.",
                        ),
                    )
                )
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("test-key", "test-model")

    gateway.search("Continue this prompt exactly.")

    assert len(beta_calls) == 2
    assert beta_calls[1]["messages"] == [
        {"role": "user", "content": "Continue this prompt exactly."},
        {"role": "assistant", "content": first_response.content},
    ]
    assert len(parse_calls) == 1
    normalized_payload = json.loads(parse_calls[0]["messages"][0]["content"])
    assert [call["tools"][0]["max_uses"] for call in beta_calls] == [2, 1]
    assert all(
        call["tools"][0]["allowed_domains"]
        == list(public_research.SEARCH_ALLOWED_DOMAINS)
        for call in beta_calls
    )
    assert normalized_payload["narrative"] == (
        "The continued cited narrative uses the prior search result."
    )
    assert normalized_payload["sources"] == [
        {
            "title": "Continued World Bank update",
            "url": source_url,
            "published_at": "2025-04-30",
            "excerpt": "Prior source excerpt, not assistant narrative.",
            "publisher": "World Bank",
            "publication_date_basis": "provider_metadata",
        }
    ]


def test_anthropic_gateway_continues_mapping_pause_turn_once(monkeypatch):
    beta_calls: list[dict[str, object]] = []
    source_url = "https://www.worldbank.org/mapping-pause"
    first_response = {
        "content": [
            {
                "type": "web_search_tool_result",
                "content": [
                    {
                        "type": "web_search_result",
                        "title": "Mapping pause update",
                        "url": source_url,
                        "published_at": "2025-04-30",
                    }
                ],
            }
        ],
        "stop_reason": "pause_turn",
    }
    second_response = {
        "content": [
            {
                "type": "text",
                "text": "The mapping pause response is grounded.",
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "title": "Mapping pause update",
                        "url": source_url,
                        "encrypted_index": "0",
                        "cited_text": "A provider source excerpt.",
                    }
                ],
            }
        ],
        "stop_reason": "end_turn",
    }

    class FakeBetaMessages:
        def create(self, **kwargs):
            beta_calls.append(kwargs)
            return (first_response, second_response)[len(beta_calls) - 1]

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(
                    claims=(
                        _claim(
                            source_url=source_url,
                            source_title="Mapping pause update",
                            source_date=date(2025, 4, 30),
                            supporting_quote="A provider source excerpt.",
                        ),
                    )
                )
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert len(beta_calls) == 2
    assert beta_calls[1]["messages"][1] == {
        "role": "assistant",
        "content": first_response["content"],
    }
    assert len(result) == 1


def test_anthropic_gateway_salvages_only_exact_source_excerpt(monkeypatch):
    source_url = "https://www.worldbank.org/dated-update"

    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Dated World Bank update",
                                url=source_url,
                                published_at="2025-04-30",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text=(
                            "The cited sentence is salvageable. "
                            "This uncited sentence must be excluded."
                        ),
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Dated World Bank update",
                                url=source_url,
                                encrypted_index="0",
                                cited_text="Source excerpt for the salvageable sentence.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(parsed_output=None)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("test-key", "test-model")

    result = gateway.search("Use dated cited evidence.")
    assert [claim.text for claim in result] == ["Source excerpt for the salvageable sentence."]


def test_anthropic_gateway_rejects_undated_sources_during_salvage(monkeypatch):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Undated World Bank update",
                                url="https://www.worldbank.org/undated-update",
                                page_age="2 days ago",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="The source is cited but undated.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Undated World Bank update",
                                url="https://www.worldbank.org/undated-update",
                                encrypted_index="0",
                                cited_text="Undated source excerpt.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(parsed_output=None)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("test-key", "test-model")

    with pytest.raises(ValueError, match="no parsed output"):
        gateway.search("Do not invent a source date.")


@pytest.mark.parametrize(
    ("publisher", "source_type", "source_url", "source_title"),
    [
        (
            "World Bank",
            "licensed event-level dataset",
            "https://www.worldbank.org/data",
            "Conflict events",
        ),
        ("World Bank", "public analysis", "https://www.worldbank.org/blog/post", "Update"),
        (
            "World Bank",
            "public analysis",
            "https://www.worldbank.org/research/blog-post/update",
            "Update",
        ),
        ("World Bank", "public analysis", "https://www.worldbank.org/update", "World Bank Blog"),
        (
            "World Bank",
            "public analysis",
            "https://twitter.com/worldbank/status/1",
            "Update",
        ),
        ("World Bank", "user-generated reference", "https://www.worldbank.org/update", "Update"),
        (
            "World Bank",
            "public analysis",
            "https://www.worldbank.org/update",
            "Community user-generated page",
        ),
        ("Wikipedia contributors", "public analysis", "https://wikipedia.org/page", "Update"),
        ("Independent analyst", "public analysis", "https://example.org/analysis", "Analysis"),
        (
            "Synthetic public source",
            "public analysis",
            "https://www.worldbank.org/update",
            "Update",
        ),
        ("Not World Bank", "public analysis", "https://www.worldbank.org/update", "Update"),
        (
            "World Bank affiliate",
            "public analysis",
            "https://www.worldbank.org/update",
            "Update",
        ),
    ],
)
def test_retain_public_claims_rejects_nonpermitted_public_sources(
    publisher: str, source_type: str, source_url: str, source_title: str
):
    retained, rejected = retain_public_claims(
        (
            _claim(
                publisher=publisher,
                source_type=source_type,
                source_url=source_url,
                source_title=source_title,
            ),
        )
    )

    assert retained == ()
    assert rejected == {"claim-1": "permitted institutional public source is required"}


@pytest.mark.parametrize(
    "source_title",
    [
        "Social Protection Update",
        "Community Resilience Assessment",
        "Benin Country Profile",
    ],
)
def test_retain_public_claims_allows_institutional_titles_with_generic_words(source_title: str):
    retained, rejected = retain_public_claims(
        (_claim(source_title=source_title, source_url="https://www.worldbank.org/update"),)
    )

    assert len(retained) == 1
    assert rejected == {}


def test_retain_public_claims_rejects_world_bank_indicator_api_observations():
    claim = _claim(
        publisher="World Bank",
        source_url="https://api.worldbank.org/v2/country/BEN/indicator/NY.GDP.PCAP.CD?date=2025",
    )

    retained, rejected = retain_public_claims((claim,))

    assert retained == ()
    assert rejected == {"claim-1": "permitted institutional public source is required"}


@pytest.mark.parametrize(
    ("publisher", "source_url"),
    [
        ("World Bank", "https://www.worldbank.org/update"),
        ("United Nations", "https://www.un.org/update"),
        ("United Nations Development Programme", "https://www.undp.org/update"),
        ("OECD", "https://www.oecd.org/update"),
        ("International Monetary Fund", "https://www.imf.org/update"),
        ("African Development Bank", "https://www.afdb.org/update"),
        ("Asian Development Bank", "https://www.adb.org/update"),
        ("Inter-American Development Bank", "https://www.iadb.org/update"),
        (
            "European Bank for Reconstruction and Development",
            "https://www.ebrd.com/update",
        ),
        (
            "International Committee of the Red Cross",
            "https://www.icrc.org/update",
        ),
        ("International Organization for Migration", "https://www.iom.int/update"),
        ("ReliefWeb", "https://reliefweb.int/update"),
        ("United Nations Children's Fund", "https://www.unicef.org/update"),
        ("UN Development Programme", "https://www.undp.org/update"),
        ("United Nations Office on Drugs and Crime", "https://www.unodc.org/update"),
        (
            "United Nations Office for Disaster Risk Reduction",
            "https://www.undrr.org/update",
        ),
        (
            "United Nations Entity for Gender Equality and the Empowerment of Women",
            "https://www.unwomen.org/update",
        ),
        ("Reuters", "https://www.reuters.com/world/africa/update"),
        ("Associated Press", "https://apnews.com/article/update"),
        ("BBC", "https://www.bbc.com/news/articles/update"),
        ("BBC", "https://www.bbc.co.uk/news/articles/update"),
        ("International Crisis Group", "https://www.crisisgroup.org/africa/update"),
        ("ISS Africa", "https://issafrica.org/iss-today/update"),
        (
            "Africa Center for Strategic Studies",
            "https://africacenter.org/spotlight/update",
        ),
    ],
)
def test_retain_public_claims_accepts_permitted_institutional_publishers(
    publisher: str, source_url: str
):
    retained, rejected = retain_public_claims(
        (_claim(publisher=publisher, source_url=source_url),)
    )

    assert len(retained) == 1
    assert rejected == {}


@pytest.mark.parametrize(
    ("publisher", "source_url"),
    [
        ("World Bank", "https://example.org/update"),
        ("World Bank", "https://worldbank.org.example.org/update"),
        ("Government of Kenya", "https://government-kenya.example.org/update"),
        ("Government of Kenya", "https://www.kenya.example.org/update"),
        ("Government of Kenya", "https://www.gov.evil.example.org/update"),
        ("Government of Kenya", "https://www.gov.ke/update"),
        ("National statistics office", "https://stats.gov.ke/update"),
        ("Ministry of Finance", "https://treasury.gov/update"),
        ("Government of Benin", "https://www.gouv.bj/update"),
        ("Not Government of Kenya", "https://www.gov.ke/update"),
        ("National statistics office of Kenya", "https://stats.gov.ke/update"),
        (
            "United Nations Children's Fund affiliate",
            "https://www.unicef.org/update",
        ),
        ("UN Development Programme affiliate", "https://www.undp.org/update"),
    ],
)
def test_retain_public_claims_rejects_publisher_host_mismatches(
    publisher: str, source_url: str
):
    retained, rejected = retain_public_claims(
        (_claim(publisher=publisher, source_url=source_url),)
    )

    assert retained == ()
    assert rejected == {"claim-1": "permitted institutional public source is required"}


def test_public_research_models_are_frozen_and_forbid_extra_fields():
    research_source = public_research.ResearchSource(
        title="Update", url="https://worldbank.org/update", published_at=date(2026, 8, 4)
    )
    artifact = public_research.SearchArtifact(
        narrative="A cited synthesis.", sources=(research_source,)
    )
    batch = public_research.ResearchClaimBatch(claims=(_claim(),))

    assert artifact.sources == (research_source,)
    assert batch.claims[0].claim_id == "claim-1"

    with pytest.raises(ValidationError):
        public_research.ResearchSource(
            title="Update",
            url="https://worldbank.org/update",
            published_at=date(2026, 8, 4),
            extra="reject",
        )
    with pytest.raises(ValidationError):
        artifact.narrative = "mutated"


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


@pytest.mark.parametrize("parsed_output", [None, SimpleNamespace(claims=())])
def test_anthropic_gateway_rejects_absent_or_wrong_normalized_output(
    monkeypatch, parsed_output
):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Update",
                                url="https://www.worldbank.org/update",
                                page_age="2 days ago",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="A final narrative with an undated source.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Update",
                                url="https://www.worldbank.org/update",
                                encrypted_index="0",
                                cited_text="An undated source excerpt.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(parsed_output=parsed_output)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=10
    )

    with pytest.raises(ValueError, match="no parsed output"):
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
        "source_url": "https://www.worldbank.org/context-update",
        "source_date": date(2026, 8, 1),
        "source_type": "public analysis",
        "relevance": "Tests whether the claim remains plausible.",
        "relationship": "qualifies",
        "context_kind": "structural_dynamic",
        "licensed_data_required": False,
    }
    fields.update(overrides)
    return CurrentContextClaim(**fields)



@pytest.mark.parametrize(
    ("publisher", "source_url"),
    [
        ("International Rescue Committee", "https://www.rescue.org/press-release/update"),
        ("ACLED", "https://acleddata.com/analysis/country-update"),
    ],
)
def test_public_irc_and_acled_analysis_are_trusted(publisher, source_url):
    claim = _claim(publisher=publisher, source_url=source_url)

    retained, rejected = retain_public_claims((claim,))

    assert retained == (claim,)
    assert rejected == {}


def test_acled_api_subdomain_is_not_a_public_analysis_source():
    claim = _claim(publisher="ACLED", source_url="https://api.acleddata.com/events")

    retained, _ = retain_public_claims((claim,))

    assert retained == ()


def test_research_contract_caps_sources_findings_and_bundle_size():
    sources = tuple(
        public_research.ResearchSource(
            title=f"Source {index}",
            url=f"https://www.reuters.com/source-{index}",
            published_at=date(2026, 8, 1),
        )
        for index in range(4)
    )

    with pytest.raises(ValidationError):
        public_research.SearchArtifact(narrative="Bounded.", sources=sources)
    with pytest.raises(ValidationError):
        public_research.SearchArtifact(narrative="x" * 6_001, sources=sources[:1])
    with pytest.raises(ValidationError):
        public_research.ResearchClaimBatch(
            claims=tuple(_claim(f"claim-{index}") for index in range(7))
        )


def test_search_artifact_caps_complete_serialized_source_bundle():
    source = public_research.ResearchSource(
        title="A" * 500,
        url="https://www.reuters.com/world/example-2026-08-01/",
        published_at=date(2026, 8, 1),
        excerpt="B" * 1_500,
    )

    with pytest.raises(ValidationError):
        public_research.SearchArtifact(narrative="C" * 5_000, sources=(source,))


def test_oversized_cited_excerpt_is_not_retained():
    source_url = "https://www.reuters.com/world/example-2026-08-01/"
    blocks = (
        {
            "type": "web_search_tool_result",
            "content": {
                "type": "web_search_result",
                "title": "Country update",
                "url": source_url,
                "published_at": "2026-08-01",
            },
        },
        {
            "type": "text",
            "text": "A cited finding.",
            "citations": [
                {
                    "type": "web_search_result_location",
                    "title": "Country update",
                    "url": source_url,
                    "cited_text": "x" * 1_501,
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="no cited synthesis"):
        public_research._extract_search_artifact(blocks)

def _cited_response(
    *,
    source_url: str,
    source_title: str,
    page_age: str,
    narrative: str = "The grounded narrative.",
    cited_text: str = "A source excerpt that is not assistant text.",
) -> SimpleNamespace:
    return SimpleNamespace(
        content=(
            SimpleNamespace(
                type="web_search_tool_result",
                content=(
                    SimpleNamespace(
                        type="web_search_result",
                        title=source_title,
                        url=source_url,
                        published_at=page_age,
                    ),
                ),
            ),
            SimpleNamespace(
                type="text",
                text=narrative,
                citations=(
                    SimpleNamespace(
                        type="web_search_result_location",
                        title=source_title,
                        url=source_url,
                        encrypted_index="0",
                        cited_text=cited_text,
                    ),
                ),
            ),
        ),
        stop_reason="end_turn",
    )


def test_page_age_parses_iso_and_provider_display_dates_but_not_relative_ages():
    assert public_research._parse_source_date("2025-04-30") == date(2025, 4, 30)
    assert public_research._parse_source_date("April 30, 2025") == date(2025, 4, 30)
    assert public_research._parse_source_date("2 days ago") is None


def test_canonical_source_urls_strip_default_ports_slashes_and_fragments():
    assert public_research._normalize_source_url(
        "HTTPS://WWW.WORLDBANK.ORG:443/bound/?q=1#section"
    ) == "https://www.worldbank.org/bound?q=1"
    assert public_research._normalize_source_url(
        "http://www.worldbank.org:80/bound/"
    ) == "http://www.worldbank.org/bound"
    assert public_research._normalize_source_url(
        "https://www.worldbank.org./bound"
    ) == "https://www.worldbank.org/bound"
    assert public_research._normalize_source_url(
        "https://www.worldbank.org/bound?q=1"
    ) != public_research._normalize_source_url("https://www.worldbank.org/bound?q=2")


def test_normalized_claims_match_url_and_use_retrieved_source_metadata(monkeypatch):
    source_url = "https://www.worldbank.org/bound?q=1"
    retrieved_url = "HTTPS://WWW.WORLDBANK.ORG:443/bound/?q=1#section"
    claim_url = "HTTPS://WWW.WORLDBANK.ORG.:443/bound/?q=1#section"
    source_title = "Bound update"
    source_date = date(2025, 4, 30)
    valid = _claim(
        claim_id="valid",
        source_url=claim_url,
        source_title=source_title,
        source_date=source_date,
        publisher="World Bank",
        supporting_quote="A source excerpt that is not assistant text.",
    )
    invalid_url = valid.model_copy(
        update={"claim_id": "invalid-url", "source_url": "https://www.worldbank.org/other"}
    )
    invalid_title = valid.model_copy(
        update={"claim_id": "invalid-title", "source_title": "Other update"}
    )
    invalid_date = valid.model_copy(
        update={"claim_id": "invalid-date", "source_date": date(2025, 5, 1)}
    )

    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url=retrieved_url,
                source_title=source_title,
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(
                    claims=(valid, invalid_url, invalid_title, invalid_date)
                )
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert [claim.claim_id for claim in result] == [
        "valid",
        "invalid-title",
        "invalid-date",
    ]
    assert all(claim.source_title == source_title for claim in result)
    assert all(claim.source_date == source_date for claim in result)
    assert all(claim.source_url == source_url for claim in result)


def test_uncited_retrieved_sources_are_unavailable_to_normalization(monkeypatch):
    source_a = "https://www.worldbank.org/cited"
    source_b = "https://www.worldbank.org/uncited"
    claim_a = _claim(
        claim_id="cited",
        source_url=source_a,
        source_title="Cited update",
        source_date=date(2025, 4, 30),
        text="Cited source excerpt.",
        supporting_quote="Cited source excerpt.",
        publication_date_basis="provider_metadata",
    )
    claim_b = _claim(
        claim_id="uncited",
        source_url=source_b,
        source_title="Uncited update",
        source_date=date(2025, 4, 30),
    )

    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Cited update",
                                url=source_a,
                                published_at="2025-04-30",
                            ),
                            SimpleNamespace(
                                type="web_search_result",
                                title="Uncited update",
                                url=source_b,
                                published_at="2025-04-30",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="Only the cited source supports this narrative.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Cited update",
                                url=source_a,
                                encrypted_index="0",
                                cited_text="Cited source excerpt.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(claims=(claim_a, claim_b))
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert result == (claim_a,)


def test_mapping_shaped_provider_blocks_are_extracted():
    artifact, segments = public_research._extract_search_artifact(
        (
            {
                "type": "web_search_tool_result",
                "content": {
                    "type": "web_search_result",
                    "title": "Mapped update",
                    "url": "https://www.worldbank.org/mapped",
                    "published_at": "2025-04-30",
                },
            },
            {
                "type": "text",
                "text": "Mapped cited narrative.",
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "title": "Mapped update",
                        "url": "https://www.worldbank.org/mapped",
                        "encrypted_index": "0",
                        "cited_text": "Mapped source excerpt.",
                    }
                ],
            },
        )
    )

    assert artifact.sources[0].title == "Mapped update"
    assert artifact.narrative == "Mapped cited narrative."
    assert segments[0][1] == artifact.sources


def test_web_search_error_content_fails_safely_without_logging(caplog, monkeypatch):
    error_message = "provider secret error details"
    parse_called = False

    class FakeBetaMessages:
        def create(self, **kwargs):
            return {
                "content": [
                    {
                        "type": "web_search_tool_result",
                        "content": {
                            "type": "web_search_tool_result_error",
                            "error_code": "unavailable",
                            "error_message": error_message,
                        },
                    }
                ],
                "stop_reason": "end_turn",
            }

    class FakeMessages:
        def parse(self, **kwargs):
            nonlocal parse_called
            parse_called = True
            return SimpleNamespace(parsed_output=None)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    caplog.set_level("DEBUG")

    with pytest.raises(ConnectionError, match="provider was unavailable"):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert not parse_called
    assert error_message not in caplog.text


def test_invalid_normalized_claims_fall_back_to_block_level_salvage(monkeypatch):
    source_url = "https://www.worldbank.org/fallback"
    source_title = "Fallback update"

    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url=source_url,
                source_title=source_title,
                page_age="April 30, 2025",
                narrative="The complete grounded block is the salvage unit.",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            invalid = _claim(
                source_url="https://www.worldbank.org/not-retrieved",
                source_title=source_title,
                source_date=date(2025, 4, 30),
                publisher="World Bank",
            )
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(claims=(invalid,))
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert len(result) == 1
    assert result[0].text == "A source excerpt that is not assistant text."
    assert result[0].source_date == date(2025, 4, 30)


def test_normalized_claim_uses_grounded_source_metadata_when_model_fields_drift():
    source = public_research.ResearchSource(
        title="Guinea transition update",
        url="https://www.reuters.com/world/africa/guinea-transition-update",
        publisher="Reuters",
        published_at=date(2026, 8, 30),
        publication_date_basis="provider_metadata",
        excerpt="Guinea's political transition remains uncertain.",
    )
    artifact = public_research.SearchArtifact(
        narrative="Guinea's political transition remains uncertain.",
        sources=(source,),
    )
    normalized = _claim(
        publisher="World Bank",
        source_title="Model-rewritten title",
        source_url=source.url,
        source_date=date(2026, 8, 29),
        text="Guinea's political transition remains uncertain.",
        supporting_quote="Guinea's political transition remains uncertain.",
        publication_date_basis="canonical_url",
    )

    retained = public_research._validate_normalized_claims((normalized,), artifact)

    assert retained == (
        normalized.model_copy(
            update={
                "publisher": "Reuters",
                "source_title": source.title,
                "source_date": source.published_at,
                "source_url": source.url,
                "supporting_quote": normalized.supporting_quote,
                "publication_date_basis": "provider_metadata",
            }
        ),
    )


def test_normalization_exception_falls_back_to_block_level_salvage(monkeypatch):
    beta_calls = []
    parse_calls = []
    source_url = "https://www.worldbank.org/exception-fallback"

    class FakeBetaMessages:
        def create(self, **kwargs):
            beta_calls.append(kwargs)
            return _cited_response(
                source_url=source_url,
                source_title="Exception fallback update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            parse_calls.append(kwargs)
            raise ValidationError.from_exception_data(
                "ResearchClaimBatch",
                [{"type": "missing", "loc": ("claims",), "input": {}}],
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert len(result) == 1
    assert result[0].text == "A source excerpt that is not assistant text."
    assert len(beta_calls) == 1
    assert len(parse_calls) == 1


@pytest.mark.parametrize(
    "narrative",
    [
        "Cited sentence. Uncited sentence without punctuation",
        "Unpunctuated cited block",
    ],
)
def test_salvage_rejects_ambiguous_or_unpunctuated_cited_blocks(monkeypatch, narrative):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.worldbank.org/ambiguous-salvage",
                source_title="Ambiguous salvage update",
                page_age="2025-04-30",
                narrative=narrative,
                cited_text=narrative,
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise ValidationError.from_exception_data(
                "ResearchClaimBatch",
                [{"type": "missing", "loc": ("claims",), "input": {}}],
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(ValidationError):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")


def test_dated_government_source_salvage_is_not_accepted(monkeypatch):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.gov.ke/government-update",
                source_title="Government of Kenya update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise ValidationError.from_exception_data(
                "ResearchClaimBatch",
                [{"type": "missing", "loc": ("claims",), "input": {}}],
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(ValidationError):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")


def test_normalization_value_error_propagates_without_salvage(monkeypatch):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.worldbank.org/value-error",
                source_title="Value error update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise ValueError("invalid JSON shape")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(ValueError, match="invalid JSON shape"):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")


def test_anthropic_api_error_propagates_without_salvage(monkeypatch):
    response = httpx.Response(
        401,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )
    provider_error = APIStatusError(
        "provider authentication failed",
        response=response,
        body={"error": {"message": "secret details"}},
    )

    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.worldbank.org/api-error",
                source_title="API error update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise provider_error

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(APIStatusError) as raised:
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert raised.value is provider_error


@pytest.mark.parametrize(
    ("provider_error", "expected"),
    [
        (
            APIConnectionError(
                request=httpx.Request(
                    "POST", "https://api.anthropic.com/v1/messages"
                )
            ),
            ConnectionError,
        ),
        (
            APITimeoutError(
                httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            ),
            TimeoutError,
        ),
    ],
)
def test_anthropic_transport_failures_normalize_at_gateway_boundary(
    monkeypatch, provider_error, expected
):
    search_calls = []

    class FakeBetaMessages:
        def create(self, **kwargs):
            search_calls.append(kwargs)
            raise provider_error

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()),
        messages=SimpleNamespace(),
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(expected):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert len(search_calls) == 1


def test_provider_runtime_error_propagates_without_salvage(monkeypatch):
    class ProviderError(RuntimeError):
        pass

    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.worldbank.org/provider-error",
                source_title="Provider error update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise ProviderError("provider permission denied")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(ProviderError, match="provider permission denied"):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")


def test_normalization_exception_is_reraised_when_salvage_is_empty(monkeypatch):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url="https://www.worldbank.org/relative",
                source_title="Relative age update",
                page_age="two days ago",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise RuntimeError("normalization failed")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    with pytest.raises(RuntimeError, match="normalization failed"):
        public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")


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


def test_accepts_and_normalizes_an_institutional_public_source_url():
    claim = _claim(source_url="  https://www.worldbank.org/context-update  ")

    retained, rejected = retain_public_claims((claim,))

    assert claim.source_url == "https://www.worldbank.org/context-update"
    assert retained == (claim,)
    assert rejected == {}


def test_rejects_all_claims_with_a_duplicate_claim_id():
    first = _claim("duplicate-claim")
    second = first.model_copy(update={"text": "A second claim with the same identifier."})

    retained, rejected = retain_public_claims((first, second))

    assert retained == ()
    assert rejected == {"duplicate-claim": "duplicate claim ID is not permitted"}


def test_public_research_prompt_requests_plain_text_cited_synthesis():
    prompt = public_research.load_research_prompt()

    expected_terms = ("concise", "plain text", "cited synthesis")

    for term in expected_terms:
        assert term in prompt
    assert "strict JSON array only" not in prompt

    permitted_hierarchy = (
        "public UN",
        "IRC",
        "ACLED analysis",
        "ICRC",
        "IOM",
        "ReliefWeb",
    )
    for term in permitted_hierarchy:
        assert term in prompt
    for term in (
        "Reuters",
        "Associated Press",
        "BBC",
        "International Crisis Group",
        "ISS Africa",
        "Africa Center for Strategic Studies",
    ):
        assert term in prompt
    assert "public analytics" not in prompt
    assert "trusted media" not in prompt
    assert "licensed ACLED" in prompt
    assert "official national government sources" not in prompt


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
        "https://www.worldbank.org/context-update",
        "https://subdomain.worldbank.org/context-update",
        "https://2026.worldbank.org/context-update",
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


def test_public_research_prompt_omits_the_second_call_schema_contract():
    prompt = public_research.load_research_prompt()

    assert "`claim_id`" not in prompt
    assert "strict JSON array only" not in prompt


def test_public_research_prompt_requires_exact_modes_and_source_hierarchy():
    prompt = public_research.load_research_prompt()

    for term in (
        "`rra_update`",
        "`holistic`",
        "focus on developments after its",
        "publication date",
        "Never call the output an RRA",
        "Prefer recent International Crisis Group",
        "selected country",
        "One substantive trusted source",
        "three sources and six short findings",
        "publisher validation allowlist",
        "generic development or indicator sources",
        "licensed event-level data",
    ):
        assert term in prompt


def test_public_research_prompt_targets_missing_non_economic_themes_on_retry():
    prompt = public_research.load_research_prompt()

    for term in (
        "non-economic",
        "governance",
        "conflict",
        "institutional",
        "security",
        "social",
        "service-delivery",
        "already-covered economic themes",
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
    retained, rejected = retain_public_claims(
        (_claim(source_url="https://2026.worldbank.org/update"),)
    )

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
    retained, rejected = retain_public_claims(
        (_claim(source_url="https://[fec0::1]/context-update"),)
    )

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}


def test_extraction_fails_closed_instead_of_cutting_an_oversized_bundle():
    title = "A" * 500
    url = "https://www.reuters.com/world/example-2026-08-01/"
    blocks = (
        {
            "type": "web_search_tool_result",
            "content": {
                "type": "web_search_result",
                "title": title,
                "url": url,
                "published_at": "2026-08-01",
            },
        },
        {
            "type": "text",
            "text": "C" * 5_000,
            "citations": [
                {
                    "type": "web_search_result_location",
                    "title": title,
                    "url": url,
                    "cited_text": "B" * 1_500,
                }
            ],
        },
    )

    with pytest.raises(ValidationError, match="Serialized source bundle"):
        public_research._extract_search_artifact(blocks)


@pytest.mark.parametrize(
    ("item", "expected_date", "expected_basis"),
    [
        (
            {
                "title": "Synthetic Reuters report",
                "url": "https://www.reuters.com/world/africa/headline-2024-01-15/",
                "page_age": "1 day ago",
            },
            date(2024, 1, 15),
            "canonical_url",
        ),
        (
            {
                "title": "Synthetic Reuters report",
                "url": "https://www.reuters.com/world/africa/2026/08/30/story-id/",
                "published_at": "2026-08-30T14:15:00Z",
                "page_age": "today",
            },
            date(2026, 8, 30),
            "provider_metadata",
        ),
        (
            {
                "title": "Synthetic AP report",
                "url": "https://apnews.com/article/opaque-story-id",
                "page_age": "1 day ago",
            },
            None,
            None,
        ),
        (
            {
                "title": "Synthetic conflicting Reuters report",
                "url": "https://www.reuters.com/world/africa/headline-2026-08-30/",
                "published_at": "2026-08-29",
            },
            None,
            "conflicting",
        ),
    ],
)
def test_source_dates_use_publication_provenance_not_page_age(
    item, expected_date, expected_basis
):
    _, _, published_at, basis = public_research._source_metadata(item)

    assert published_at == expected_date
    assert basis == expected_basis


@pytest.mark.parametrize(
    ("result_date", "expected_date", "expected_basis"),
    [
        (None, date(2026, 8, 30), "source_excerpt"),
        ("2026-08-29", None, "conflicting"),
    ],
)
def test_publication_labelled_excerpt_resolves_or_conflicts(
    result_date, expected_date, expected_basis
):
    url = "https://apnews.com/article/synthetic-publication-date"
    result = {
        "type": "web_search_result",
        "title": "Synthetic Guinea update",
        "url": url,
    }
    if result_date is not None:
        result["published_at"] = result_date
    artifact, _ = public_research._extract_search_artifact(
        (
            {"type": "web_search_tool_result", "content": result},
            {
                "type": "text",
                "text": "Synthetic cited synthesis.",
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "title": "Synthetic Guinea update",
                        "url": url,
                        "cited_text": (
                            "Published: 2026-08-30 - Guinea's transition remains unsettled."
                        ),
                    }
                ],
            },
        ),
        selected_country="Guinea",
    )

    assert artifact.sources[0].published_at == expected_date
    assert artifact.sources[0].publication_date_basis == expected_basis


@pytest.mark.parametrize("label", ["Published", "Publication date"])
def test_publication_labelled_excerpt_accepts_display_date(label):
    assert public_research._publication_date_from_excerpt(
        f"{label}: August 30, 2026 - Guinea's transition remains unsettled."
    ) == date(2026, 8, 30)


def test_normalized_claim_requires_quote_from_exact_country_source():
    transition = public_research.ResearchSource(
        title="Synthetic Guinea political transition report",
        url="https://www.reuters.com/world/africa/guinea-transition-2026-08-30",
        publisher="Reuters",
        published_at=date(2026, 8, 30),
        publication_date_basis="canonical_url",
        excerpt="Guinea's transition timetable remains contested.",
    )
    land = public_research.ResearchSource(
        title="Synthetic regional land report",
        url="https://apnews.com/article/synthetic-land-report",
        publisher="Associated Press",
        published_at=date(2026, 8, 29),
        publication_date_basis="provider_metadata",
        excerpt="Land disputes increased in a different country.",
    )
    missing_excerpt = public_research.ResearchSource(
        title="Synthetic Guinea report without excerpt",
        url="https://www.bbc.com/news/articles/synthetic-no-excerpt",
        publisher="BBC",
        published_at=date(2026, 8, 28),
        publication_date_basis="provider_metadata",
    )
    artifact = public_research.SearchArtifact(
        narrative="Synthetic cited synthesis.", sources=(transition, land, missing_excerpt)
    )
    valid = _claim(
        "valid",
        source_url=transition.url,
        supporting_quote="Guinea's transition timetable remains contested.",
    )
    swapped = _claim(
        "swapped",
        source_url=land.url,
        supporting_quote="Guinea's transition timetable remains contested.",
    )
    fabricated = _claim(
        "fabricated", source_url=transition.url, supporting_quote="Fabricated quote."
    )
    unknown = _claim(
        "unknown",
        source_url="https://www.reuters.com/world/unknown-2026-08-30/",
        supporting_quote="Guinea's transition timetable remains contested.",
    )
    wrong_country = _claim(
        "wrong-country", source_url=land.url, supporting_quote=land.excerpt
    )
    missing_quote = _claim("missing-quote", source_url=transition.url)
    no_excerpt = _claim(
        "no-excerpt",
        source_url=missing_excerpt.url,
        supporting_quote="Guinea claim not present in retrieved evidence.",
    )

    retained = public_research._validate_normalized_claims(
        (valid, swapped, fabricated, unknown, wrong_country, missing_quote, no_excerpt),
        artifact,
        selected_country="Guinea",
    )

    assert [claim.claim_id for claim in retained] == ["valid"]
    assert retained[0].text == transition.excerpt
    assert retained[0].publisher == "Reuters"
    assert retained[0].publication_date_basis == "canonical_url"


def test_salvage_uses_source_excerpt_and_requires_country_connection():
    source = public_research.ResearchSource(
        title="Synthetic Guinea update",
        url="https://www.reuters.com/world/africa/guinea-update-2026-08-30/",
        publisher="Reuters",
        published_at=date(2026, 8, 30),
        publication_date_basis="canonical_url",
        excerpt="Guinea's transition timetable remains contested.",
    )

    retained = public_research._salvage_grounded_segments(
        ((source.excerpt, (source,)),),
        selected_country="Guinea",
    )
    rejected = public_research._salvage_grounded_segments(
        ((source.excerpt, (source,)),), selected_country="Somalia"
    )

    assert retained[0].text == source.excerpt
    assert retained[0].supporting_quote == source.excerpt
    assert rejected == ()


def test_bounded_article_metadata_reads_publication_fields_only():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=(
                '<meta property="article:published_time" content="2026-08-30T10:00:00Z">'
                '<meta property="article:modified_time" content="2026-09-01T10:00:00Z">'
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        resolved = public_research._fetch_article_publication_date(
            "https://apnews.com/article/opaque-story-id", client
        )
        blocked = public_research._fetch_article_publication_date(
            "http://apnews.com/article/opaque-story-id", client
        )

    assert resolved == date(2026, 8, 30)
    assert blocked is None
    assert len(requests) == 1


def test_gateway_performs_at_most_one_metadata_get_for_opaque_sources(monkeypatch):
    urls = (
        "https://apnews.com/article/opaque-story-id",
        "https://www.bbc.com/news/articles/opaque-story-id",
    )
    metadata_requests = []

    def metadata_handler(request: httpx.Request) -> httpx.Response:
        metadata_requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/xhtml+xml"},
            text='<script type="application/ld+json">{"datePublished":"2026-08-30"}</script>',
        )

    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=tuple(
                            SimpleNamespace(
                                type="web_search_result",
                                title=f"Guinea update {i}",
                                url=url,
                            )
                            for i, url in enumerate(urls)
                        ),
                    ),
                    *tuple(
                        SimpleNamespace(
                            type="text",
                            text=f"Synthetic assistant narrative {i}.",
                            citations=(
                                SimpleNamespace(
                                    type="web_search_result_location",
                                    title=f"Guinea update {i}",
                                    url=url,
                                    cited_text=f"Guinea current condition {i} remains unsettled.",
                                ),
                            ),
                        )
                        for i, url in enumerate(urls)
                    ),
                ),
                stop_reason="end_turn",
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()),
        messages=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(parsed_output=None)),
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    with httpx.Client(transport=httpx.MockTransport(metadata_handler)) as metadata_client:
        result = public_research.AnthropicPublicResearchGateway(
            "key", "model", metadata_client=metadata_client
        ).search("country: Guinea")

    assert len(metadata_requests) == 1
    assert [claim.source_url for claim in result] == [urls[0]]
    assert result[0].publication_date_basis == "article_metadata"


def test_article_metadata_does_not_fetch_acled_api():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<meta property="article:published_time" content="2026-08-30">',
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert public_research._fetch_article_publication_date(
            "https://api.acleddata.com/events", client
        ) is None
    assert requests == []


def test_country_scope_rejects_longer_different_country_name():
    source = public_research.ResearchSource(
        title="Guinea-Bissau conflict update",
        url="https://www.reuters.com/world/africa/guinea-bissau-2026-08-30/",
        excerpt="Violence increased in Guinea-Bissau.",
    )
    assert not public_research._source_mentions_country(source, "Guinea")


def test_country_scope_keeps_source_mentioning_selected_and_neighbour():
    # West-African reporting frequently references neighbours; a genuine Guinea
    # source must not be discarded merely because it also mentions Guinea-Bissau.
    source = public_research.ResearchSource(
        title="Guinea transition update",
        url="https://africacenter.org/guinea-transition",
        excerpt=(
            "Guinea's junta delayed elections again, while neighbouring "
            "Guinea-Bissau and Mali faced their own instability."
        ),
    )
    assert public_research._source_mentions_country(source, "Guinea")


def test_country_scope_rejects_neighbour_only_variants():
    for excerpt in (
        "Violence increased in Guinea-Bissau.",
        "Equatorial Guinea announced new oil revenues.",
        "Papua New Guinea reported tribal clashes.",
    ):
        source = public_research.ResearchSource(
            title="",
            url="https://example.invalid",
            excerpt=excerpt,
        )
        assert not public_research._source_mentions_country(source, "Guinea")


def test_country_scope_keeps_plain_selected_country():
    source = public_research.ResearchSource(
        title="",
        url="https://example.invalid",
        excerpt="Guinea's security forces clashed with protesters in Conakry.",
    )
    assert public_research._source_mentions_country(source, "Guinea")


def test_source_metadata_reads_page_age_date():
    # Anthropic's real web_search_result carries the date in `page_age`.
    item = SimpleNamespace(
        type="web_search_result",
        title="Guinea transition update",
        url="https://africacenter.org/guinea",
        page_age="April 30, 2025",
    )
    _title, _url, published_at, basis = public_research._source_metadata(item)
    assert published_at == date(2025, 4, 30)
    assert basis == "provider_metadata"


def test_source_metadata_still_reads_published_at_field():
    item = SimpleNamespace(
        type="web_search_result",
        title="x",
        url="https://africacenter.org/y",
        published_at="2025-04-30",
    )
    _title, _url, published_at, _basis = public_research._source_metadata(item)
    assert published_at == date(2025, 4, 30)


PUBLIC_DIAGNOSTIC_KEYS = {
    "source_candidates",
    "source_linked_excerpts",
    "missing_publication_date",
    "untrusted_host_publisher",
    "country_mismatch",
    "normalization_failure",
}


def _diagnostic_gateway(monkeypatch, response, parsed_output, *, metadata_client=None):
    class FakeBetaMessages:
        def create(self, **kwargs):
            return response

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(parsed_output=parsed_output)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    return public_research.AnthropicPublicResearchGateway(
        "key", "model", metadata_client=metadata_client
    )


def test_gateway_exposes_fixed_safe_diagnostics_for_accepted_source(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/guinea-update-2026-08-30/"
    quote = "Guinea political violence disrupted local services."
    normalized = _claim(
        publisher="Reuters",
        source_url=source_url,
        source_title="Guinea update",
        source_date=date(2026, 8, 30),
        text=quote,
        supporting_quote=quote,
        publication_date_basis="canonical_url",
    )
    gateway = _diagnostic_gateway(
        monkeypatch,
        _cited_response(
            source_url=source_url,
            source_title="Guinea update",
            page_age="2026-08-30",
            cited_text=quote,
        ),
        public_research.ResearchClaimBatch(claims=(normalized,)),
    )

    claims = gateway.search("country: Guinea")

    assert len(claims) == 1
    assert claims[0].text == quote
    assert claims[0].source_url == normalized.source_url.rstrip("/")
    assert set(gateway.last_diagnostics) == PUBLIC_DIAGNOSTIC_KEYS
    assert gateway.last_diagnostics == {
        "source_candidates": 1,
        "source_linked_excerpts": 1,
        "missing_publication_date": 0,
        "untrusted_host_publisher": 0,
        "country_mismatch": 0,
        "normalization_failure": 0,
    }


def test_gateway_diagnostics_count_country_mismatch_without_source_content(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/somalia-update-2026-08-30/"
    quote = "Somalia political violence disrupted local services."
    gateway = _diagnostic_gateway(
        monkeypatch,
        _cited_response(
            source_url=source_url,
            source_title="Somalia update",
            page_age="2026-08-30",
            cited_text=quote,
        ),
        None,
    )

    with pytest.raises(ValueError, match="no cited synthesis"):
        gateway.search("country: Guinea")

    assert gateway.last_diagnostics["source_candidates"] == 1
    assert gateway.last_diagnostics["source_linked_excerpts"] == 1
    assert gateway.last_diagnostics["country_mismatch"] == 1
    assert all(type(value) is int and value >= 0 for value in gateway.last_diagnostics.values())
    assert "Somalia" not in str(gateway.last_diagnostics)


def test_gateway_diagnostics_count_missing_date_and_normalization_failure(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/guinea-undated/"
    quote = "Guinea political violence disrupted local services."
    gateway = _diagnostic_gateway(
        monkeypatch,
        _cited_response(
            source_url=source_url,
            source_title="Guinea undated update",
            page_age="unknown",
            cited_text=quote,
        ),
        None,
        metadata_client=object(),
    )

    with pytest.raises(ValueError, match="no parsed output"):
        gateway.search("country: Guinea")

    assert gateway.last_diagnostics["missing_publication_date"] == 1
    assert gateway.last_diagnostics["normalization_failure"] == 1

def test_empty_web_search_result_is_successful_and_not_malformed(monkeypatch):
    response = SimpleNamespace(
        content=(
            SimpleNamespace(type="web_search_tool_result", content=()),
        ),
        stop_reason="end_turn",
    )
    gateway = _diagnostic_gateway(monkeypatch, response, None)

    assert gateway.search("country: Guinea") == ()
    assert set(gateway.last_diagnostics.values()) == {0}


def test_valid_source_survives_alongside_search_tool_error(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/guinea-update-2026-08-30/"
    quote = "Guinea political violence disrupted local services."
    valid_response = _cited_response(
        source_url=source_url,
        source_title="Guinea update",
        page_age="2026-08-30",
        cited_text=quote,
    )
    error_block = SimpleNamespace(
        type="web_search_tool_result",
        content=SimpleNamespace(
            type="web_search_tool_result_error",
            error_code="unavailable",
            error_message="private provider detail",
        ),
    )
    response = SimpleNamespace(
        content=(error_block, *valid_response.content),
        stop_reason="end_turn",
    )
    normalized = _claim(
        publisher="Reuters",
        source_url=source_url,
        source_title="Guinea update",
        source_date=date(2026, 8, 30),
        text=quote,
        supporting_quote=quote,
    )
    gateway = _diagnostic_gateway(
        monkeypatch,
        response,
        public_research.ResearchClaimBatch(claims=(normalized,)),
    )

    claims = gateway.search("country: Guinea")

    assert len(claims) == 1
    assert gateway.last_diagnostics["source_candidates"] == 1
    assert "private provider detail" not in str(gateway.last_diagnostics)

def test_unknown_nonempty_search_item_is_malformed_not_empty(monkeypatch):
    response = SimpleNamespace(
        content=(
            SimpleNamespace(
                type="web_search_tool_result",
                content=SimpleNamespace(type="unexpected_provider_item"),
            ),
        ),
        stop_reason="end_turn",
    )
    gateway = _diagnostic_gateway(monkeypatch, response, None)

    with pytest.raises(ValueError, match="malformed search results"):
        gateway.search("country: Guinea")


def test_missing_date_is_recorded_before_metadata_client_failure(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/guinea-undated/"
    quote = "Guinea political violence disrupted local services."
    response = _cited_response(
        source_url=source_url,
        source_title="Guinea undated update",
        page_age="unknown",
        cited_text=quote,
    )

    class BrokenMetadataClient:
        def stream(self, *args, **kwargs):
            raise RuntimeError("programming failure")

    gateway = _diagnostic_gateway(
        monkeypatch,
        response,
        None,
        metadata_client=BrokenMetadataClient(),
    )

    with pytest.raises(RuntimeError, match="programming failure"):
        gateway.search("country: Guinea")

    assert gateway.last_diagnostics["missing_publication_date"] == 1


def test_object_shaped_search_tool_error_is_unavailable(monkeypatch):
    response = SimpleNamespace(
        content=(
            SimpleNamespace(
                type="web_search_tool_result",
                content=SimpleNamespace(
                    type="web_search_tool_result_error",
                    error_code="unavailable",
                    error_message="private provider detail",
                ),
            ),
        ),
        stop_reason="end_turn",
    )
    gateway = _diagnostic_gateway(monkeypatch, response, None)

    with pytest.raises(ConnectionError, match="provider was unavailable"):
        gateway.search("country: Guinea")

    assert set(gateway.last_diagnostics.values()) == {0}
    assert "private provider detail" not in str(gateway.last_diagnostics)


def test_selected_country_must_appear_in_excerpt_not_only_regional_title():
    source = public_research.ResearchSource(
        title="Somalia and Kenya regional security update",
        url="https://www.reuters.com/world/africa/regional-update-2026-08-30/",
        published_at=date(2026, 8, 30),
        excerpt="Violence increased in Kenya.",
    )

    assert not public_research._source_mentions_country(source, "Somalia")


def test_salvage_uses_final_conflicting_date_record_for_same_url():
    url = "https://apnews.com/article/synthetic-conflict-date"
    title = "Somalia political update"
    quote = "Political violence in Somalia increased."
    blocks = (
        {
            "type": "web_search_tool_result",
            "content": [
                {
                    "type": "web_search_result",
                    "title": title,
                    "url": url,
                    "published_at": "2026-08-30",
                }
            ],
        },
        {
            "type": "text",
            "text": quote,
            "citations": [
                {
                    "type": "web_search_result_location",
                    "title": title,
                    "url": url,
                    "cited_text": quote,
                }
            ],
        },
        {
            "type": "text",
            "text": quote,
            "citations": [
                {
                    "type": "web_search_result_location",
                    "title": title,
                    "url": url,
                    "published_at": "2026-08-29",
                    "cited_text": quote,
                }
            ],
        },
    )

    artifact, segments = public_research._extract_search_artifact(
        blocks, selected_country="Somalia"
    )

    assert artifact.sources[0].publication_date_basis == "conflicting"
    assert public_research._salvage_grounded_segments(
        segments, selected_country="Somalia"
    ) == ()


def test_same_url_preserves_later_useful_excerpt_within_source_bound():
    url = "https://www.reuters.com/world/africa/somalia-update-2026-08-30/"
    title = "Somalia current update"
    blocks = [
        {
            "type": "web_search_tool_result",
            "content": [{"type": "web_search_result", "title": title, "url": url}],
        }
    ]
    for quote in (
        "The population estimate for Somalia was revised.",
        "Political violence increased in Somalia.",
    ):
        blocks.append(
            {
                "type": "text",
                "text": quote,
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "title": title,
                        "url": url,
                        "cited_text": quote,
                    }
                ],
            }
        )

    artifact, _ = public_research._extract_search_artifact(
        tuple(blocks), selected_country="Somalia"
    )

    assert "Political violence increased in Somalia." in artifact.sources[0].excerpt


def test_primary_reliefweb_copy_without_originating_publisher_is_not_accepted():
    quote = "Political violence increased in Somalia."
    source = public_research.ResearchSource(
        title="Somalia situation report",
        url="https://reliefweb.int/report/somalia/situation-report",
        publisher="ReliefWeb",
        published_at=date(2026, 8, 30),
        excerpt=quote,
    )
    claim = _claim(
        publisher="ReliefWeb",
        source_url=source.url,
        source_title=source.title,
        source_date=source.published_at,
        text=quote,
        supporting_quote=quote,
    )

    accepted = public_research._validate_normalized_claims(
        (claim,),
        public_research.SearchArtifact(narrative=quote, sources=(source,)),
        selected_country="Somalia",
    )

    assert accepted == ()


def test_gateway_stops_before_operation_after_attempt_deadline(monkeypatch):
    now = [0.0]
    url = "https://www.reuters.com/world/africa/somalia-update-2026-08-30/"
    quote = "Political violence increased in Somalia."
    response = _cited_response(
        source_url=url,
        source_title="Somalia update",
        page_age="2026-08-30",
        cited_text=quote,
    )

    class BetaMessages:
        def create(self, **kwargs):
            assert kwargs["timeout"] == 90.0
            now[0] = 91.0
            return response

    class Messages:
        def parse(self, **kwargs):
            raise AssertionError("normalization must not start after the deadline")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=BetaMessages()),
        messages=Messages(),
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway(
        "key",
        "model",
        timeout_seconds=90.0,
        monotonic=lambda: now[0],
    )

    with pytest.raises(TimeoutError, match="deadline"):
        gateway.search("country: Somalia")


def test_metadata_client_construction_failure_skips_undated_source(monkeypatch):
    source_url = "https://www.reuters.com/world/africa/guinea-undated/"
    quote = "Political violence increased in Guinea."
    response = _cited_response(
        source_url=source_url,
        source_title="Guinea undated update",
        page_age="unknown",
        cited_text=quote,
    )

    class BrokenClient:
        def __init__(self, **kwargs):
            raise OSError("invalid certificate path")

    gateway = _diagnostic_gateway(monkeypatch, response, None)
    monkeypatch.setattr(public_research.httpx, "Client", BrokenClient)

    with pytest.raises(ValueError, match="no parsed output"):
        gateway.search("country: Guinea")
    assert gateway.last_diagnostics["missing_publication_date"] == 1


def test_salvage_keeps_each_sentence_from_merged_same_url_excerpts():
    url = "https://www.reuters.com/world/africa/somalia-update-2026-08-30/"
    quotes = (
        "Population estimate for Somalia rose.",
        "Political violence increased in Somalia.",
    )
    blocks = []
    for quote in quotes:
        blocks.extend(
            (
                {
                    "type": "web_search_tool_result",
                    "content": [
                        {
                            "type": "web_search_result",
                            "title": "Somalia update",
                            "url": url,
                            "page_age": "2026-08-30",
                        }
                    ],
                },
                {
                    "type": "text",
                    "text": quote,
                    "citations": [
                        {
                            "type": "web_search_result_location",
                            "title": "Somalia update",
                            "url": url,
                            "cited_text": quote,
                        }
                    ],
                },
            )
        )

    _, segments = public_research._extract_search_artifact(
        tuple(blocks), selected_country="Somalia"
    )
    claims = public_research._salvage_grounded_segments(
        segments, selected_country="Somalia"
    )

    assert tuple(claim.supporting_quote for claim in claims) == quotes


def test_normalized_claim_country_must_be_in_exact_quote_not_other_excerpt():
    url = "https://www.reuters.com/world/africa/regional-update"
    source = public_research.ResearchSource(
        title="Somalia and Kenya update",
        url=url,
        publisher="Reuters",
        published_at=date(2026, 8, 30),
        excerpt=(
            "Somalia held local consultations. […] "
            "Political violence increased in Kenya."
        ),
    )
    quote = "Political violence increased in Kenya."
    claim = _claim(
        publisher="Reuters",
        source_url=url,
        source_title=source.title,
        source_date=source.published_at,
        text=quote,
        supporting_quote=quote,
    )

    accepted = public_research._validate_normalized_claims(
        (claim,),
        public_research.SearchArtifact(narrative=source.excerpt, sources=(source,)),
        selected_country="Somalia",
    )

    assert accepted == ()


def test_article_metadata_stream_stops_at_shared_attempt_deadline():
    now = [0.0]
    chunks = [0]

    class Response:
        status_code = 200
        headers = {"content-type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def iter_bytes(self):
            for value in (b"<html>", b"<meta>", b"</html>"):
                now[0] += 0.6
                chunks[0] += 1
                yield value

    class Client:
        def stream(self, *_args, **_kwargs):
            return Response()

    result = public_research._fetch_article_publication_date(
        "https://www.reuters.com/world/africa/guinea-update",
        Client(),
        timeout=1.0,
        deadline=1.0,
        monotonic=lambda: now[0],
    )

    assert result is None
    assert chunks[0] == 2


def test_overflow_source_remains_available_for_local_qualification():
    sources = tuple(
        {
            "type": "web_search_result",
            "title": f"Somalia update {index}",
            "url": f"https://www.reuters.com/world/africa/somalia-{index}/",
            "published_at": "2026-08-30",
        }
        for index in range(4)
    )
    blocks = [
        {
            "type": "web_search_tool_result",
            "content": list(sources),
        }
    ]
    for index, source in enumerate(sources):
        quote = (
            "Political violence increased in Somalia."
            if index == 3
            else f"Somalia population estimate {index} was revised."
        )
        blocks.append(
            {
                "type": "text",
                "text": quote,
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "title": source["title"],
                        "url": source["url"],
                        "published_at": source["published_at"],
                        "cited_text": quote,
                    }
                ],
            }
        )

    artifact, segments = public_research._extract_search_artifact(
        tuple(blocks), selected_country="Somalia"
    )
    claims = public_research._salvage_grounded_segments(
        segments, selected_country="Somalia"
    )

    assert len(artifact.sources) == public_research.MAX_RETAINED_SOURCES
    assert len(segments) == 4
    assert len(claims) == 4
    assert claims[-1].supporting_quote == "Political violence increased in Somalia."
