from hashlib import sha256
from pathlib import Path

import pytest

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import (
    DocumentRole,
    EvidenceLocator,
    EvidencePack,
    PriorityArea,
    RecommendationScale,
    RevisionSummaryItem,
    SensitivityCategory,
)
from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment
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


def test_runtime_validation_does_not_require_confirmed_priority_response(
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
            "review_focus": "Is the partnership logic credible?",
        },
    }

    validated = validate(context)

    assert "missing_priority_response" not in {
        issue["code"] for issue in validated["validation_issues"]
    }


def test_runtime_builds_evidence_and_completes_an_uploaded_review(monkeypatch):
    class FakeGateway:
        def __init__(self, api_key, model_id):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            evidence_id = pack.evidence[0].evidence_id
            return output_type(
                overall_read="The draft identifies a material delivery constraint.",
                revision_summary=(
                    RevisionSummaryItem(
                        priority_area_id="area-1",
                        action="Clarify the delivery constraint.",
                    ),
                ),
                priority_areas=(
                    PriorityArea(
                        priority_area_id="area-1",
                        heading="Delivery constraint",
                        assessment="The constraint is described in the uploaded draft.",
                        why_it_matters="It may affect implementation.",
                        recommended_action="Clarify the delivery constraint.",
                        target_locator=EvidenceLocator(
                            document_title="benin-cpf.txt",
                            heading="Paragraph 1",
                            excerpt="Material FCV delivery constraint.",
                        ),
                        recommendation_scale=RecommendationScale.FINE_TUNING,
                        evidence_ids=(evidence_id,),
                        sensitivity=SensitivityCategory.CAUTIOUS,
                    ),
                ),
                institutional_referral_ids=(),
                limitations=("No current RRA was supplied.",),
                coverage_note="The review covers the uploaded CPF.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )
    events = []
    context = services["review_orchestrator"].run(
        {
            "assessment_id": "run-1",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"Material FCV delivery constraint. " * 20,
                },
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: events.append((kind, data)),
    )

    assert context["evidence_pack"].evidence
    assert context["result"].priority_areas[0].evidence_ids == (
        context["evidence_pack"].evidence[0].evidence_id,
    )
    assert events[-1][0] == "run_complete"


def test_runtime_preserves_primary_evidence_with_supporting_document(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            captured["pack"] = pack
            return output_type(
                overall_read="The draft identifies a material delivery constraint.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the uploaded CPF and package documents.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )

    context = services["review_orchestrator"].run(
        {
            "assessment_id": "run-with-supporting-document",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"Primary CPF delivery constraint. " * 20,
                },
                "package_documents": [
                    {
                        "name": "benin-package.txt",
                        "bytes": b"Supporting package context. " * 10,
                    },
                ],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    pack = captured["pack"]
    primary_evidence = [
        item
        for item in pack.evidence
        if item.locator and item.locator.document_title == "benin-cpf.txt"
    ]
    package_evidence = [
        item
        for item in pack.evidence
        if item.locator and item.locator.document_title == "benin-package.txt"
    ]
    assert primary_evidence
    assert all(item.document_role == DocumentRole.PRIMARY for item in primary_evidence)
    assert package_evidence
    assert all(item.document_role == DocumentRole.PACKAGE for item in package_evidence)
    assert context["result"].document_coverage.primary_document == "benin-cpf.txt"


def test_runtime_preserves_three_upload_roles_and_focus_in_evidence(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["payload"] = payload
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The draft needs a clearer delivery approach.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the CPF, package, and context documents.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )

    services["review_orchestrator"].run(
        {
            "assessment_id": "run-with-three-upload-roles",
            "payload": {
                "country": "Benin",
                "review_stage": "concept_review",
                "detail_level": "in_depth",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"Primary CPF delivery constraint. " * 20,
                },
                "package_documents": [
                    {
                        "name": "benin-results.txt",
                        "bytes": b"Package results framework. " * 10,
                    },
                ],
                "context_documents": [
                    {
                        "name": "benin-rra.txt",
                        "bytes": b"Context risk analysis. " * 10,
                    },
                ],
                "review_focus": "Focus on delivery arrangements.",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    pack = captured["pack"]
    by_role = {
        role: [item for item in pack.evidence if item.document_role == role]
        for role in DocumentRole
    }
    assert all(by_role.values())
    assert all(item.evidence_id.startswith("primary-") for item in by_role[DocumentRole.PRIMARY])
    assert all(item.evidence_id.startswith("package-") for item in by_role[DocumentRole.PACKAGE])
    assert all(item.evidence_id.startswith("context-") for item in by_role[DocumentRole.CONTEXT])
    assert set(pack.metadata.document_fingerprints) == {
        "primary:benin-cpf.txt",
        "package:1:benin-results.txt",
        "context:1:benin-rra.txt",
    }
    assert pack.metadata.detail_level.value == "in_depth"
    assert captured["payload"]["review_focus"] == "Focus on delivery arrangements."


def test_runtime_role_budgets_reserve_context_and_balance_package_documents(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The draft needs a clearer delivery approach.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the uploaded CPF and corroborating documents.",
            )

    def extracted(name, role, count):
        return ExtractedDocument(
            name=name,
            segments=tuple(
                ExtractedSegment(
                    text=f"{role} segment {index}",
                    page=None,
                    heading=None,
                    element=f"{role} {index}",
                )
                for index in range(count)
            ),
            warnings=(),
        )

    def fake_extract(data, name, *, max_pdf_pages=None):
        if name == "benin-cpf.txt":
            return extracted(name, "primary", 20)
        if name.startswith("package-"):
            return extracted(name, "package", 10)
        return extracted(name, "context", 10)

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.extract_document", fake_extract)
    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )

    services["review_orchestrator"].run(
        {
            "assessment_id": "run-with-saturated-role-budgets",
            "payload": {
                "country": "Benin",
                "review_stage": "concept_review",
                "detail_level": "in_depth",
                "cpf": {"name": "benin-cpf.txt", "bytes": b"primary"},
                "package_documents": [
                    {"name": f"package-{index}.txt", "bytes": b"package"}
                    for index in range(3)
                ],
                "context_documents": [
                    {"name": f"context-{index}.txt", "bytes": b"context"}
                    for index in range(2)
                ],
                "review_focus": "",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    by_role = {
        role: [item for item in captured["pack"].evidence if item.document_role == role]
        for role in DocumentRole
    }
    assert len(by_role[DocumentRole.PRIMARY]) == 12
    assert len(by_role[DocumentRole.PACKAGE]) == 8
    assert len(by_role[DocumentRole.CONTEXT]) == 4
    assert len(captured["pack"].evidence) == 24
    assert len({item.locator.document_title for item in by_role[DocumentRole.PACKAGE]}) == 3
    assert len({item.locator.document_title for item in by_role[DocumentRole.CONTEXT]}) == 2
    assert len(by_role[DocumentRole.PRIMARY]) > len(by_role[DocumentRole.PACKAGE])


def test_runtime_bounds_model_visible_corrections_but_preserves_lineage(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            captured["pack"] = pack
            return output_type(
                overall_read="The draft requires cautious review.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the uploaded CPF.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )
    corrections = [
        {
            "correction_id": f"correction-{index:02d}",
            "created_at": "2026-08-11T18:00:00+00:00",
            "text": "x" * 5000,
            "independently_supported": False,
        }
        for index in range(25)
    ]

    services["review_orchestrator"].run(
        {
            "assessment_id": "run-with-corrections",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"Material FCV delivery constraint. " * 20,
                },
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": corrections,
            },
        },
        lambda kind, data: None,
    )

    pack = captured["pack"]
    assert len(pack.user_corrections) == 20
    assert all(len(item.text) <= 2000 for item in pack.user_corrections)
    assert len(pack.metadata.correction_ids) == 25


def test_runtime_passes_only_model_authored_forbidden_phrases_to_repair(monkeypatch):
    repair_payloads = []

    class FakeGateway:
        def __init__(self, api_key, model_id):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            if prompt_name == "repair":
                repair_payloads.append(payload)
                overall_read = "The draft requires cautious review."
            else:
                overall_read = "This package is eligible for special treatment."
            return output_type(
                overall_read=overall_read,
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the uploaded CPF.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeGateway,
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True)
    )

    context = services["review_orchestrator"].run(
        {
            "assessment_id": "run-repair-target",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"SOURCE_SENTINEL material delivery constraint. " * 10,
                },
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    assert repair_payloads[0]["forbidden_phrases"] == ("eligible for", "eligible")
    assert "metadata" not in repair_payloads[0]["draft"]
    assert "SOURCE_SENTINEL" not in str(repair_payloads[0])
    assert context["result"].metadata.repair_count == 1
