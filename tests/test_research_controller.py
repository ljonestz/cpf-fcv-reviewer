import logging
from datetime import date, datetime
from math import inf, nan
from types import SimpleNamespace

import httpx
import pytest
from anthropic import APIConnectionError, APITimeoutError

from cpf_fcv_reviewer import public_research
from cpf_fcv_reviewer.contracts import CurrentEvidenceTier
from cpf_fcv_reviewer.public_research import CurrentContextClaim
from cpf_fcv_reviewer.research_controller import (
    InsufficientResearch,
    MalformedResearch,
    ResearchConfigurationError,
    ResearchController,
    ResearchMode,
    ResearchProviderFailure,
    ResearchRequest,
    ResearchResult,
    ResearchSourceRejected,
    ResearchTimeout,
    _normalize_source_url,
    _subtract_calendar_years,
)


def claim(
    claim_id: str,
    *,
    publisher: str = "World Bank",
    context_kind: str = "structural_dynamic",
    source_date: date = date(2026, 7, 1),
    source_url: str | None = None,
) -> CurrentContextClaim:
    if source_url is None:
        source_host = "www.un.org" if publisher == "United Nations" else "www.worldbank.org"
        source_url = f"https://{source_host}/{claim_id}"
    return CurrentContextClaim(
        claim_id=claim_id,
        text=f"Claim {claim_id} establishes a bounded context finding.",
        publisher=publisher,
        source_title=f"Source {claim_id}",
        source_url=source_url,
        source_date=source_date,
        source_type="public report",
        relevance="Relevant to the current-country research question.",
        context_kind=context_kind,
        relationship="establishes",
        licensed_data_required=False,
    )


def sufficient_claims(review_date: date = date(2026, 8, 1)) -> tuple[CurrentContextClaim, ...]:
    return (
        claim("s1", source_date=date(2025, 9, 1)),
        claim("s2", publisher="United Nations", source_date=date(2026, 7, 1)),
        claim("s3", context_kind="current_development", source_date=review_date),
        claim("s4", context_kind="resilience_factor", source_date=date(2025, 10, 1)),
    )


def holistic_request() -> ResearchRequest:
    return ResearchRequest("Benin", date(2026, 8, 1), ResearchMode.HOLISTIC)


def rra_request() -> ResearchRequest:
    return ResearchRequest(
        "Benin",
        date(2026, 8, 1),
        ResearchMode.RRA_UPDATE,
        diagnostic_title="Benin Risk and Resilience Assessment",
        diagnostic_date=date(2022, 3, 1),
        diagnostic_summary="The diagnostic identifies structural delivery constraints.",
    )


class ScriptedGateway:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []

    def search(self, prompt: str):
        self.prompts.append(prompt)
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(response, BaseException):
            raise response
        return response


class ScriptedRecoveryGateway:
    def __init__(self, response, *, on_search=None):
        self.response = response
        self.on_search = on_search
        self.calls = 0
        self.timeouts = []

    def search(self, request, *, timeout_seconds):
        self.calls += 1
        self.timeouts.append(timeout_seconds)
        if self.on_search is not None:
            self.on_search(timeout_seconds)
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def controller(gateway, **overrides):
    settings = {
        "max_attempts": 3,
        "minimum_claims": 4,
        "minimum_publishers": 2,
        "retry_backoff_seconds": 0,
        "sleep": lambda _: None,
    }
    settings.update(overrides)
    return ResearchController(gateway, **settings)


def test_controller_stops_after_first_sufficient_attempt():
    gateway = ScriptedGateway((sufficient_claims(),))
    events = []

    result = controller(gateway).run(holistic_request(), lambda *event: events.append(event))

    assert gateway.calls == 1
    assert result.tier is CurrentEvidenceTier.FULL
    assert events[-1][0] == "research_sufficient"


def test_full_evidence_returns_explicit_full_tier():
    result = controller(ScriptedGateway((sufficient_claims(),))).run(
        holistic_request(), lambda *_: None
    )

    assert result.tier is CurrentEvidenceTier.FULL
    assert result.limitation is None


