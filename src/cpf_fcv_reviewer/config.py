from __future__ import annotations

import os


def build_config(overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    config = {
        "APP_RELEASE": os.getenv("APP_RELEASE", "dev"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "ANTHROPIC_MODEL_ID": os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5"),
        "REGISTRY_BUNDLE_PATH": os.getenv("REGISTRY_BUNDLE_PATH", ""),
        "REGISTRY_BUNDLE_SHA256": os.getenv("REGISTRY_BUNDLE_SHA256", ""),
        "ALLOW_SYNTHETIC_REGISTRY": False,
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "RESEARCH_MAX_ATTEMPTS": int(os.getenv("RESEARCH_MAX_ATTEMPTS", "3")),
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": float(
            os.getenv("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "90")
        ),
        "RESEARCH_TOTAL_BUDGET_SECONDS": float(
            os.getenv("RESEARCH_TOTAL_BUDGET_SECONDS", "300")
        ),
        "RESEARCH_MINIMUM_CLAIMS": int(os.getenv("RESEARCH_MINIMUM_CLAIMS", "4")),
        "RESEARCH_MINIMUM_PUBLISHERS": int(
            os.getenv("RESEARCH_MINIMUM_PUBLISHERS", "2")
        ),
        "RESEARCH_RETRY_BACKOFF_SECONDS": float(
            os.getenv("RESEARCH_RETRY_BACKOFF_SECONDS", "1")
        ),
        "SESSION_TTL_SECONDS": (
            overrides["SESSION_TTL_SECONDS"]
            if "SESSION_TTL_SECONDS" in overrides
            else int(os.getenv("SESSION_TTL_SECONDS", "3600"))
        ),
        "START_BACKGROUND_RUNS": True,
        "TESTING": False,
    }
    config.update(overrides or {})
    positive_research_settings = (
        "RESEARCH_MAX_ATTEMPTS",
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS",
        "RESEARCH_TOTAL_BUDGET_SECONDS",
        "RESEARCH_MINIMUM_CLAIMS",
        "RESEARCH_MINIMUM_PUBLISHERS",
    )
    if any(config[name] <= 0 for name in positive_research_settings):
        raise ValueError("Research settings must be positive.")
    if config["RESEARCH_RETRY_BACKOFF_SECONDS"] < 0:
        raise ValueError("Research retry backoff cannot be negative.")
    if config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"] > config["RESEARCH_TOTAL_BUDGET_SECONDS"]:
        raise ValueError("Research attempt timeout cannot exceed total budget.")
    config["ANTHROPIC_API_KEY"] = config["ANTHROPIC_API_KEY"].strip()
    if not config["TESTING"] and not config["ANTHROPIC_API_KEY"]:
        raise RuntimeError("ANTHROPIC_API_KEY is required outside tests.")
    return config
