from pathlib import Path

import pytest

from cpf_fcv_reviewer.app import create_app


def test_health_reports_release_without_secrets():
    api_key = "sentinel-api-key-must-not-leak"
    app = create_app(
        {
            "TESTING": True,
            "APP_RELEASE": "test-release",
            "ANTHROPIC_API_KEY": api_key,
        }
    )
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "release": "test-release",
        "storage": "volatile",
        "queue": "in_process",
    }
    assert api_key not in response.get_data(as_text=True)


def test_health_prefers_render_git_commit(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    app = create_app({"TESTING": True})

    assert app.test_client().get("/health").get_json()["release"] == (
        "abcdef1234567890"
    )


def test_production_defaults_to_24_hour_retention():
    app = create_app({"TESTING": True}, use_environment=False)

    assert app.config["SESSION_TTL_SECONDS"] == 86_400


def test_production_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    try:
        create_app({"TESTING": False})
    except RuntimeError as exc:
        assert str(exc) == "ANTHROPIC_API_KEY is required outside tests."
    else:
        raise AssertionError("create_app must fail closed without an API key")


def test_production_rejects_whitespace_only_api_key():
    try:
        create_app({"TESTING": False, "ANTHROPIC_API_KEY": "   "})
    except RuntimeError as exc:
        assert str(exc) == "ANTHROPIC_API_KEY is required outside tests."
    else:
        raise AssertionError("create_app must reject a whitespace-only API key")


def test_false_smoke_environment_does_not_relax_production_api_key(monkeypatch):
    monkeypatch.setenv("SMOKE_MODE", "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is required outside tests"):
        create_app({"TESTING": False})


def test_normal_create_app_cannot_enable_smoke_mode_directly():
    with pytest.raises(RuntimeError, match="create_smoke_app"):
        create_app(
            {
                "TESTING": True,
                "APP_ENV": "development",
                "SMOKE_MODE": True,
            }
        )


def test_session_ttl_override_skips_malformed_environment_value(monkeypatch):
    monkeypatch.setenv("SESSION_TTL_SECONDS", "not-an-integer")
    app = create_app({"TESTING": True, "SESSION_TTL_SECONDS": 120})

    assert app.config["SESSION_TTL_SECONDS"] == 120


def test_render_uses_threaded_worker_without_late_ssl_monkey_patch():
    procfile = Path("Procfile").read_text(encoding="utf-8")

    assert "--worker-class gthread" in procfile
    assert "--threads 4" in procfile
    assert "gevent" not in procfile


def test_render_python_matches_the_validated_runtime_line():
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.13"

def test_gunicorn_default_timeout_covers_background_review_budget():
    namespace = {}
    config = Path("gunicorn.conf.py").read_text(encoding="utf-8")
    exec(compile(config, "gunicorn.conf.py", "exec"), namespace)

    assert namespace["timeout"] == 1200



def test_wsgi_patches_gevent_before_importing_application_dependencies():
    wsgi = Path("wsgi.py").read_text(encoding="utf-8")

    assert 'if "gevent" in sys.argv:' in wsgi
    assert wsgi.index("monkey.patch_all()") < wsgi.index(
        "from cpf_fcv_reviewer.app import create_app"
    )
