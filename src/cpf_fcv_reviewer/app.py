from __future__ import annotations

from flask import Flask, jsonify, render_template

from .config import build_config
from .routes import bp as review_blueprint
from .runtime import build_runtime_services
from .session_store import VolatileSessionStore


def create_app(
    overrides: dict | None = None,
    services: dict | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config(overrides))
    if services is None:
        services = {} if app.testing else build_runtime_services(app.config)
    app.extensions.update(services)
    app.extensions["session_store"] = VolatileSessionStore(
        ttl_seconds=app.config["SESSION_TTL_SECONDS"]
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
            storage="volatile",
        )

    return app
