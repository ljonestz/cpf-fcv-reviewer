from cpf_fcv_reviewer.app import create_app


def test_health_reports_release_without_secrets():
    app = create_app({"TESTING": True, "APP_RELEASE": "test-release"})
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "release": "test-release",
        "storage": "volatile",
    }
    assert "ANTHROPIC_API_KEY" not in response.get_data(as_text=True)


def test_production_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    try:
        create_app({"TESTING": False})
    except RuntimeError as exc:
        assert str(exc) == "ANTHROPIC_API_KEY is required outside tests."
    else:
        raise AssertionError("create_app must fail closed without an API key")
