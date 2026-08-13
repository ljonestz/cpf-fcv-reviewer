import pytest

from cpf_fcv_reviewer.config import build_config


def test_research_settings_have_bounded_defaults():
    config = build_config({"TESTING": True})

    assert config["RESEARCH_MAX_ATTEMPTS"] == 3
    assert config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] == 90.0
    assert config["RESEARCH_TOTAL_BUDGET_SECONDS"] == 300.0
    assert config["RESEARCH_MINIMUM_CLAIMS"] == 4
    assert config["RESEARCH_MINIMUM_PUBLISHERS"] == 2
    assert config["RESEARCH_RETRY_BACKOFF_SECONDS"] == 1.0


def test_research_settings_accept_overrides(monkeypatch):
    monkeypatch.setenv("RESEARCH_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("RESEARCH_TOTAL_BUDGET_SECONDS", "60")

    config = build_config({"TESTING": True})

    assert config["RESEARCH_MAX_ATTEMPTS"] == 5
    assert config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] == 12.5
    assert config["RESEARCH_TOTAL_BUDGET_SECONDS"] == 60.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"RESEARCH_MAX_ATTEMPTS": 0},
        {"RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 0},
        {"RESEARCH_TOTAL_BUDGET_SECONDS": 0},
        {"RESEARCH_MINIMUM_CLAIMS": 0},
        {"RESEARCH_MINIMUM_PUBLISHERS": 0},
        {"RESEARCH_RETRY_BACKOFF_SECONDS": -1},
        {"RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 301, "RESEARCH_TOTAL_BUDGET_SECONDS": 300},
    ],
)
def test_research_settings_reject_nonpositive_or_inconsistent_values(overrides):
    with pytest.raises(ValueError):
        build_config({"TESTING": True, **overrides})
