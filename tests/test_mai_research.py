"""mAI public search discovers URLs; only fetched page text can support quotes."""
import json
from datetime import date
from unittest.mock import Mock

import httpx
import pytest

from cpf_fcv_reviewer.mai_research import MaiGoogleResearchGateway, fetch_public_article
from cpf_fcv_reviewer.public_research import CurrentContextClaim, ResearchClaimBatch


QUOTE = "Guinea's mining communities face exclusion from local services."
URL = "https://www.hrw.org/news/2026/09/12/guinea-mining"
HTML = ("<html><head><title>Guinea mining</title>"
        '<meta property="article:published_time" content="2026-09-12T10:00:00Z">'
        "</head><body><h1>Guinea mining</h1><p>" + QUOTE + "</p>"
        "<script>PRIVATE_SCRIPT</script></body></html>")


def claim(**changes):
    fields = dict(claim_id="c1", text=QUOTE, supporting_quote=QUOTE,
                  publisher="Invented publisher", source_title="Invented title",
                  source_url=URL, source_date=date(2026, 10, 1), source_type="report",
                  relevance="Distributional exclusion affects conflict sensitivity.",
                  context_kind="structural_dynamic", relationship="establishes",
                  licensed_data_required=False, fcv_relevant=True, source_quality="analysis")
    return CurrentContextClaim(**(fields | changes))


def model_reply(stop="STOP", chunks=None):
    return {"candidates": [{"finishReason": stop, "groundingMetadata": {
        "groundingChunks": chunks if chunks is not None else [{"web": {"uri": URL}}],
        "groundingSupports": [{"segment": {"text": "Synthesis is not an exact quote"},
                               "groundingChunkIndices": [0]}],
        "searchEntryPoint": {"renderedContent": '<div>Search suggestions</div>'},
    }}]}


def gateway(reply=None, claims=None, handler=None):
    model = Mock()
    model.team_name = "test-team"
    model._token.return_value = "synthetic-token"
    captured = []

    def api(request):
        captured.append(request)
        return httpx.Response(200, json=reply or model_reply())

    model._client = httpx.Client(transport=httpx.MockTransport(api))
    model._complete.return_value = (ResearchClaimBatch(claims=claims).model_dump_json()
        if claims is not None else json.dumps({"observations": [{
            "passage_id": "s1p1", "relevance": "Distributional exclusion limits services.",
            "context_kind": "structural_dynamic", "fcv_relevant": True,
            "source_quality": "analysis"}]}))
    public = httpx.Client(transport=httpx.MockTransport(handler or (
        lambda r: httpx.Response(200, text=HTML, headers={"content-type": "text/html"}))))
    return MaiGoogleResearchGateway(model, public_client=public), model, captured


def test_search_uses_only_canonical_country_date_and_fixed_topics():
    research, model, requests = gateway()
    result = research.search("country: Guinea\nreview_date: 2026-10-04\nPRIVATE_CPF_TEXT")
    body = requests[0].content.decode()
    assert "PRIVATE_CPF_TEXT" not in body
    assert "Guinea" in body and "2026-10-04" in body
    assert json.loads(body)["tools"] == [{"googleSearch": {}}]
    assert requests[0].url.host == "azapimdev.worldbank.org"
    assert requests[0].headers["Authorization"] == "Bearer synthetic-token"
    assert result[0].text == QUOTE
    assert result[0].source_date == date(2026, 9, 12)
    assert result[0].publisher == "Human Rights Watch"
    assert result[0].verification == "verified"
    assert research.last_search_suggestions == '<div>Search suggestions</div>'


@pytest.mark.parametrize("field", ["country: PRIVATE_NOT_A_COUNTRY", "country: Guinea\ncountry: Mali"])
def test_unknown_or_multiple_countries_fail_before_network(field):
    research, model, requests = gateway()
    with pytest.raises(ValueError):
        research.search(field + "\nreview_date: 2026-10-04")
    assert not requests


@pytest.mark.parametrize("stop", ["MAX_TOKENS", "SAFETY", None])
def test_incomplete_grounding_cannot_be_normalized(stop):
    research, model, _ = gateway(model_reply(stop))
    with pytest.raises(ValueError):
        research.search("country: Guinea\nreview_date: 2026-10-04")
    model._complete.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"supporting_quote": "Synthesis is not an exact quote"},
    {"source_url": "https://www.hrw.org/invented"},
    {"supporting_quote": "The government guarantees peace and jobs."},
])
def test_generated_or_wrong_source_quotes_are_rejected(changes):
    research, _, _ = gateway(claims=(claim(**changes),))
    with pytest.raises(ValueError):
        research.search("country: Guinea\nreview_date: 2026-10-04")


