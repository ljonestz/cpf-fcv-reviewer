"""Regression tests for the web_search allowed-domains 400 failure.

Root cause (confirmed against the live API, request_id req_011Cen5rjLbvogiirH5nzooS):
the web_search request sent ``allowed_domains`` containing news wires whose sites
block Anthropic's crawler (reuters.com, apnews.com, bbc.com, bbc.co.uk). Anthropic
rejects the ENTIRE request with HTTP 400 ("The following domains are not accessible
to our user agent: [...]"), so live-news research failed on every run.

Fix: exclude crawler-blocked wires from the domains actually sent, and self-heal by
dropping any domain Anthropic rejects and retrying once (future-proofing).
"""
from __future__ import annotations

from types import SimpleNamespace

from cpf_fcv_reviewer import public_research


def _gateway(monkeypatch, fake_client):
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    return public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=30.0
    )


class _DomainsBlockedError(Exception):
    """Mimics anthropic.BadRequestError for inaccessible allowed_domains."""

    def __init__(self, domains: list[str]) -> None:
        listed = ", ".join(f"'{d}'" for d in domains)
        message = (
            "The following domains are not accessible to our user agent: "
            f"[{listed}]. Read more: https://support.anthropic.com/..."
        )
        self.status_code = 400
        self.body = {
            "type": "error",
            "error": {"type": "invalid_request_error", "message": message},
        }
        super().__init__(f"Error code: 400 - {self.body}")


def test_search_allowed_domains_excludes_crawler_blocked_wires():
    sent = set(public_research.SEARCH_ALLOWED_DOMAINS)
    # The wires that block Anthropic's crawler must NOT be sent (they cause the 400).
    assert public_research.CRAWLER_BLOCKED_SEARCH_DOMAINS.isdisjoint(sent)
    for wire in ("reuters.com", "apnews.com", "bbc.com", "bbc.co.uk"):
        assert wire not in sent
    # Reachable trusted sources are still sent.
    assert {"crisisgroup.org", "rescue.org", "acleddata.com", "reliefweb.int",
            "un.org", "unhcr.org", "issafrica.org"} <= sent


def test_blocked_wires_remain_approved_publishers():
    # The wires are still valid publishers, so results reaching us via the
    # app-fetched curated fallback (or any crawlable mirror) are accepted.
    assert public_research._publisher_for_source_url("https://www.reuters.com/x") == "Reuters"
    assert public_research._publisher_for_source_url("https://www.bbc.com/news/x") == "BBC"
    assert public_research._publisher_for_source_url("https://apnews.com/article/x") == (
        "Associated Press"
    )


def test_inaccessible_search_domains_parsed_from_error_body():
    exc = _DomainsBlockedError(["reuters.com", "bbc.com"])
    assert public_research._inaccessible_search_domains(exc) == frozenset(
        {"reuters.com", "bbc.com"}
    )


def test_inaccessible_search_domains_empty_for_unrelated_error():
    assert public_research._inaccessible_search_domains(ValueError("nope")) == frozenset()


def test_web_search_drops_rejected_domain_and_retries(monkeypatch):
    """If Anthropic rejects a currently-allowed domain, drop it and retry once."""
    rejected = public_research.SEARCH_ALLOWED_DOMAINS[0]
    sentinel = SimpleNamespace(content=(), stop_reason="end_turn")
    calls: list[dict] = []

    class FakeBetaMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise _DomainsBlockedError([rejected])
            return sentinel

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=SimpleNamespace()
    )
    gateway = _gateway(monkeypatch, fake_client)

    result = gateway._create_web_search_response(
        [{"role": "user", "content": "country: Guinea"}],
        deadline=gateway._monotonic() + 30,
    )

    assert result is sentinel
    assert len(calls) == 2
    assert rejected in calls[0]["tools"][0]["allowed_domains"]
    assert rejected not in calls[1]["tools"][0]["allowed_domains"]


def test_web_search_does_not_retry_on_unrelated_400(monkeypatch):
    """A 400 with no inaccessible-domain info must surface, not loop."""
    calls: list[dict] = []

    class Unrelated400(Exception):
        status_code = 400
        body = {"error": {"message": "max_tokens too large"}}

    class FakeBetaMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            raise Unrelated400()

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=SimpleNamespace()
    )
    gateway = _gateway(monkeypatch, fake_client)

    raised = False
    try:
        gateway._create_web_search_response(
            [{"role": "user", "content": "x"}],
            deadline=gateway._monotonic() + 30,
        )
    except Unrelated400:
        raised = True
    assert raised
    assert len(calls) == 1  # no retry
