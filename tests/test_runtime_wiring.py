from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import (
    CurrentEvidenceTier,
    DocumentRole,
    EvidenceLocator,
    EvidencePack,
    PriorityArea,
    RecommendationScale,
    RevisionSummaryItem,
    SensitivityCategory,
)
from cpf_fcv_reviewer.extraction import (
    DocumentUnreadable,
    ExtractedDocument,
    ExtractedSegment,
    ExtractionLimitExceeded,
)
from cpf_fcv_reviewer.public_research import CurrentContextClaim
from cpf_fcv_reviewer.registry import load_registry_bundle
from cpf_fcv_reviewer.research_controller import ResearchMode, ResearchResult
from cpf_fcv_reviewer.runtime import _truncate_at_word_boundary, build_runtime_services
from cpf_fcv_reviewer.sources import SourceCandidate

FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")
OPTIONAL_UPLOAD_WARNING = (
    "An optional uploaded document could not be read and was excluded."
)


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


MALFORMED_OPTIONAL_UPLOADS = (
    ("private-invalid-zip.docx", b"X9K7Q not a zip archive"),
    (
        "private-missing-content-types.docx",
        _zip_bytes({"word/document.xml": b"<w:document>X9K7Q</w:document>"}),
    ),
    (
        "private-missing-document-part.docx",
        _zip_bytes(
            {
                "[Content_Types].xml": (
                    b'<Types xmlns="http://schemas.openxmlformats.org/package/'
                    b'2006/content-types"><!--X9K7Q--></Types>'
                )
            }
        ),
    ),
    ("private-financial-token.pdf", b"X9K7Q-secret-looking-prefix"),
)


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
        "RESEARCH_MAX_ATTEMPTS": 3,
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 90.0,
        "RESEARCH_TOTAL_BUDGET_SECONDS": 300.0,
        "RESEARCH_MINIMUM_CLAIMS": 4,
        "RESEARCH_MINIMUM_PUBLISHERS": 2,
        "RESEARCH_RETRY_BACKOFF_SECONDS": 1.0,
    }
    config.update(overrides)
    return config


def _current_claims():
    return (
        CurrentContextClaim(
            claim_id="claim-1", text="Exact current finding.", publisher="World Bank",
            source_title="Finding", source_url="https://www.worldbank.org/finding",
            source_date=date(2026, 7, 1), source_type="report", relevance="Relevant.",
            context_kind="structural_dynamic", relationship="establishes",
            licensed_data_required=False,
        ),
        CurrentContextClaim(
            claim_id="claim-2", text="Exact other finding.", publisher="Other source",
            source_title="Other finding", source_url="https://other.example.org/finding",
            source_date=date(2026, 7, 2), source_type="briefing", relevance="Relevant.",
            context_kind="current_development", relationship="corroborates",
            licensed_data_required=False,
        ),
    )


class _InjectedResearchController:
    def __init__(self, result=None):
        self.requests = []
        self.emits = []
        self.allow_document_led = []
        self.result = result

    def run(self, request, emit, *, allow_document_led=False):
        self.requests.append(request)
        self.emits.append(emit)
        self.allow_document_led.append(allow_document_led)
        return self.result or ResearchResult(_current_claims(), {}, 1, CurrentEvidenceTier.FULL)


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
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
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

    assert set(services) == {
        "review_orchestrator",
        "registry_bundle",
        "research_controller",
    }
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
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
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
    render = dict(services["review_orchestrator"].steps)["render"]

    with pytest.raises(RuntimeError, match="Review result is unavailable"):
        render({})


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
    gateway_calls = []
    current_context_evidence_id = None

    class FakeGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            nonlocal current_context_evidence_id
            gateway_calls.append(prompt_name)
            if prompt_name == "repair":
                assert {issue["code"] for issue in payload["validation_issues"]} == {
                    "missing_current_context_support"
                }
                repaired_draft = dict(payload["draft"])
                repaired_priority = dict(repaired_draft["priority_areas"][0])
                repaired_priority["evidence_ids"] = (
                    *repaired_priority["evidence_ids"],
                    current_context_evidence_id,
                )
                repaired_draft["priority_areas"] = (repaired_priority,)
                return output_type.model_validate(repaired_draft)

            assert prompt_name == "review"
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            evidence_id = next(
                item.evidence_id
                for item in pack.evidence
                if item.evidence_type == "document_fact"
            )
            current_context_evidence_id = next(
                item.evidence_id
                for item in pack.evidence
                if item.evidence_type == "current_context"
            )
            return output_type(
                overall_read="The draft identifies a material delivery constraint.",
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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
        current_context_evidence_id,
    )
    assert gateway_calls == ["review", "repair"]
    assert events[-1][0] == "run_complete"


