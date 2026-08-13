from datetime import date

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
)


def claim(
    claim_id: str,
    *,
    publisher: str = "World Bank",
    context_kind: str = "structural_dynamic",
    source_date: date = date(2026, 7, 1),
    source_url: str | None = None,
) -> CurrentContextClaim:
    return CurrentContextClaim(
        claim_id=claim_id,
        text=f"Claim {claim_id} establishes a bounded context finding.",
        publisher=publisher,
        source_title=f"Source {claim_id}",
        source_url=source_url or f"https://example.org/{claim_id}",
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
    gateway = ScriptedGateway((RuntimeError("authentication failed"), sufficient_claims()))

    with pytest.raises(ResearchConfigurationError):
        controller(gateway).run(holistic_request(), lambda *_: None)

    assert gateway.calls == 1


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


def test_duplicate_url_and_claim_id_are_not_accumulated():
    first = claim("same", source_url="https://example.org/same")
    second = claim("same", publisher="United Nations", source_url="https://example.org/other")
    third = claim("other", publisher="United Nations", source_url="https://example.org/same")
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
