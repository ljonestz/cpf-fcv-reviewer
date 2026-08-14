import json
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
                                page_age="April 30, 2025",
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

    assert beta_calls[0]["messages"] == [
        {"role": "user", "content": "Use this prompt exactly."}
    ]
    assert isinstance(response, tuple)
    assert response[0].publisher == "World Bank"
    assert response[0].context_kind == "current_development"
    assert response[0].relationship == "establishes"
    assert beta_calls[0]["tools"][0]["name"] == "web_search"
    assert "concise cited synthesis" in beta_calls[0]["system"]

    assert len(parse_calls) == 1
    parse_call = parse_calls[0]
    assert parse_call["output_format"].__name__ == "ResearchClaimBatch"
    assert "tools" not in parse_call
    normalized_payload = json.loads(parse_call["messages"][0]["content"])
    assert normalized_payload == {
        "narrative": "The first cited narrative segment.\nThe second cited narrative segment.",
        "sources": [
            {
                "title": "World Bank update",
                "url": source_url,
                "published_at": "2025-04-30",
            }
        ],
    }


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
                        page_age="2025-04-30",
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
    assert normalized_payload["narrative"] == (
        "The continued cited narrative uses the prior search result."
    )
    assert normalized_payload["sources"] == [
        {
            "title": "Continued World Bank update",
            "url": source_url,
            "published_at": "2025-04-30",
        }
    ]


def test_anthropic_gateway_salvages_only_dated_cited_sentences_with_stable_ids(monkeypatch):
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
                                page_age="2025-04-30",
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

    first = gateway.search("Use dated cited evidence.")
    second = gateway.search("Use dated cited evidence.")

    assert len(first) == 1
    assert first == second
    assert first[0].text == (
        "The cited sentence is salvageable. This uncited sentence must be excluded."
    )
    assert first[0].source_date == date(2025, 4, 30)
    assert first[0].source_url == source_url
    assert first[0].claim_id.startswith("sha256:")


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
        ("Government of Kenya", "https://www.gov.ke/update"),
        ("Official national government", "https://www.gov.ke/update"),
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


def _cited_response(
    *,
    source_url: str,
    source_title: str,
    page_age: str,
    narrative: str = "The grounded narrative.",
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
                        page_age=page_age,
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
                        cited_text="A source excerpt that is not assistant text.",
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


def test_normalized_claims_must_match_retrieved_source_metadata(monkeypatch):
    source_url = "https://www.worldbank.org/bound"
    source_title = "Bound update"
    source_date = date(2025, 4, 30)
    valid = _claim(
        claim_id="valid",
        source_url=source_url,
        source_title=source_title,
        source_date=source_date,
        publisher="World Bank",
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
                source_url=source_url,
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

    assert result == (valid,)


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
    assert result[0].text == "The complete grounded block is the salvage unit."
    assert result[0].source_date == date(2025, 4, 30)


def test_normalization_exception_falls_back_to_block_level_salvage(monkeypatch):
    source_url = "https://www.worldbank.org/exception-fallback"

    class FakeBetaMessages:
        def create(self, **kwargs):
            return _cited_response(
                source_url=source_url,
                source_title="Exception fallback update",
                page_age="2025-04-30",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            raise RuntimeError("normalization failed")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)

    result = public_research.AnthropicPublicResearchGateway("key", "model").search("prompt")

    assert len(result) == 1
    assert result[0].text == "The grounded narrative."


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
    retained, rejected = retain_public_claims((_claim(source_url="https://[fec0::1]/context-update"),))

    assert retained == ()
    assert rejected == {"claim-1": "public source URL is required"}
