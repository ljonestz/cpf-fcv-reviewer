from __future__ import annotations

from flask import Flask, jsonify

from .config import build_config


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config(overrides))

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            release=app.config["APP_RELEASE"],
            storage="volatile",
        )

    return app