@pytest.mark.parametrize("tier", [True, False, "full", 1, None])
def test_research_result_rejects_legacy_boolean_and_invalid_tiers(tier):
    with pytest.raises(ValueError, match="tier"):
        ResearchResult((), {}, 1, tier)


@pytest.mark.parametrize(
    ("tier", "limitation"),
    [
        (CurrentEvidenceTier.FULL, "Unexpected limitation"),
        (CurrentEvidenceTier.REDUCED, None),
        (CurrentEvidenceTier.REDUCED, ""),
        (CurrentEvidenceTier.REDUCED, "   \n\t"),
        (CurrentEvidenceTier.DOCUMENT_LED, None),
        (CurrentEvidenceTier.DOCUMENT_LED, 1),
    ],
)
def test_research_result_rejects_inconsistent_tier_and_limitation(tier, limitation):
    with pytest.raises(ValueError, match="limitation"):
        ResearchResult((), {}, 1, tier, limitation)


@pytest.mark.parametrize(
    "tier",
    [CurrentEvidenceTier.REDUCED, CurrentEvidenceTier.DOCUMENT_LED],
)
def test_research_result_accepts_nonblank_limitation_for_nonfull_tiers(tier):
    result = ResearchResult((), {}, 1, tier, "Current evidence is limited.")

    assert result.limitation == "Current evidence is limited."


def test_thin_recent_public_evidence_returns_reduced_tier_with_limitation():
    events = []
    result = controller(
        ScriptedGateway(((claim("one"),),)),
        max_attempts=1,
    ).run(holistic_request(), lambda *event: events.append(event))

    assert result.tier is CurrentEvidenceTier.REDUCED
    assert "one public source" in result.limitation
    reduced = [data for kind, data in events if kind == "research_reduced"]
    assert len(reduced) == 1
    assert set(reduced[0]) == {"missing_coverage"}


def test_primary_and_recovery_claims_merge_and_deduplicate():
    primary = sufficient_claims()[:1]
    recovery = ScriptedRecoveryGateway((sufficient_claims()[0],) + sufficient_claims()[1:])
    events = []

    result = controller(
        ScriptedGateway((primary,)),
        recovery_gateway=recovery,
        max_attempts=1,
    ).run(holistic_request(), lambda *event: events.append(event))

    assert recovery.calls == 1
    assert result.tier is CurrentEvidenceTier.FULL
    assert len(result.claims) == 4
    assert [data for kind, data in events if kind == "research_curated_recovery"] == [
        {"accepted_count": 4}
    ]


def test_recovery_failure_does_not_discard_usable_primary_evidence():
    result = controller(
        ScriptedGateway(((claim("primary"),),)),
        recovery_gateway=ScriptedRecoveryGateway(TimeoutError("temporary")),
        max_attempts=1,
    ).run(holistic_request(), lambda *_: None)

    assert result.tier is CurrentEvidenceTier.REDUCED
    assert result.claims[0].claim_id == "primary"


def test_recovery_is_bounded_and_late_claims_are_not_accepted():
    now = [0.0]
    primary = claim("primary")

    class DelayedPrimaryGateway:
        def search(self, _prompt):
            now[0] += 0.25
            return (primary,)

    def finish_after_deadline(timeout_seconds):
        now[0] += timeout_seconds + 0.01

    recovery = ScriptedRecoveryGateway(
        sufficient_claims(), on_search=finish_after_deadline
    )
    result = controller(
        DelayedPrimaryGateway(),
        recovery_gateway=recovery,
        max_attempts=1,
        total_budget_seconds=1.0,
        monotonic=lambda: now[0],
    ).run(holistic_request(), lambda *_: None)

    assert recovery.timeouts == [0.75]
    assert result.tier is CurrentEvidenceTier.REDUCED
    assert result.claims == (primary,)


