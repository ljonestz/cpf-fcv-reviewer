from __future__ import annotations

import os


def build_config(overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    config = {
        "APP_RELEASE": os.getenv("APP_RELEASE", "dev"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "SESSION_TTL_SECONDS": (
            overrides["SESSION_TTL_SECONDS"]
            if "SESSION_TTL_SECONDS" in overrides
            else int(os.getenv("SESSION_TTL_SECONDS", "3600"))
        ),
        "START_BACKGROUND_RUNS": True,
        "TESTING": False,
    }
    config.update(overrides or {})
    config["ANTHROPIC_API_KEY"] = config["ANTHROPIC_API_KEY"].strip()
    if not config["TESTING"] and not config["ANTHROPIC_API_KEY"]:
        raise RuntimeError("ANTHROPIC_API_KEY is required outside tests.")
    return config
