from math import inf, nan

import pytest

from cpf_fcv_reviewer.config import build_config


def test_research_settings_have_bounded_defaults():
    config = build_config({"TESTING": True})

    assert config["RESEARCH_MAX_ATTEMPTS"] == 1
    assert config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] == 90.0
    assert config["RESEARCH_TOTAL_BUDGET_SECONDS"] == 300.0
    assert config["RESEARCH_MINIMUM_CLAIMS"] == 4
    assert config["RESEARCH_MINIMUM_PUBLISHERS"] == 2
    assert config["RESEARCH_RETRY_BACKOFF_SECONDS"] == 1.0
    assert config["RESEARCH_RECOVERY_TIMEOUT_SECONDS"] == 8.0
    assert config["RESEARCH_RECOVERY_MAX_BYTES"] == 500000
    assert config["RELIEFWEB_APP_NAME"] == "cpf-fcv-reviewer"


def test_research_settings_accept_overrides(monkeypatch):
    monkeypatch.setenv("RESEARCH_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("RESEARCH_TOTAL_BUDGET_SECONDS", "60")

    config = build_config({"TESTING": True})

    assert config["RESEARCH_MAX_ATTEMPTS"] == 5
    assert config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] == 12.5
    assert config["RESEARCH_TOTAL_BUDGET_SECONDS"] == 60.0


def test_recovery_settings_accept_environment_values_and_trim_app_name(monkeypatch):
    monkeypatch.setenv("RESEARCH_RECOVERY_TIMEOUT_SECONDS", "4.5")
    monkeypatch.setenv("RESEARCH_RECOVERY_MAX_BYTES", "10000")
    monkeypatch.setenv("RELIEFWEB_APP_NAME", "  approved-app  ")

    config = build_config({"TESTING": True})

    assert config["RESEARCH_RECOVERY_TIMEOUT_SECONDS"] == 4.5
    assert config["RESEARCH_RECOVERY_MAX_BYTES"] == 10000
    assert config["RELIEFWEB_APP_NAME"] == "approved-app"


@pytest.mark.parametrize("value", ["\n", " \n ", "\u0085"])
def test_reliefweb_app_name_rejects_raw_environment_control_characters(monkeypatch, value):
    monkeypatch.setenv("RELIEFWEB_APP_NAME", value)

    with pytest.raises(ValueError):
        build_config({"TESTING": True})


@pytest.mark.parametrize("value", ["\n", " \n ", "\u0085"])
def test_reliefweb_app_name_rejects_raw_override_control_characters(value):
    with pytest.raises(ValueError):
        build_config({"TESTING": True, "RELIEFWEB_APP_NAME": value})


def test_reliefweb_app_name_strips_ordinary_whitespace_to_empty_value():
    config = build_config({"TESTING": True, "RELIEFWEB_APP_NAME": "   "})

    assert config["RELIEFWEB_APP_NAME"] == ""


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


@pytest.mark.parametrize(
    "name, value",
    [
        ("RESEARCH_MAX_ATTEMPTS", True),
        ("RESEARCH_MINIMUM_CLAIMS", 1.0),
        ("RESEARCH_MINIMUM_PUBLISHERS", "2"),
        ("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", nan),
        ("RESEARCH_TOTAL_BUDGET_SECONDS", inf),
        ("RESEARCH_RETRY_BACKOFF_SECONDS", True),
    ],
)
def test_research_settings_reject_wrong_types_or_nonfinite_values(name, value):
    with pytest.raises(ValueError):
        build_config({"TESTING": True, name: value})


@pytest.mark.parametrize(
    "name, value",
    [
        ("RESEARCH_RECOVERY_TIMEOUT_SECONDS", True),
        ("RESEARCH_RECOVERY_TIMEOUT_SECONDS", 0),
        ("RESEARCH_RECOVERY_TIMEOUT_SECONDS", nan),
        ("RESEARCH_RECOVERY_TIMEOUT_SECONDS", inf),
        ("RESEARCH_RECOVERY_MAX_BYTES", True),
        ("RESEARCH_RECOVERY_MAX_BYTES", 9999),
        ("RESEARCH_RECOVERY_MAX_BYTES", 2_000_001),
        ("RESEARCH_RECOVERY_MAX_BYTES", 10_000.0),
        ("RESEARCH_RECOVERY_MAX_BYTES", "500000"),
        ("RELIEFWEB_APP_NAME", "bad\nname"),
    ],
)
def test_recovery_settings_reject_invalid_values(name, value):
    with pytest.raises(ValueError):
        build_config({"TESTING": True, name: value})


def test_volatile_prototype_mode_is_explicit_and_boolean(monkeypatch):
    monkeypatch.setenv("ALLOW_VOLATILE_PROTOTYPE", "true")

    config = build_config(
        {"TESTING": True},
        use_environment=True,
    )

    assert config["ALLOW_VOLATILE_PROTOTYPE"] is True

    with pytest.raises(ValueError, match="ALLOW_VOLATILE_PROTOTYPE"):
        build_config({"TESTING": True, "ALLOW_VOLATILE_PROTOTYPE": "yes"})