def test_late_empty_recovery_raises_timeout_without_document_led_opt_in():
    now = [0.0]
    events = []

    def finish_after_deadline(timeout_seconds):
        now[0] += timeout_seconds + 0.01

    recovery = ScriptedRecoveryGateway((), on_search=finish_after_deadline)

    with pytest.raises(ResearchTimeout, match="budget"):
        controller(
            ScriptedGateway(((),)),
            recovery_gateway=recovery,
            max_attempts=1,
            total_budget_seconds=1.0,
            monotonic=lambda: now[0],
        ).run(
            holistic_request(),
            lambda kind, data: events.append((kind, data)),
        )

    assert recovery.calls == 1
    _assert_events_are_privacy_safe(events)


def test_late_empty_recovery_uses_explicit_document_led_fallback():
    now = [0.0]
    events = []

    def finish_after_deadline(timeout_seconds):
        now[0] += timeout_seconds + 0.01

    recovery = ScriptedRecoveryGateway((), on_search=finish_after_deadline)
    result = controller(
        ScriptedGateway(((),)),
        recovery_gateway=recovery,
        max_attempts=1,
        total_budget_seconds=1.0,
        monotonic=lambda: now[0],
    ).run(
        holistic_request(),
        lambda kind, data: events.append((kind, data)),
        allow_document_led=True,
    )

    assert result.tier is CurrentEvidenceTier.DOCUMENT_LED
    assert result.claims == ()
    assert result.limitation
    assert events[-1][0] == "research_document_led"
    _assert_events_are_privacy_safe(events)


def test_late_all_rejected_recovery_raises_timeout():
    now = [0.0]
    events = []
    rejected = claim("licensed").model_copy(update={"licensed_data_required": True})

    def finish_after_deadline(timeout_seconds):
        now[0] += timeout_seconds + 0.01

    recovery = ScriptedRecoveryGateway((rejected,), on_search=finish_after_deadline)

    with pytest.raises(ResearchTimeout, match="budget"):
        controller(
            ScriptedGateway(((),)),
            recovery_gateway=recovery,
            max_attempts=1,
            total_budget_seconds=1.0,
            monotonic=lambda: now[0],
        ).run(
            holistic_request(), lambda kind, data: events.append((kind, data))
        )

    assert recovery.calls == 1
    _assert_events_are_privacy_safe(events)


def test_primary_recent_evidence_precedes_late_recovery_timeout():
    now = [0.0]
    events = []
    primary = claim("primary-recent")

    def finish_after_deadline(timeout_seconds):
        now[0] += timeout_seconds + 0.01

    recovery = ScriptedRecoveryGateway((), on_search=finish_after_deadline)
    result = controller(
        ScriptedGateway(((primary,),)),
        recovery_gateway=recovery,
        max_attempts=1,
        total_budget_seconds=1.0,
        monotonic=lambda: now[0],
    ).run(holistic_request(), lambda kind, data: events.append((kind, data)))

    assert recovery.calls == 1
    assert result.tier is CurrentEvidenceTier.REDUCED
    assert result.claims == (primary,)
    _assert_events_are_privacy_safe(events)


def test_provider_failure_and_recovery_failure_preserve_primary_exception():
    with pytest.raises(ResearchTimeout):
        controller(
            ScriptedGateway((TimeoutError(),)),
            recovery_gateway=ScriptedRecoveryGateway(TimeoutError()),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)


def test_document_led_requires_explicit_opt_in_and_no_accepted_claims():
    recovery = ScriptedRecoveryGateway(())
    result = controller(
        ScriptedGateway((TimeoutError(),)),
        recovery_gateway=recovery,
        max_attempts=1,
    ).run(holistic_request(), lambda *_: None, allow_document_led=True)

    assert result.tier is CurrentEvidenceTier.DOCUMENT_LED
    assert result.claims == ()
    assert result.limitation

    with pytest.raises(ResearchTimeout):
        controller(
            ScriptedGateway((TimeoutError(),)),
            recovery_gateway=ScriptedRecoveryGateway(()),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)