def test_runtime_excludes_bad_optional_uploads_independently(monkeypatch):
    services = _runtime_services(monkeypatch)
    steps = dict(services["review_orchestrator"].steps)

    def document(name, text):
        return ExtractedDocument(
            name=name,
            segments=(
                ExtractedSegment(
                    text=text,
                    page=None,
                    heading=None,
                    element="Paragraph 1",
                ),
            ) if text else (),
            warnings=(),
        )

    def fake_extract(data, name, *, max_pdf_pages=None):
        if name == "benin-cpf.txt":
            return document(name, "Readable primary evidence. " * 10)
        if name == "malformed-package.pdf":
            raise ExtractionLimitExceeded("PRIVATE_FORMAT_DETAIL")
        if name == "empty-context.txt":
            return document(name, "")
        return document(name, "Usable optional evidence.")

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.extract_document", fake_extract)
    payload = {
        "country": "Benin",
        "review_stage": "finalization",
        "detail_level": "standard",
        "cpf": {"name": "benin-cpf.txt", "bytes": b"primary"},
        "package_documents": [
            {"name": "malformed-package.pdf", "bytes": b"PRIVATE_PACKAGE_TEXT"},
            {"name": "usable-package.txt", "bytes": b"usable package"},
        ],
        "context_documents": [
            {"name": "empty-context.txt", "bytes": b"PRIVATE_CONTEXT_TEXT"},
            {"name": "usable-context.txt", "bytes": b"usable context"},
        ],
        "review_focus": "",
        "corrections": [],
    }

    context = steps["extract"]({"assessment_id": "optional-isolation", "payload": payload})

    assert [item.name for item in context["package_documents"]] == [
        "usable-package.txt"
    ]
    assert [item.name for item in context["context_documents"]] == [
        "usable-context.txt"
    ]
    warning = "An optional uploaded document could not be read and was excluded."
    assert context["extraction_warnings"] == (warning, warning)
    assert not any(
        value in " ".join(context["extraction_warnings"])
        for value in (
            "malformed-package.pdf",
            "empty-context.txt",
            "PRIVATE_FORMAT_DETAIL",
            "PRIVATE_PACKAGE_TEXT",
            "PRIVATE_CONTEXT_TEXT",
        )
    )

    context["research_result"] = ResearchResult(
        _current_claims(), {}, 1, CurrentEvidenceTier.FULL
    )
    context = steps["build_evidence"](context)

    assert set(context["evidence_pack"].metadata.document_fingerprints) == {
        "primary:benin-cpf.txt",
        "package:2:usable-package.txt",
        "context:2:usable-context.txt",
    }


