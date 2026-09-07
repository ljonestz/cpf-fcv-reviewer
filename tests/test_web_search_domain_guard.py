"""Broad search discovery preserves source acceptance and call limits."""
from __future__ import annotations

from types import SimpleNamespace

from cpf_fcv_reviewer import public_research


def _gateway(monkeypatch, fake_client):
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    return public_research.AnthropicPublicResearchGateway(
        "test-key", "test-model", timeout_seconds=30.0
    )


def test_blocked_wires_remain_approved_publishers():
    # The wires are still valid publishers, so results reaching us via the
    # app-fetched curated fallback (or any crawlable mirror) are accepted.
    assert public_research._publisher_for_source_url("https://www.reuters.com/x") == "Reuters"
    assert public_research._publisher_for_source_url("https://www.bbc.com/news/x") == "BBC"
    assert public_research._publisher_for_source_url("https://apnews.com/article/x") == (
        "Associated Press"
    )


def test_web_search_discovers_broadly_without_extra_calls(monkeypatch):
    calls = []
    sentinel = SimpleNamespace(content=(), stop_reason="end_turn")

    class FakeBetaMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return sentinel

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=SimpleNamespace()
    )
    gateway = _gateway(monkeypatch, fake_client)
    result = gateway._create_web_search_response(
        [{"role": "user", "content": "country: Kenya"}],
        deadline=gateway._monotonic() + 30,
    )
    assert result is sentinel
    assert len(calls) == 1
    assert "allowed_domains" not in calls[0]["tools"][0]
    assert calls[0]["tools"][0]["max_uses"] == 2


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
