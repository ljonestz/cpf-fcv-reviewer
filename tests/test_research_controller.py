from datetime import date, datetime
from math import inf, nan

import pytest

from cpf_fcv_reviewer.public_research import CurrentContextClaim
from cpf_fcv_reviewer.research_controller import (
    InsufficientResearch,
    MalformedResearch,
    ResearchConfigurationError,
    ResearchController,
    ResearchMode,
    ResearchProviderFailure,
    ResearchRequest,
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
    assert result.sufficient is True
    assert events[-1][0] == "research_sufficient"


def test_controller_uses_targeted_fallback_for_thin_result():
    gateway = ScriptedGateway(((claim("c1"),), sufficient_claims()))

    result = controller(gateway).run(rra_request(), lambda *_: None)

    assert gateway.calls == 2
    assert "missing coverage" in gateway.prompts[1]
    assert result.sufficient is True


def test_controller_blocks_after_all_attempts_are_insufficient():
    gateway = ScriptedGateway(((claim("c1"),),) * 3)

    with pytest.raises(InsufficientResearch):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 3


def test_transient_provider_error_retries_then_succeeds():
    gateway = ScriptedGateway((ConnectionError("temporary"), sufficient_claims()))

    result = controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 2
    assert result.sufficient is True


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


def test_sufficiency_requires_publisher_diversity_structural_current_and_recent():
    claims = (
        claim("c1", source_date=date(2025, 1, 1)),
        claim("c2", source_date=date(2025, 2, 1)),
        claim("c3", context_kind="current_development", source_date=date(2025, 3, 1)),
        claim("c4", source_date=date(2025, 4, 1)),
    )

    with pytest.raises(InsufficientResearch):
        controller(gateway=ScriptedGateway((claims,)), max_attempts=1).run(
            holistic_request(), lambda *_: None
        )


def test_rra_recent_window_and_prompt_are_explicit():
    gateway = ScriptedGateway(((claim("c1"),),))
    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=1).run(rra_request(), lambda *_: None)

    assert "research_mode: rra_update" in gateway.prompts[0]
    assert "2022-03-01" in gateway.prompts[0]
    assert "2026-08-01" in gateway.prompts[0]


def test_holistic_recent_window_is_bounded_to_24_months():
    gateway = ScriptedGateway(((claim("c1"),),))
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
    first = claim("same", source_url="https://www.worldbank.org/same")
    second = claim("same", publisher="United Nations", source_url="https://www.un.org/other")
    third = claim("other", source_url="https://www.worldbank.org/same")
    gateway = ScriptedGateway(((first,), (second, third)))

    events = []
    with pytest.raises(InsufficientResearch):
        controller(gateway).run(holistic_request(), lambda *event: events.append(event))

    assert any(data["rejected_count"] > 0 for kind, data in events if kind == "research_attempt")


def test_events_are_count_only():
    events = []
    gateway = ScriptedGateway(((claim("c1"),),))
    with pytest.raises(InsufficientResearch):
        controller(gateway, max_attempts=1).run(
            rra_request(), lambda kind, data: events.append((kind, data))
        )

    forbidden = ("Benin", "Risk", "Claim", "https://", "prompt")
    for _, data in events:
        assert not any(value in str(data) for value in forbidden)


def test_all_source_rejections_raise_source_rejected():
    rejected = claim("licensed") .model_copy(update={"licensed_data_required": True})
    with pytest.raises(ResearchSourceRejected):
        controller(ScriptedGateway(((rejected,),)), max_attempts=1).run(
            holistic_request(), lambda *_: None
        )


def test_total_budget_stops_before_next_attempt():
    now = [0.0]

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    gateway = ScriptedGateway(((claim("c1"),), sufficient_claims()))
    with pytest.raises(ResearchTimeout):
        controller(
            gateway,
            total_budget_seconds=1.0,
            retry_backoff_seconds=2.0,
            monotonic=clock,
            sleep=sleep,
        ).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1


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