@pytest.mark.parametrize(
    ("invalid_name", "invalid_bytes"),
    MALFORMED_OPTIONAL_UPLOADS,
    ids=(
        "invalid-zip",
        "missing-content-types",
        "missing-document-part",
        "invalid-pdf",
    ),
)
def test_runtime_malformed_optional_bytes_are_private_and_valid_context_continues(
    monkeypatch,
    caplog,
    capsys,
    invalid_name,
    invalid_bytes,
):
    secret_marker = "X9K7Q"
    controller = _InjectedResearchController(
        ResearchResult(
            (),
            {},
            1,
            CurrentEvidenceTier.DOCUMENT_LED,
            "Independent current-country research was unavailable.",
        )
    )

    class ModelGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            return output_type(
                overall_read="The uploaded draft can be reviewed with caution.",
                alignment_readout="The draft provides bounded contextual evidence.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the readable submitted documents.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", ModelGateway)
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=controller,
    )
    events = []
    caplog.clear()

    context = services["review_orchestrator"].run(
        {
            "assessment_id": "private-optional-preflight",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {
                    "name": "benin-cpf.txt",
                    "bytes": b"Readable primary evidence. " * 10,
                },
                "package_documents": [],
                "context_documents": [
                    {
                        "name": invalid_name,
                        "bytes": invalid_bytes,
                    },
                    {
                        "name": "usable-context.txt",
                        "bytes": b"Usable current-context evidence.",
                    },
                ],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: events.append((kind, data)),
    )

    assert [document.name for document in context["context_documents"]] == [
        "usable-context.txt"
    ]
    assert context["extraction_warnings"] == (OPTIONAL_UPLOAD_WARNING,)
    assert context["evidence_pack"].warnings.count(OPTIONAL_UPLOAD_WARNING) == 1
    assert controller.allow_document_led == [True]
    assert events[-1][0] == "run_complete"
    captured = capsys.readouterr()
    disclosed = " ".join(
        (
            caplog.text,
            captured.out,
            captured.err,
            repr(events),
            context["result"].model_dump_json(),
        )
    )
    assert secret_marker not in disclosed
    assert invalid_name not in disclosed


@pytest.mark.parametrize(
    ("invalid_name", "invalid_bytes"),
    MALFORMED_OPTIONAL_UPLOADS,
    ids=(
        "invalid-zip",
        "missing-content-types",
        "missing-document-part",
        "invalid-pdf",
    ),
)
def test_runtime_malformed_optional_cannot_enable_document_led(
    monkeypatch,
    invalid_name,
    invalid_bytes,
):
    controller = _InjectedResearchController()
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        model_gateway=object(),
        research_controller=controller,
    )
    steps = dict(services["review_orchestrator"].steps)
    primary_without_text = ExtractedDocument("benin-cpf.txt", (), ())

    def allow_document_led_for(context_documents):
        context = steps["extract"](
            {
                "payload": {
                    "country": "Benin",
                    "cpf": {
                        "name": "benin-cpf.txt",
                        "bytes": b"Readable primary evidence. " * 10,
                    },
                    "package_documents": [],
                    "context_documents": context_documents,
                }
            }
        )
        context["primary_document"] = primary_without_text
        context["_emit"] = lambda *_: None
        steps["research"](context)
        return controller.allow_document_led[-1]

    invalid_upload = {
        "name": invalid_name,
        "bytes": invalid_bytes,
    }
    assert allow_document_led_for([invalid_upload]) is False
    assert allow_document_led_for(
        [
            invalid_upload,
            {"name": "usable-context.txt", "bytes": b"Usable context evidence."},
        ]
    ) is True


def test_runtime_optional_extraction_does_not_swallow_programming_defects(monkeypatch):
    services = _runtime_services(monkeypatch)
    extract = dict(services["review_orchestrator"].steps)["extract"]

    def fake_extract(data, name, *, max_pdf_pages=None):
        if name == "benin-cpf.txt":
            return ExtractedDocument(
                name=name,
                segments=(
                    ExtractedSegment(
                        text="Readable primary evidence. " * 10,
                        page=None,
                        heading=None,
                        element="Paragraph 1",
                    ),
                ),
                warnings=(),
            )
        raise KeyError("programming defect")

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.extract_document", fake_extract)

    with pytest.raises(KeyError, match="programming defect"):
        extract(
            {
                "payload": {
                    "country": "Benin",
                    "cpf": {"name": "benin-cpf.txt", "bytes": b"primary"},
                    "package_documents": [
                        {"name": "optional.txt", "bytes": b"optional"}
                    ],
                    "context_documents": [],
                }
            }
        )


def test_runtime_primary_document_remains_fail_closed(monkeypatch):
    services = _runtime_services(monkeypatch)
    extract = dict(services["review_orchestrator"].steps)["extract"]
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.extract_document",
        lambda data, name, *, max_pdf_pages=None: ExtractedDocument(name, (), ()),
    )

    with pytest.raises(DocumentUnreadable):
        extract(
            {
                "payload": {
                    "country": "Benin",
                    "cpf": {"name": "benin-cpf.txt", "bytes": b""},
                    "package_documents": [],
                    "context_documents": [],
                }
            }
        )


