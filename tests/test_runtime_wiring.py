from hashlib import sha256
from pathlib import Path

import pytest

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import EvidencePack
from cpf_fcv_reviewer.registry import load_registry_bundle
from cpf_fcv_reviewer.runtime import build_runtime_services
from cpf_fcv_reviewer.sources import SourceCandidate

FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")


def test_explicit_services_are_registered_without_runtime_rebuild():
    orchestrator = object()
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)

    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"review_orchestrator": orchestrator, "registry_bundle": bundle},
    )

    assert app.extensions["review_orchestrator"] is orchestrator
    assert app.extensions["registry_bundle"] is bundle
    assert "session_store" in app.extensions


def production_config(**overrides):
    config = {
        "TESTING": False,
        "ANTHROPIC_API_KEY": "test-key",
        "ANTHROPIC_MODEL_ID": "test-model",
        "REGISTRY_BUNDLE_PATH": str(FIXTURE),
        "REGISTRY_BUNDLE_SHA256": sha256(FIXTURE.read_bytes()).hexdigest(),
        "ALLOW_SYNTHETIC_REGISTRY": False,
    }
    config.update(overrides)
    return config


def test_production_startup_fails_closed_for_missing_registry(tmp_path):
    with pytest.raises(RuntimeError, match="registry bundle"):
        create_app(production_config(REGISTRY_BUNDLE_PATH=str(tmp_path / "missing.json")))


def test_runtime_rejects_registry_hash_mismatch():
    with pytest.raises(RuntimeError, match="hash mismatch"):
        build_runtime_services(
            production_config(
                ALLOW_SYNTHETIC_REGISTRY=True,
                REGISTRY_BUNDLE_SHA256="0" * 64,
            )
        )


def test_production_rejects_synthetic_registry_even_with_valid_hash():
    with pytest.raises(RuntimeError, match="test-only"):
        build_runtime_services(production_config())


def test_runtime_builds_exact_named_step_sequence(monkeypatch):
    class FakeModelGateway:
        def __init__(self, api_key, model_id):
            self.api_key = api_key
            self.model_id = model_id

    class FakeResearchGateway(FakeModelGateway):
        pass

    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicModelGateway",
        FakeModelGateway,
    )
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeResearchGateway,
    )

    services = build_runtime_services(production_config(ALLOW_SYNTHETIC_REGISTRY=True))

    assert set(services) == {"review_orchestrator", "registry_bundle"}
    assert [name for name, _ in services["review_orchestrator"].steps] == [
        "extract",
        "resolve_sources",
        "research",
        "build_evidence",
        "map",
        "review",
        "validate",
        "render",
    ]


def _runtime_services(monkeypatch):
    class FakeGateway:
        def __init__(self, api_key, model_id):
            pass

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    return build_runtime_services(production_config(ALLOW_SYNTHETIC_REGISTRY=True))


def test_runtime_resolve_sources_prefers_direct_original(monkeypatch):
    services = _runtime_services(monkeypatch)
    steps = dict(services["review_orchestrator"].steps)
    original = SourceCandidate("sp-1", "Country RRA.docx", "3", "sharepoint_original", True)
    derived = SourceCandidate("md-1", "Country RRA.md", "3", "derived_copy", True)

    context = steps["resolve_sources"]({"source_candidates": (derived, original)})

    assert context["authoritative_source"] == original


def test_runtime_resolve_sources_uses_upload_fallback(monkeypatch):
    services = _runtime_services(monkeypatch)
    steps = dict(services["review_orchestrator"].steps)
    upload = SourceCandidate("up-1", "Country RRA.docx", "3", "upload", True)

    context = steps["resolve_sources"]({"source_candidates": (upload,)})

    assert context["authoritative_source"] == upload


def test_runtime_cannot_report_completion_without_a_review_result(monkeypatch):
    services = _runtime_services(monkeypatch)
    events = []

    with pytest.raises(RuntimeError, match="Review result is unavailable"):
        services["review_orchestrator"].run(
            {},
            lambda kind, data: events.append((kind, data)),
        )

    assert events[-1][0] == "run_failed"
    assert not any(kind == "run_complete" for kind, _ in events)


def test_runtime_validation_requires_confirmed_priority_response(
    monkeypatch,
    make_valid_result,
):
    result, evidence = make_valid_result
    services = _runtime_services(monkeypatch)
    validate = dict(services["review_orchestrator"].steps)["validate"]
    context = {
        "result": result,
        "evidence_pack": EvidencePack(
            metadata=result.metadata,
            evidence=tuple(evidence.values()),
            diagnostic_entries=(),
        ),
        "payload": {
            "priority_questions": ("Is the partnership logic credible?",),
        },
    }

    validated = validate(context)

    assert "missing_priority_response" in {
        issue["code"] for issue in validated["validation_issues"]
    }
