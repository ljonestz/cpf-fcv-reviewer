from hashlib import sha256
from pathlib import Path


def test_render_blueprint_uses_paid_single_instance_persistent_disk():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")

    assert "plan: starter" in blueprint
    assert "numInstances: 1" in blueprint
    assert "mountPath: /var/data" in blueprint
    assert "PERSISTENCE_PATH" in blueprint
    assert "/var/data/reviews.sqlite3" in blueprint


def test_render_blueprint_runs_current_branch_and_threaded_gunicorn():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")

    assert "branch: main" in blueprint
    assert "--worker-class gthread" in blueprint
    assert "healthCheckPath: /health" in blueprint
    assert "maxShutdownDelaySeconds: 300" in blueprint


def test_render_blueprint_pins_current_strategy_registry_bundle():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")
    bundle = Path("registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json")

    assert "cpf_fcv_reviewer_public_guardrails_v1.1.0.json" in blueprint
    # Derive the pin from the bundle so regenerating it cannot pass this test
    # and then fail closed at boot.
    assert sha256(bundle.read_bytes()).hexdigest() in blueprint


def test_render_blueprint_enables_named_reliefweb_recovery():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")

    assert "key: RELIEFWEB_APP_NAME\n        sync: false" in blueprint