def test_rejected_claims_cannot_enable_reduced_mode():
    rejected = claim("licensed").model_copy(update={"licensed_data_required": True})

    with pytest.raises(ResearchSourceRejected):
        controller(
            ScriptedGateway(((rejected,),)),
            recovery_gateway=ScriptedRecoveryGateway(()),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)


def test_recovery_configuration_error_is_not_isolated():
    with pytest.raises(ResearchConfigurationError):
        controller(
            ScriptedGateway(((claim("primary"),),)),
            recovery_gateway=ScriptedRecoveryGateway(ResearchConfigurationError()),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)


def test_recovery_programming_error_propagates_immediately():
    with pytest.raises(KeyError, match="missing"):
        controller(
            ScriptedGateway(((claim("primary"),),)),
            recovery_gateway=ScriptedRecoveryGateway(KeyError("missing")),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)


def test_terminal_route_log_is_stable_and_contains_no_research_content(caplog):
    with caplog.at_level(logging.INFO, logger="cpf_fcv_reviewer.research_controller"):
        result = controller(
            ScriptedGateway(((claim("private"),),)),
            max_attempts=1,
        ).run(holistic_request(), lambda *_: None)

    assert result.tier is CurrentEvidenceTier.REDUCED
    terminal = [
        record.getMessage()
        for record in caplog.records
        if "research_terminal" in record.getMessage()
    ]
    assert len(terminal) == 1
    assert "route=research_reduced" in terminal[0]
    assert "duration_seconds=" in terminal[0]
    assert "accepted_count=1" in terminal[0]
    assert not any(value in terminal[0] for value in ("Benin", "Claim", "https://"))


def test_injected_jitter_is_applied_and_sleep_does_not_exceed_budget():
    now = [0.0]
    sleeps = []

    def clock():
        return now[0]

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    with pytest.raises(ResearchTimeout):
        controller(
            ScriptedGateway(((), TimeoutError())),
            max_attempts=2,
            total_budget_seconds=1.0,
            retry_backoff_seconds=0.25,
            jitter=lambda delay: delay * 2,
            monotonic=clock,
            sleep=sleep,
        ).run(holistic_request(), lambda *_: None)

    assert sleeps == [0.5]


def test_jittered_backoff_is_capped_to_remaining_budget():
    now = [0.0]
    sleeps = []

    def clock():
        return now[0]

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    class DelayedGateway:
        def search(self, prompt):
            now[0] += 0.75
            return ()

    with pytest.raises(ResearchTimeout):
        controller(
            DelayedGateway(),
            max_attempts=2,
            total_budget_seconds=1.0,
            retry_backoff_seconds=2.0,
            jitter=lambda delay: delay,
            monotonic=clock,
            sleep=sleep,
        ).run(holistic_request(), lambda *_: None)

    assert sleeps == [0.25]


def test_controller_uses_targeted_fallback_for_thin_result():
    gateway = ScriptedGateway(((claim("c1"),), sufficient_claims()))

    result = controller(gateway).run(rra_request(), lambda *_: None)

    assert gateway.calls == 2
    assert "missing coverage" in gateway.prompts[1]
    assert result.tier is CurrentEvidenceTier.FULL


def test_controller_blocks_after_all_attempts_are_insufficient():
    gateway = ScriptedGateway(((claim("c1", source_date=date(2023, 1, 1)),),) * 3)

    with pytest.raises(InsufficientResearch):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 3


def test_transient_provider_error_retries_then_succeeds():
    gateway = ScriptedGateway((ConnectionError("temporary"), sufficient_claims()))

    result = controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 2
    assert result.tier is CurrentEvidenceTier.FULL