def test_runtime_preserves_primary_evidence_with_supporting_document(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            captured["pack"] = pack
            return output_type(
                overall_read="The draft identifies a material delivery constraint.",
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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


def test_runtime_accepts_injected_gateways_and_constructs_configured_research_controller():
    model_gateway = object()
    research_gateway = object()

    services = build_runtime_services(
        production_config(
            ALLOW_SYNTHETIC_REGISTRY=True,
            RESEARCH_MAX_ATTEMPTS=5,
            RESEARCH_TOTAL_BUDGET_SECONDS=42.0,
            RESEARCH_MINIMUM_CLAIMS=6,
            RESEARCH_MINIMUM_PUBLISHERS=3,
            RESEARCH_RETRY_BACKOFF_SECONDS=0.25,
        ),
        model_gateway=model_gateway,
        research_gateway=research_gateway,
    )

    controller = services["research_controller"]
    assert controller.gateway is research_gateway
    assert controller.max_attempts == 5
    assert controller.total_budget_seconds == 42.0
    assert controller.minimum_claims == 6
    assert controller.minimum_publishers == 3
    assert controller._backoff == (0.25,)


def test_default_research_gateway_receives_attempt_timeout(monkeypatch):
    captured = {}

    class FakeModelGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

    class FakeResearchGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds):
            captured["timeout_seconds"] = timeout_seconds

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", FakeModelGateway)
    monkeypatch.setattr(
        "cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway",
        FakeResearchGateway,
    )

    build_runtime_services(
        production_config(
            ALLOW_SYNTHETIC_REGISTRY=True,
            RESEARCH_ATTEMPT_TIMEOUT_SECONDS=12.5,
        )
    )

    assert captured["timeout_seconds"] == 12.5


def test_runtime_preserves_three_upload_roles_and_focus_in_evidence(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["payload"] = payload
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The draft needs a clearer delivery approach.",
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The draft needs a clearer delivery approach.",
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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
    assert sum(len(items) for items in by_role.values()) == 24
    assert len(
        [item for item in captured["pack"].evidence if item.evidence_type == "current_context"]
    ) == 2
    assert len({item.locator.document_title for item in by_role[DocumentRole.PACKAGE]}) == 3
    assert len({item.locator.document_title for item in by_role[DocumentRole.CONTEXT]}) == 2
    assert len(by_role[DocumentRole.PRIMARY]) > len(by_role[DocumentRole.PACKAGE])


def test_runtime_evidence_truncation_keeps_complete_words(monkeypatch):
    services = _runtime_services(monkeypatch)
    build_evidence = dict(services["review_orchestrator"].steps)["build_evidence"]
    segment_text = (
        ("x " * 299)
        + "obscure "
        + ("y " * 496)
        + "magnified "
        + ("z " * 10)
    )
    context = build_evidence(
        {
            "assessment_id": "word-boundary-evidence",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "detail_level": "standard",
                "cpf": {"name": "benin-cpf.txt", "bytes": b"primary"},
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "corrections": [],
            },
            "primary_document": ExtractedDocument(
                name="benin-cpf.txt",
                segments=(
                    ExtractedSegment(
                        text=segment_text,
                        page=None,
                        heading=None,
                        element="Paragraph 1",
                    ),
                ),
                warnings=(),
            ),
            "research_result": ResearchResult((), {}, 0, CurrentEvidenceTier.FULL),
        }
    )
    evidence = next(
        item
        for item in context["evidence_pack"].evidence
        if item.evidence_type == "document_fact"
    )

    assert len(evidence.text) <= 1600
    assert len(evidence.locator.excerpt) <= 600
    assert evidence.text.endswith("y")
    assert evidence.locator.excerpt.endswith("x")
    assert segment_text[len(evidence.text)].isspace()
    assert segment_text[len(evidence.locator.excerpt)].isspace()


def test_runtime_evidence_truncation_keeps_single_long_token_nonempty():
    truncated = _truncate_at_word_boundary("x" * 1601, 1600)

    assert truncated == "x" * 1600


def test_runtime_bounds_model_visible_corrections_but_preserves_lineage(monkeypatch):
    captured = {}

    class FakeGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            pack = EvidencePack.model_validate(payload["evidence_pack"])
            captured["pack"] = pack
            return output_type(
                overall_read="The draft requires cautious review.",
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            self.model_id = model_id

        def generate(self, *, prompt_name, payload, output_type):
            if prompt_name == "repair":
                repair_payloads.append(payload)
                overall_read = "The draft requires cautious review."
            else:
                overall_read = "This package is eligible for special treatment."
            return output_type(
                overall_read=overall_read,
                alignment_readout="The draft partly reflects current context.",
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
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=_InjectedResearchController(),
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


def _run_narrow_runtime(monkeypatch, package_text, *, controller=None):
    captured = {}

    class ModelGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The review identifies a delivery constraint.",
                alignment_readout="The draft partly reflects current context.",
                revision_summary=(), priority_areas=(), institutional_referral_ids=(),
                limitations=(), coverage_note="The review covers the uploaded CPF.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", ModelGateway)
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=controller,
        review_date_provider=lambda: date(2026, 8, 13),
    )
    context = services["review_orchestrator"].run(
        {
            "assessment_id": "narrow-runtime-run",
            "payload": {
                "country": "Benin", "review_stage": "finalization",
                "cpf": {"name": "benin-cpf.txt", "bytes": b"CPF text " * 20},
                "package_documents": [{"name": "package.txt", "bytes": package_text}],
                "context_documents": [], "review_focus": "", "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )
    return context, captured["pack"]


def test_runtime_researches_with_dated_rra_request_and_emitter(monkeypatch):
    controller = _InjectedResearchController()
    context, _ = _run_narrow_runtime(
        monkeypatch,
        b"Benin Risk and Resilience Assessment, March 2025. First segment.",
        controller=controller,
    )

    request = controller.requests[0]
    assert request.mode is ResearchMode.RRA_UPDATE
    assert request.diagnostic_title == "package.txt"
    assert request.diagnostic_date == date(2025, 3, 1)
    assert request.diagnostic_summary == (
        "Benin Risk and Resilience Assessment, March 2025. First segment."
    )
    assert controller.emits[0] is not None
    assert context["uploaded_diagnostic"].name == "package.txt"
    assert context["research_result"].tier is CurrentEvidenceTier.FULL


def test_runtime_uses_holistic_request_without_rra(monkeypatch):
    controller = _InjectedResearchController()
    context, pack = _run_narrow_runtime(
        monkeypatch, b"Package context without a diagnostic marker.", controller=controller
    )

    request = controller.requests[0]
    assert request.mode is ResearchMode.HOLISTIC
    assert request.diagnostic_title is None
    assert request.diagnostic_date is None
    assert context["uploaded_diagnostic"] is None
    assert pack.metadata.diagnostic_mode.value == "limited_framing"


def test_runtime_uses_holistic_request_but_rra_alignment_for_undated_rra(monkeypatch):
    controller = _InjectedResearchController()
    context, pack = _run_narrow_runtime(
        monkeypatch,
        b"Benin Risk and Resilience Assessment. Undated findings.",
        controller=controller,
    )

    request = controller.requests[0]
    assert request.mode is ResearchMode.HOLISTIC
    assert request.diagnostic_title is None
    assert request.diagnostic_date is None
    assert context["uploaded_diagnostic"].publication_date is None
    assert pack.metadata.diagnostic_mode.value == "rra_alignment"


def test_runtime_appends_current_research_exactly_before_review(monkeypatch):
    controller = _InjectedResearchController()
    _, pack = _run_narrow_runtime(
        monkeypatch,
        b"No diagnostic supplied.",
        controller=controller,
    )

    current = [item for item in pack.evidence if item.evidence_type == "current_context"]
    actual = [
        (item.evidence_id, item.text, item.source_url, item.confidence)
        for item in current
    ]
    assert actual == [
        ("current-001", "Exact current finding.", "https://www.worldbank.org/finding", "high"),
        ("current-002", "Exact other finding.", "https://other.example.org/finding", "medium"),
    ]


def test_runtime_appends_registry_evidence_to_model_pack(monkeypatch):
    _, pack = _run_narrow_runtime(
        monkeypatch,
        b"No diagnostic supplied.",
        controller=_InjectedResearchController(),
    )
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)

    registry = [item for item in pack.evidence if item.evidence_type == "registry_language"]
    assert [(item.evidence_id, item.text) for item in registry] == [
        (f"registry-{entry.entry_id}", entry.approved_text)
        for entry in bundle.entries
    ]
    assert all(item.confidence == "high" for item in registry)


@pytest.mark.parametrize(
    ("primary_segments", "context_segments", "expected"),
    (
        (("Readable primary",), (), True),
        ((), ("Readable context",), True),
        ((), (), False),
    ),
)
def test_runtime_passes_document_led_only_for_usable_uploaded_evidence(
    monkeypatch,
    primary_segments,
    context_segments,
    expected,
):
    controller = _InjectedResearchController(
        ResearchResult(
            (),
            {},
            1,
            CurrentEvidenceTier.DOCUMENT_LED,
            "Independent current-country research was unavailable.",
        )
    )
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        model_gateway=object(),
        research_controller=controller,
    )
    research = dict(services["review_orchestrator"].steps)["research"]

    def document(name, segments):
        return ExtractedDocument(
            name=name,
            segments=tuple(
                ExtractedSegment(text=text, page=None, heading=None, element="Paragraph 1")
                for text in segments
            ),
            warnings=(),
        )

    context = research(
        {
            "payload": {"country": "Benin"},
            "primary_document": document("benin-cpf.txt", primary_segments),
            "package_documents": (),
            "context_documents": (document("context.txt", context_segments),),
            "_emit": lambda *_: None,
        }
    )

    assert context["research_result"].tier is CurrentEvidenceTier.DOCUMENT_LED
    assert controller.allow_document_led == [expected]


def test_runtime_does_not_turn_uploaded_rra_into_current_context(monkeypatch):
    limitation = "Independent current-country research was unavailable."
    controller = _InjectedResearchController(
        ResearchResult((), {}, 1, CurrentEvidenceTier.DOCUMENT_LED, limitation)
    )
    captured = {}

    class ModelGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            captured["pack"] = EvidencePack.model_validate(payload["evidence_pack"])
            return output_type(
                overall_read="The uploaded draft can be reviewed with caution.",
                alignment_readout="Independent current context was unavailable.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=(),
                coverage_note="The review covers the uploaded CPF and RRA.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", ModelGateway)
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=controller,
    )
    context = services["review_orchestrator"].run(
        {
            "assessment_id": "rra-is-not-current-context",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {"name": "benin-cpf.txt", "bytes": b"CPF text " * 20},
                "package_documents": [
                    {
                        "name": "benin-rra.txt",
                        "bytes": b"Benin Risk and Resilience Assessment. " * 20,
                    }
                ],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    assert controller.allow_document_led == [True]
    assert not [
        item for item in captured["pack"].evidence if item.evidence_type == "current_context"
    ]
    assert context["evidence_pack"].metadata.current_evidence_tier is CurrentEvidenceTier.DOCUMENT_LED


def test_runtime_preserves_research_limitation_once_through_repair(monkeypatch):
    authoritative_limitation = (
        "  Independent current-country\n research   was unavailable.  "
    )
    limitation = "Independent current-country research was unavailable."
    unrelated_limitation = "  Model caveat keeps spacing.  "
    controller = _InjectedResearchController(
        ResearchResult(
            (),
            {},
            1,
            CurrentEvidenceTier.DOCUMENT_LED,
            authoritative_limitation,
        )
    )

    class ModelGateway:
        def __init__(self, api_key, model_id, *, timeout_seconds=None):
            pass

        def generate(self, *, prompt_name, payload, output_type):
            if prompt_name == "repair":
                overall_read = "The draft requires cautious review."
                limitations = (
                    "\tIndependent current-country research was   unavailable.\n",
                    unrelated_limitation,
                )
            else:
                overall_read = "This package is eligible for special treatment."
                limitations = (
                    "Independent current-country  research was unavailable.",
                    unrelated_limitation,
                )
            return output_type(
                overall_read=overall_read,
                alignment_readout="Independent current context was unavailable.",
                revision_summary=(),
                priority_areas=(),
                institutional_referral_ids=(),
                limitations=limitations,
                coverage_note="The review covers the uploaded CPF.",
            )

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicModelGateway", ModelGateway)
    services = build_runtime_services(
        production_config(ALLOW_SYNTHETIC_REGISTRY=True),
        research_controller=controller,
    )
    context = services["review_orchestrator"].run(
        {
            "assessment_id": "document-led-repair",
            "payload": {
                "country": "Benin",
                "review_stage": "finalization",
                "cpf": {"name": "benin-cpf.txt", "bytes": b"CPF text " * 20},
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "detail_level": "standard",
                "corrections": [],
            },
        },
        lambda kind, data: None,
    )

    result = context["result"]
    assert context["evidence_pack"].warnings.count(limitation) == 1
    assert result.limitations.count(limitation) == 1
    assert result.limitations == (unrelated_limitation, limitation)
    assert result.metadata.current_evidence_tier is CurrentEvidenceTier.DOCUMENT_LED
    assert result.metadata.current_evidence_limitation == limitation
    assert result.metadata.repair_count == 1