def test_public_fetch_never_receives_desktop_credentials_and_excludes_scripts():
    requests = []

    def public(request):
        requests.append(request)
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})

    research, model, _ = gateway(handler=public)
    research.search("country: Guinea\nreview_date: 2026-10-04")
    assert all("authorization" not in r.headers for r in requests)
    serialized = str(model._complete.call_args)
    assert "PRIVATE_SCRIPT" not in serialized


@pytest.mark.parametrize("url", ["http://www.hrw.org/a", "https://127.0.0.1/a",
    "https://www.hrw.org.evil.example.com/a", "https://user:pass@www.hrw.org/a",
    "https://api.acleddata.com/a", "https://www.hrw.org:8443/a"])
def test_unapproved_fetch_urls_are_not_requested(url):
    handler = Mock(side_effect=AssertionError("Must reject before HTTP"))
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_public_article(url, client) is None
    handler.assert_not_called()


def test_redirect_target_is_revalidated_before_fetch():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "https://127.0.0.1/private"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_public_article(URL, client) is None
    assert len(calls) == 1


def test_google_redirect_resolves_to_original_public_page():
    redirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/test"

    def handler(request):
        if request.url.host == "vertexaisearch.cloud.google.com":
            return httpx.Response(302, headers={"location": URL})
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})

    article = fetch_public_article(redirect, httpx.Client(transport=httpx.MockTransport(handler)))
    assert article["url"] == URL
    assert article["published_at"] == "2026-09-12"


@pytest.mark.parametrize("headers,body", [
    ({"content-type": "application/pdf"}, b"not-html"),
    ({"content-type": "text/html", "content-length": "9000000"}, b"big"),
    ({"content-type": "text/html"}, b"x" * 600001),
], ids=["pdf", "declared_size", "streamed_size"])
def test_non_html_and_oversized_pages_are_rejected(headers, body):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, headers=headers)))
    assert fetch_public_article(URL, client) is None


def test_mAI_search_configuration_requires_no_separate_key_and_is_local_only():
    from cpf_fcv_reviewer.config import build_config
    config = build_config({"APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": "test", "RESEARCH_PROVIDER": "mai_google"}, use_environment=False)
    assert config["ANTHROPIC_API_KEY"] == ""
    assert config["RESEARCH_MODEL_ID"] == "gemini-3.8-flash"
    with pytest.raises(ValueError):
        build_config({"TESTING": True, "MODEL_PROVIDER": "anthropic",
                      "RESEARCH_PROVIDER": "mai_google"}, use_environment=False)


def test_runtime_uses_same_mai_gateway_for_search_and_normalization(monkeypatch):
    from pathlib import Path
    from cpf_fcv_reviewer import runtime
    from cpf_fcv_reviewer.config import build_config
    registry = Path(__file__).resolve().parents[1] / "registry_bundles" / (
        "cpf_fcv_reviewer_public_guardrails_v1.1.0.json")
    forbidden = Mock(side_effect=AssertionError("No direct Anthropic research"))
    monkeypatch.setattr(runtime, "AnthropicPublicResearchGateway", forbidden)
    config = build_config({"APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": "test", "RESEARCH_PROVIDER": "mai_google",
        "REGISTRY_BUNDLE_PATH": str(registry),
        "REGISTRY_BUNDLE_SHA256": registry.with_suffix(".sha256").read_text().split()[0]},
        use_environment=False)
    mai = Mock()
    services = runtime.build_runtime_services(config, model_gateway=mai, follow_on_gateway=mai)
    assert isinstance(services["research_controller"].gateway, MaiGoogleResearchGateway)
    assert services["research_controller"].gateway.mai is mai
    forbidden.assert_not_called()


def test_intake_explains_mai_search_without_separate_api_key():
    from cpf_fcv_reviewer.app import create_app
    app = create_app({"TESTING": True, "APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": "test", "RESEARCH_PROVIDER": "mai_google", "START_BACKGROUND_RUNS": False},
        services={}, use_environment=False)
    page = app.test_client().get("/").get_data(as_text=True)
    assert "Google Search through mAI Factory" in page
    assert "country and review date" in page
    assert "Institutional-source research only" not in page