@pytest.mark.parametrize(
    ("provider_error", "expected"),
    [
        (
            APIConnectionError(
                request=httpx.Request(
                    "POST", "https://api.anthropic.com/v1/messages"
                )
            ),
            ResearchProviderFailure,
        ),
        (
            APITimeoutError(
                httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            ),
            ResearchTimeout,
        ),
    ],
)
def test_anthropic_transport_failures_are_retryable_and_classified(
    monkeypatch, provider_error, expected
):
    calls = 0

    class FakeBetaMessages:
        def create(self, **kwargs):
            nonlocal calls
            calls += 1
            raise provider_error

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()),
        messages=SimpleNamespace(),
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("key", "model")

    with pytest.raises(expected):
        controller(gateway, max_attempts=2).run(holistic_request(), lambda *_: None)

    assert calls == 2


def test_configuration_error_stops_immediately():
    class UnauthorizedError(RuntimeError):
        status_code = 401

    gateway = ScriptedGateway((UnauthorizedError("unrelated"), sufficient_claims()))

    with pytest.raises(ResearchConfigurationError):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1


def test_auth_like_message_without_status_retries_as_provider_failure():
    gateway = ScriptedGateway((RuntimeError("authentication failed"),) * 3)

    with pytest.raises(ResearchProviderFailure):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 3


def test_research_request_rejects_non_date_diagnostic_date():
    with pytest.raises(ValueError, match="diagnostic date"):
        ResearchRequest(
            "Benin",
            date(2026, 8, 1),
            ResearchMode.RRA_UPDATE,
            diagnostic_title="Benin RRA",
            diagnostic_date="2022-03-01",
        )


def test_research_request_rejects_datetime_review_date():
    with pytest.raises(ValueError, match="review date"):
        ResearchRequest(
            "Benin",
            datetime(2026, 8, 1),
            ResearchMode.HOLISTIC,
        )


def test_research_request_rejects_datetime_diagnostic_date():
    with pytest.raises(ValueError, match="diagnostic date"):
        ResearchRequest(
            "Benin",
            date(2026, 8, 1),
            ResearchMode.RRA_UPDATE,
            diagnostic_title="Benin RRA",
            diagnostic_date=datetime(2022, 3, 1),
        )


def test_timeout_retries_then_raises_terminal_timeout():
    gateway = ScriptedGateway((TimeoutError(), TimeoutError(), TimeoutError()))

    with pytest.raises(ResearchTimeout):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 3


def test_malformed_retries_then_raises_terminal_malformed():
    gateway = ScriptedGateway((ValueError("Public research response could not be parsed."),) * 3)

    with pytest.raises(MalformedResearch):
        controller(gateway).run(holistic_request(), lambda *_: None)


def test_other_provider_error_retries_then_raises_provider_failure():
    gateway = ScriptedGateway((OSError("unavailable"),) * 3)

    with pytest.raises(ResearchProviderFailure):
        controller(gateway).run(holistic_request(), lambda *_: None)


@pytest.mark.parametrize(
    "error",
    [KeyError("missing"), IndexError("bad index"), ZeroDivisionError("division")],
)
def test_programming_errors_propagate_immediately(error):
    gateway = ScriptedGateway((error, sufficient_claims()))

    with pytest.raises(type(error)):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1


def test_sufficiency_requires_publisher_diversity_structural_current_and_recent():
    claims = (
        claim("c1", source_date=date(2023, 1, 1)),
        claim("c2", source_date=date(2023, 2, 1)),
        claim("c3", context_kind="current_development", source_date=date(2023, 3, 1)),
        claim("c4", source_date=date(2023, 4, 1)),
    )

    with pytest.raises(InsufficientResearch):
        controller(gateway=ScriptedGateway((claims,)), max_attempts=1).run(
            holistic_request(), lambda *_: None
        )


def test_rra_recent_window_and_prompt_are_explicit():
    gateway = ScriptedGateway(((claim("c1", source_date=date(2022, 1, 1)),),))
    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=1).run(rra_request(), lambda *_: None)

    assert "research_mode: rra_update" in gateway.prompts[0]
    assert "2022-03-01" in gateway.prompts[0]
    assert "2026-08-01" in gateway.prompts[0]


def test_holistic_recent_window_is_bounded_to_24_months():
    gateway = ScriptedGateway(((claim("c1", source_date=date(2024, 7, 31)),),))
    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=1).run(holistic_request(), lambda *_: None)

    assert "24 months" in gateway.prompts[0]


