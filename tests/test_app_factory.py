from pathlib import Path

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
    }
    assert api_key not in response.get_data(as_text=True)


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


def test_wsgi_patches_gevent_before_importing_application_dependencies():
    wsgi = Path("wsgi.py").read_text(encoding="utf-8")

    assert 'if "gevent" in sys.argv:' in wsgi
    assert wsgi.index("monkey.patch_all()") < wsgi.index(
        "from cpf_fcv_reviewer.app import create_app"
    )
