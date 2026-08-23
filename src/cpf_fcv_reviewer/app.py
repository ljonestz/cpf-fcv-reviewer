from __future__ import annotations

import atexit
from hashlib import sha256
from pathlib import Path

from flask import Flask, jsonify, render_template

from .background import InProcessAssessmentQueue, PersistentAssessmentWorker
from .config import build_config
from .persistent_store import SQLiteSessionStore
from .routes import bp as review_blueprint
from .runtime import build_runtime_services
from .session_store import VolatileSessionStore


def create_app(
    overrides: dict | None = None,
    services: dict | None = None,
    *,
    use_environment: bool = True,
) -> Flask:
    app = Flask(__name__)
    app_config = build_config(overrides, use_environment=use_environment)
    if app_config["SMOKE_MODE"] and not (
        services is not None and services.get("_smoke_mode") is True
    ):
        raise RuntimeError("SMOKE_MODE must be created through create_smoke_app.")
    app.config.update(app_config)
    persistence_path = str(app.config.get("PERSISTENCE_PATH", "")).strip()
    if services is None:
        services = {} if app.testing else build_runtime_services(app.config)
    injected_session_store = (
        services is not None and services.get("session_store") is not None
    )
    if (
        app.config["APP_ENV"] == "production"
        and not app.testing
        and not persistence_path
        and not injected_session_store
        and not app.config["ALLOW_VOLATILE_PROTOTYPE"]
    ):
        raise RuntimeError(
            "Production requires PERSISTENCE_PATH or an explicitly injected session_store."
        )
    app.extensions.update(services)
    if "session_store" not in app.extensions:
        if persistence_path:
            app.extensions["session_store"] = SQLiteSessionStore(
                persistence_path,
                ttl_seconds=app.config["SESSION_TTL_SECONDS"],
            )
        else:
            app.extensions["session_store"] = VolatileSessionStore(
                ttl_seconds=app.config["SESSION_TTL_SECONDS"]
            )
    if "assessment_queue" not in app.extensions:
        session_store = app.extensions["session_store"]
        if (
            isinstance(session_store, SQLiteSessionStore)
            and app.config["START_BACKGROUND_RUNS"]
        ):
            worker = PersistentAssessmentWorker(
                app,
                session_store,
                poll_seconds=app.config["WORKER_POLL_SECONDS"],
            )
            worker.start()
            atexit.register(worker.stop)
            app.extensions["assessment_queue"] = worker
        else:
            app.extensions["assessment_queue"] = InProcessAssessmentQueue(
                app,
                enabled=app.config["START_BACKGROUND_RUNS"],
            )
    app.register_blueprint(review_blueprint)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            release=app.config["APP_RELEASE"],
            storage=getattr(
                app.extensions["session_store"], "storage_mode", "volatile"
            ),
            queue=getattr(
                app.extensions["assessment_queue"], "mode", "configured"
            ),
        )

    return app


def create_smoke_app(*, start_background_runs: bool = True) -> Flask:
    """Create the explicit, provider-free development smoke application."""
    root = Path(__file__).resolve().parents[2]
    registry = root / "tests" / "fixtures" / "registry_bundle.synthetic.json"
    registry_hash = sha256(registry.read_bytes()).hexdigest()
    config = {
        "APP_RELEASE": "deterministic-smoke",
        "APP_ENV": "development",
        "SMOKE_MODE": True,
        "START_BACKGROUND_RUNS": start_background_runs,
        "REGISTRY_BUNDLE_PATH": str(registry),
        "REGISTRY_BUNDLE_SHA256": registry_hash,
        "ALLOW_SYNTHETIC_REGISTRY": True,
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_MODEL_ID": "deterministic-smoke",
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "RESEARCH_MAX_ATTEMPTS": 1,
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 5.0,
        "RESEARCH_TOTAL_BUDGET_SECONDS": 15.0,
        "RESEARCH_MINIMUM_CLAIMS": 4,
        "RESEARCH_MINIMUM_PUBLISHERS": 2,
        "RESEARCH_RETRY_BACKOFF_SECONDS": 0.0,
        "RESEARCH_RECOVERY_TIMEOUT_SECONDS": 1.0,
        "RESEARCH_RECOVERY_MAX_BYTES": 500_000,
        "RELIEFWEB_APP_NAME": "",
        "SESSION_TTL_SECONDS": 3_600,
        "TESTING": False,
    }
    from .smoke import build_smoke_services

    config = build_config(config, use_environment=False)
    services = build_smoke_services(config)
    services["_smoke_mode"] = True
    return create_app(config, services=services, use_environment=False)