@pytest.mark.parametrize(
    "source_url",
    [
        "HTTPS://EXAMPLE.ORG:443/source#section",
        "https://example.org/source/",
    ],
)
def test_equivalent_source_url_variants_normalize_identically(source_url):
    assert _normalize_source_url(source_url) == "https://example.org/source"


def test_distinct_source_path_and_query_do_not_normalize_identically():
    assert _normalize_source_url("https://example.org/source?a=1") != _normalize_source_url(
        "https://example.org/source?a=2"
    )
    assert _normalize_source_url("https://example.org/source/a") != _normalize_source_url(
        "https://example.org/source/b"
    )


def test_holistic_recency_uses_calendar_years_with_leap_day_fallback():
    review_date = date(2024, 2, 29)
    request = ResearchRequest("Benin", review_date, ResearchMode.HOLISTIC)

    assert _subtract_calendar_years(review_date, 2) == date(2022, 2, 28)
    assert ResearchController._is_recent(
        claim("boundary", source_date=date(2022, 2, 28)), request
    )
    assert not ResearchController._is_recent(
        claim("before", source_date=date(2022, 2, 27)), request
    )


def test_duplicate_url_and_claim_id_are_not_accumulated():
    first = claim(
        "same", source_date=date(2023, 1, 1), source_url="https://www.worldbank.org/same"
    )
    second = claim(
        "same",
        source_date=date(2023, 2, 1),
        publisher="United Nations",
        source_url="https://www.un.org/other",
    )
    third = claim(
        "other", source_date=date(2023, 3, 1), source_url="https://www.worldbank.org/same"
    )
    gateway = ScriptedGateway(((first,), (second, third)))

    events = []
    with pytest.raises(InsufficientResearch):
        controller(gateway).run(holistic_request(), lambda *event: events.append(event))

    assert any(data["rejected_count"] > 0 for kind, data in events if kind == "research_attempt")


def test_controller_deduplicates_canonicalized_gateway_source_urls(monkeypatch):
    source_url = "https://www.worldbank.org/same"

    class FakeBetaMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=(
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=(
                            SimpleNamespace(
                                type="web_search_result",
                                title="Same update",
                                url=source_url,
                                page_age="2020-04-30",
                            ),
                        ),
                    ),
                    SimpleNamespace(
                        type="text",
                        text="The same source supports this context.",
                        citations=(
                            SimpleNamespace(
                                type="web_search_result_location",
                                title="Same update",
                                url=source_url,
                                encrypted_index="0",
                                cited_text="Source excerpt.",
                            ),
                        ),
                    ),
                ),
                stop_reason="end_turn",
            )

    class FakeMessages:
        def parse(self, **kwargs):
            claims = (
                claim(
                    "first",
                    source_url="HTTPS://WWW.WORLDBANK.ORG:443/same/",
                ).model_copy(
                    update={
                        "source_title": "Same update",
                        "source_date": date(2020, 4, 30),
                    }
                ),
                claim(
                    "second",
                    source_url="https://www.worldbank.org/same",
                ).model_copy(
                    update={
                        "source_title": "Same update",
                        "source_date": date(2020, 4, 30),
                    }
                ),
            )
            return SimpleNamespace(
                parsed_output=public_research.ResearchClaimBatch(claims=claims)
            )

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=FakeBetaMessages()), messages=FakeMessages()
    )
    monkeypatch.setattr(public_research, "Anthropic", lambda **kwargs: fake_client)
    gateway = public_research.AnthropicPublicResearchGateway("key", "model")
    events = []

    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=2).run(
            holistic_request(), lambda *event: events.append(event)
        )

    assert any(data["rejected_count"] > 0 for kind, data in events if kind == "research_attempt")


