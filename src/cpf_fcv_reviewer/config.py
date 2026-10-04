from __future__ import annotations

import os
from math import isfinite
from numbers import Real
from unicodedata import category


def _environment_bool(name: str, *, use_environment: bool = True) -> bool:
    if not use_environment:
        return False
    value = os.getenv(name)
    if value is None:
        return False
    normalized = value.strip().casefold()
    if normalized in {"false", "0", "no", "off"}:
        return False
    if normalized in {"true", "1", "yes", "on"}:
        return True
    raise ValueError(f"{name} environment value is invalid.")


def build_config(
    overrides: dict | None = None,
    *,
    use_environment: bool = True,
) -> dict:
    overrides = overrides or {}

    def environment(name: str, default: str) -> str:
        return os.getenv(name, default) if use_environment else default

    config = {
        "APP_RELEASE": environment("RENDER_GIT_COMMIT", "")
        or environment("APP_RELEASE", "dev"),
        "APP_ENV": environment("APP_ENV", "production"),
        "SMOKE_MODE": _environment_bool(
            "SMOKE_MODE",
            use_environment=use_environment,
        ),
        "ALLOW_VOLATILE_PROTOTYPE": _environment_bool(
            "ALLOW_VOLATILE_PROTOTYPE",
            use_environment=use_environment,
        ),
        "ANTHROPIC_API_KEY": environment("ANTHROPIC_API_KEY", ""),
        "MODEL_PROVIDER": environment("MODEL_PROVIDER", "anthropic"),
        "MAI_TEAM_NAME": environment("MAI_TEAM_NAME", ""),
        "ANTHROPIC_MODEL_ID": environment("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5"),
        "REGISTRY_BUNDLE_PATH": environment("REGISTRY_BUNDLE_PATH", ""),
        "REGISTRY_BUNDLE_SHA256": environment("REGISTRY_BUNDLE_SHA256", ""),
        "ALLOW_SYNTHETIC_REGISTRY": False,
        "TRUST_RENDER_PROXY": _environment_bool("TRUST_RENDER_PROXY", use_environment=use_environment),
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "RESEARCH_MAX_ATTEMPTS": int(environment("RESEARCH_MAX_ATTEMPTS", "1")),
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": float(
            environment("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "180")
        ),
        "RESEARCH_TOTAL_BUDGET_SECONDS": float(
            environment("RESEARCH_TOTAL_BUDGET_SECONDS", "300")
        ),
        "RESEARCH_MINIMUM_CLAIMS": int(environment("RESEARCH_MINIMUM_CLAIMS", "4")),
        "RESEARCH_MINIMUM_PUBLISHERS": int(
            environment("RESEARCH_MINIMUM_PUBLISHERS", "2")
        ),
        "RESEARCH_RETRY_BACKOFF_SECONDS": float(
            environment("RESEARCH_RETRY_BACKOFF_SECONDS", "1")
        ),
        "RESEARCH_RECOVERY_TIMEOUT_SECONDS": float(
            environment("RESEARCH_RECOVERY_TIMEOUT_SECONDS", "8.0")
        ),
        "RESEARCH_RECOVERY_MAX_BYTES": int(
            environment("RESEARCH_RECOVERY_MAX_BYTES", "500000")
        ),
        "RELIEFWEB_APP_NAME": environment("RELIEFWEB_APP_NAME", ""),
        "SESSION_TTL_SECONDS": (
            overrides["SESSION_TTL_SECONDS"]
            if "SESSION_TTL_SECONDS" in overrides
            else int(environment("SESSION_TTL_SECONDS", "86400"))
        ),
        "PERSISTENCE_PATH": environment("PERSISTENCE_PATH", ""),
        "WORKER_POLL_SECONDS": float(environment("WORKER_POLL_SECONDS", "1")),
        "EVENT_STREAM_MAX_SECONDS": float(
            environment("EVENT_STREAM_MAX_SECONDS", "90")
        ),
        "START_BACKGROUND_RUNS": True,
        "PUBLIC_LIMITS_ENABLED": not overrides.get("TESTING", False),
        "PUBLIC_REVIEW_DAILY_LIMIT": int(environment("PUBLIC_REVIEW_DAILY_LIMIT", "4")),
        "PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT": int(environment("PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT", "2")),
        "PUBLIC_ASSISTANT_DAILY_LIMIT": int(environment("PUBLIC_ASSISTANT_DAILY_LIMIT", "12")),
        "MAX_PENDING_ASSESSMENTS": int(environment("MAX_PENDING_ASSESSMENTS", "4")),
        "MAX_EVENT_STREAMS": int(environment("MAX_EVENT_STREAMS", "8")),
        "TESTING": False,
    }
    config.update(overrides or {})
    if not isinstance(config["APP_ENV"], str) or not config["APP_ENV"].strip():
        raise ValueError("APP_ENV must be a nonblank string.")
    config["APP_ENV"] = config["APP_ENV"].strip().casefold()
    for name in ("SMOKE_MODE", "ALLOW_VOLATILE_PROTOTYPE", "PUBLIC_LIMITS_ENABLED", "TRUST_RENDER_PROXY"):
        if type(config[name]) is not bool:
            raise ValueError(f"{name} must be a boolean.")
    if config["SMOKE_MODE"] and config["APP_ENV"] != "development":
        raise RuntimeError("SMOKE_MODE is development only.")
    for name in (
        "RESEARCH_MAX_ATTEMPTS",
        "RESEARCH_MINIMUM_CLAIMS",
        "RESEARCH_MINIMUM_PUBLISHERS",
        "SESSION_TTL_SECONDS",
        "PUBLIC_REVIEW_DAILY_LIMIT",
        "PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT",
        "PUBLIC_ASSISTANT_DAILY_LIMIT",
        "MAX_PENDING_ASSESSMENTS",
        "MAX_EVENT_STREAMS",
    ):
        if type(config[name]) is not int or config[name] <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    for name, positive in (
        ("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", True),
        ("RESEARCH_TOTAL_BUDGET_SECONDS", True),
        ("RESEARCH_RETRY_BACKOFF_SECONDS", False),
        ("RESEARCH_RECOVERY_TIMEOUT_SECONDS", True),
        ("WORKER_POLL_SECONDS", True),
        ("EVENT_STREAM_MAX_SECONDS", True),
    ):
        value = config[name]
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number.")
        if value < 0 or (positive and value <= 0):
            raise ValueError(f"{name} has an invalid bound.")
    if config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] > config["RESEARCH_TOTAL_BUDGET_SECONDS"]:
        raise ValueError("Research attempt timeout cannot exceed total budget.")
    if type(config["RESEARCH_RECOVERY_MAX_BYTES"]) is not int or not (
        10_000 <= config["RESEARCH_RECOVERY_MAX_BYTES"] <= 2_000_000
    ):
        raise ValueError("RESEARCH_RECOVERY_MAX_BYTES must be an integer from 10000 to 2000000.")
    if config["RELIEFWEB_APP_NAME"] is None:
        config["RELIEFWEB_APP_NAME"] = ""
    elif not isinstance(config["RELIEFWEB_APP_NAME"], str):
        raise ValueError("RELIEFWEB_APP_NAME must be a string.")
    elif any(
        category(character) == "Cc" for character in config["RELIEFWEB_APP_NAME"]
    ):
        raise ValueError("RELIEFWEB_APP_NAME cannot contain control characters.")
    config["RELIEFWEB_APP_NAME"] = config["RELIEFWEB_APP_NAME"].strip()
    config["ANTHROPIC_API_KEY"] = config["ANTHROPIC_API_KEY"].strip()
    if config["MODEL_PROVIDER"] not in {"anthropic", "mai_desktop"}:
        raise ValueError("MODEL_PROVIDER is invalid.")
    config.setdefault("RESEARCH_PROVIDER", environment(
        "RESEARCH_PROVIDER", "institutional" if config["MODEL_PROVIDER"] == "mai_desktop"
        else "anthropic",
    ))
    if config["RESEARCH_PROVIDER"] not in ("anthropic", "institutional", "mai_google"):
        raise ValueError("RESEARCH_PROVIDER is invalid.")
    if config["RESEARCH_PROVIDER"] == "institutional" and config["MODEL_PROVIDER"] != "mai_desktop":
        raise ValueError("Institutional RESEARCH_PROVIDER requires mAI Desktop mode.")
    if config["RESEARCH_PROVIDER"] == "mai_google" and config["MODEL_PROVIDER"] != "mai_desktop":
        raise ValueError("mAI Google research requires mAI Desktop mode.")
    # Resolve the research model before Desktop sets application-owned review metadata.
    config.setdefault("RESEARCH_MODEL_ID", environment("RESEARCH_MODEL_ID", config["ANTHROPIC_MODEL_ID"]))
    if not isinstance(config["RESEARCH_MODEL_ID"], str) or not config["RESEARCH_MODEL_ID"].strip():
        raise ValueError("RESEARCH_MODEL_ID must be a nonblank string.")
    config["RESEARCH_MODEL_ID"] = config["RESEARCH_MODEL_ID"].strip()
    if config["RESEARCH_PROVIDER"] == "mai_google":
        from .mai_research import MODEL

        config["RESEARCH_MODEL_ID"] = MODEL
    if config["MODEL_PROVIDER"] == "mai_desktop":
        from .mai_desktop import MODEL_ID

        if config["APP_ENV"] != "development":
            raise RuntimeError("mAI Desktop access is development only.")
        team = config["MAI_TEAM_NAME"]
        if (not isinstance(team, str) or not team.strip() or not team.isascii()
                or any(ord(c) < 32 or ord(c) == 127 for c in team)):
            raise ValueError("MAI_TEAM_NAME must be a nonblank ASCII header value.")
        config["MAI_TEAM_NAME"] = team.strip()
        config["ANTHROPIC_MODEL_ID"] = MODEL_ID
    if ((config["MODEL_PROVIDER"] == "anthropic" or config["RESEARCH_PROVIDER"] == "anthropic")
            and not config["TESTING"]
            and not config["ANTHROPIC_API_KEY"] and not config["SMOKE_MODE"]):
        raise RuntimeError("ANTHROPIC_API_KEY is required outside tests.")
    return config