def test_passage_selection_copies_original_text_without_model_transcription():
    research, model, _ = gateway()
    model._complete.return_value = json.dumps({"observations": [{
        "passage_id": "s1p1", "relevance": "Exclusion limits equitable service delivery.",
        "context_kind": "structural_dynamic", "source_quality": "analysis",
        "fcv_relevant": True,
    }]})
    claims = research.search("country: Guinea\nreview_date: 2026-10-04")
    assert claims[0].supporting_quote == QUOTE
    assert claims[0].text == QUOTE


def test_world_bank_url_and_article_metadata_date_conflict_remains_undated():
    url = "https://www.worldbank.org/en/news/press-release/2026/06/23/guinea"
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
        200, text=HTML, headers={"content-type": "text/html"})))
    article = fetch_public_article(url, client)
    assert article["published_at"] is None
    assert article["publication_date_basis"] == "conflicting"


@pytest.mark.parametrize("changes", [{"passage_id": "invented"},
    {"fcv_relevant": False}, {"source_quality": "unsuitable"}])
def test_passage_selection_keeps_source_quality_and_ownership_gates(changes):
    research, model, _ = gateway()
    reply = json.loads(model._complete.return_value)
    reply["observations"][0].update(changes)
    model._complete.return_value = json.dumps(reply)
    assert research.search("country: Guinea\nreview_date: 2026-10-04") == ()


def test_non_country_passages_are_filtered_before_selection():
    foreign = "Mali's rural communities face a severe shortage of basic services."
    html = HTML.replace("</body>", "<p>" + foreign + "</p></body>")
    research, model, _ = gateway(handler=lambda r: httpx.Response(
        200, text=html, headers={"content-type": "text/html"}))
    research.search("country: Guinea\nreview_date: 2026-10-04")
    assert foreign not in model._complete.call_args.kwargs["messages"][0]["content"]


def test_original_iss_analysis_can_be_fetched_with_verified_publisher():
    url = "https://issafrica.org/iss-today/guinea-analysis"
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
        200, text=HTML, headers={"content-type": "text/html"})))
    article = fetch_public_article(url, client)
    assert article is not None
    assert article["publisher"] == "ISS Africa"
    assert fetch_public_article(url.replace("issafrica.org", "issafrica.org.evil.example"), client) is None


def test_explicit_visible_publication_date_is_used_and_conflicts_are_not_hidden():
    url = "https://issafrica.org/iss-today/guinea-analysis"
    visible = "<title>Guinea</title><p>Published on 11 August 2026 in ISS Today</p><p>" + QUOTE + "</p>"
    def fetch(html):
        return fetch_public_article(url, httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, text=html, headers={"content-type": "text/html"}))))
    article = fetch(visible)
    assert article["published_at"] == "2026-08-11"
    assert article["publication_date_basis"] == "source_excerpt"
    conflicted = fetch('<meta property="article:published_time" content="2026-08-12">' + visible)
    assert conflicted["published_at"] is None
    assert conflicted["publication_date_basis"] == "conflicting"


def test_normalizer_can_consider_broader_sources_before_final_three_source_cap():
    urls = ["https://www.amnesty.org/guinea", "https://www.hrw.org/guinea",
            "https://issafrica.org/guinea", "https://www.worldbank.org/guinea"]
    research, model, _ = gateway(reply=model_reply(chunks=[{"web": {"uri": u}} for u in urls]))
    research.search("country: Guinea\nreview_date: 2026-10-04")
    supplied = json.loads(model._complete.call_args.kwargs["messages"][0]["content"])["sources"]
    assert {s["url"] for s in supplied} == set(urls)


def test_research_selection_requires_topic_breadth_and_qualified_relevance():
    research, model, _ = gateway()
    research.search("country: Guinea\nreview_date: 2026-10-04")
    prompt = model._complete.call_args.kwargs["system"]
    assert "Prefer an uncovered topic over a second observation on the same issue" in prompt
    assert "Do not add facts, statistics or dates absent from the selected passage" in prompt
    assert "Preserve forecasts, uncertainty and the source's time frame" in prompt