def test_events_are_count_only():
    events = []
    gateway = ScriptedGateway(((claim("c1", source_date=date(2021, 1, 1)),),))
    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=1).run(
            rra_request(), lambda kind, data: events.append((kind, data))
        )

    forbidden = ("Benin", "Risk", "Claim", "https://", "prompt")
    for _, data in events:
        assert not any(value in str(data) for value in forbidden)


def _assert_events_are_privacy_safe(events):
    forbidden = ("Benin", "Risk", "Claim", "https://", "prompt", "licensed")
    for _, data in events:
        assert not any(value in str(data) for value in forbidden)


def test_all_source_rejections_raise_source_rejected():
    rejected = claim("licensed") .model_copy(update={"licensed_data_required": True})
    with pytest.raises(ResearchSourceRejected):
        controller(ScriptedGateway(((rejected,),)), max_attempts=1).run(
            holistic_request(), lambda *_: None
        )


def test_exact_budget_stops_calls_but_grades_accumulated_recent_evidence():
    now = [0.0]

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    gateway = ScriptedGateway(((claim("c1"),), sufficient_claims()))
    result = controller(
        gateway,
        total_budget_seconds=1.0,
        retry_backoff_seconds=2.0,
        monotonic=clock,
        sleep=sleep,
        jitter=lambda delay: delay,
    ).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1
    assert result.attempts == 1
    assert result.tier is CurrentEvidenceTier.REDUCED
    assert tuple(item.claim_id for item in result.claims) == ("c1",)


def test_budget_exhaustion_precedes_earlier_provider_failure_without_evidence():
    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    gateway = ScriptedGateway((ConnectionError("provider"), sufficient_claims()))

    with pytest.raises(ResearchTimeout, match="budget"):
        controller(
            gateway,
            max_attempts=2,
            total_budget_seconds=1.0,
            retry_backoff_seconds=2.0,
            monotonic=lambda: now[0],
            sleep=sleep,
            jitter=lambda delay: delay,
        ).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1


def test_recent_evidence_precedes_budget_and_earlier_provider_failure():
    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    gateway = ScriptedGateway((ConnectionError("provider"), (claim("recent"),)))
    result = controller(
        gateway,
        max_attempts=3,
        total_budget_seconds=1.0,
        retry_backoff_seconds=(0.0, 2.0),
        monotonic=lambda: now[0],
        sleep=sleep,
        jitter=lambda delay: delay,
    ).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 2
    assert result.attempts == 2
    assert result.tier is CurrentEvidenceTier.REDUCED


@pytest.mark.parametrize(
    "response, expected",
    [
        (ValueError("malformed"), MalformedResearch),
        (ConnectionError("provider"), ResearchProviderFailure),
    ],
)
def test_retryable_failure_precedes_source_rejection_on_exhaustion(response, expected):
    rejected = claim("licensed").model_copy(update={"licensed_data_required": True})
    gateway = ScriptedGateway((response, (rejected,)))

    with pytest.raises(expected):
        controller(gateway, max_attempts=2).run(holistic_request(), lambda *_: None)


def test_source_rejection_precedes_insufficient_only_without_prior_failure():
    rejected = claim("licensed").model_copy(update={"licensed_data_required": True})

    with pytest.raises(ResearchSourceRejected):
        controller(ScriptedGateway(((rejected,),)), max_attempts=1).run(
            holistic_request(), lambda *_: None
        )


@pytest.mark.parametrize("value", [True, False, 1.0, "3", 0, -1])
def test_controller_rejects_invalid_integer_settings(value):
    with pytest.raises(ValueError):
        controller(ScriptedGateway(()), max_attempts=value)


@pytest.mark.parametrize("value", [True, nan, inf, -inf, 0, -1, "3"])
def test_controller_rejects_invalid_budget_settings(value):
    with pytest.raises(ValueError):
        controller(ScriptedGateway(()), total_budget_seconds=value)


@pytest.mark.parametrize("value", [True, nan, inf, -inf, -1, "1"])
def test_controller_rejects_invalid_backoff_settings(value):
    with pytest.raises(ValueError):
        controller(ScriptedGateway(()), retry_backoff_seconds=value)
