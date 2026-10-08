"""Provider-free tests for large-package coverage: digest planning and evidence."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer import document_digest, runtime
from cpf_fcv_reviewer.contracts import (
    CurrentEvidenceTier,
    DocumentDigest,
    DocumentDigestPoint,
    DocumentRole,
)
from cpf_fcv_reviewer.document_digest import (
    DigestJob,
    digest_document,
    digest_documents,
    plan_digests,
)
from cpf_fcv_reviewer.extraction import (
    ExtractedDocument,
    ExtractedSegment,
    PackageCoverageUnavailable,
    PackageDocumentCountExceeded,
    PackageDocumentTooLarge,
    PackageDocumentUnreadable,
)
from cpf_fcv_reviewer.orchestrator import safe_failure_code
from cpf_fcv_reviewer.research_controller import ResearchResult

FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")


def document(name: str, pages: int, characters_per_page: int = 10) -> ExtractedDocument:
    return ExtractedDocument(
        name,
        tuple(
            ExtractedSegment("w" * characters_per_page, index, None, f"page {index}")
            for index in range(1, pages + 1)
        ),
        (),
    )


def digest(*points: DocumentDigestPoint, significance: str = "core") -> DocumentDigest:
    return DocumentDigest(
        document_type="Performance and Learning Review",
        significance=significance,
        summary="The PLR reviews delivery of the earlier framework.",
        key_points=points,
    )


def schema_error() -> ValidationError:
    try:
        DocumentDigest.model_validate({"significance": "unknown"})
    except ValidationError as error:
        return error
    raise AssertionError("expected a validation error")


class SequencedGateway:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append((prompt_name, payload, output_type))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


# --- planning -------------------------------------------------------------------------


def test_plan_digests_supplies_everything_when_within_budget():
    documents = (document("a", 3), document("b", 2))

    assert plan_digests(documents, direct_budget=50) == frozenset()


def test_plan_digests_selects_largest_documents_until_rest_fits():
    documents = (document("small", 1), document("large", 10), document("medium", 5))

    assert plan_digests(documents, direct_budget=60) == frozenset({1})
    assert plan_digests(documents, direct_budget=10) == frozenset({1, 2})
    assert plan_digests(documents, direct_budget=0) == frozenset({0, 1, 2})


# --- digest of one document ------------------------------------------------------------


def test_digest_document_builds_digest_and_cited_page_evidence():
    source = document("PLR.pdf", 3, characters_per_page=5000)
    gateway = SequencedGateway(
        digest(
            DocumentDigestPoint(
                point="Results lagged in the north.",
                source_evidence_ids=("package-doc-002-segment-003", "invented-id"),
            ),
            DocumentDigestPoint(
                point="Lessons on security access.",
                source_evidence_ids=("package-doc-002-segment-001",),
            ),
        )
    )

    outcome = digest_document(
        gateway, source, role=DocumentRole.PACKAGE, prefix="package", document_index=2
    )

    prompt_name, payload, output_type = gateway.calls[0]
    assert prompt_name == "document_digest"
    assert output_type is DocumentDigest
    assert len(payload["evidence"]) == 3
    assert payload["evidence"][0]["text"] == "w" * 5000
    ids = [item.evidence_id for item in outcome.evidence]
    assert ids == [
        "package-doc-002-digest",
        "package-doc-002-segment-001",
        "package-doc-002-segment-003",
    ]
    digest_item = outcome.evidence[0]
    assert digest_item.document_role is DocumentRole.PACKAGE
    assert digest_item.locator.element == "full-document digest"
    assert digest_item.locator.is_paraphrase is True
    assert "read in full (3 segments)" in digest_item.text
    assert "- Results lagged in the north. (p. 3)" in digest_item.text
    assert "invented-id" not in digest_item.text
    assert len(outcome.evidence[1].text) <= document_digest.CITED_SEGMENT_MAX_CHARACTERS
    assert "summarised as core material" in outcome.warning


def test_background_digest_points_may_omit_citations():
    gateway = SequencedGateway(
        digest(DocumentDigestPoint(point="General country history."), significance="background")
    )

    outcome = digest_document(
        gateway,
        document("History.pdf", 2),
        role=DocumentRole.CONTEXT,
        prefix="context",
        document_index=1,
    )

    assert [item.evidence_id for item in outcome.evidence] == ["context-doc-001-digest"]
    assert "- General country history." in outcome.evidence[0].text
    assert "background material" in outcome.warning


def test_digest_document_retries_schema_once_with_safe_issues():
    gateway = SequencedGateway(
        schema_error(), digest(DocumentDigestPoint(point="Point.", source_evidence_ids=()))
    )

    outcome = digest_document(
        gateway, document("A.pdf", 1), role=DocumentRole.PACKAGE, prefix="package",
        document_index=1,
    )

    assert outcome.digest is not None
    retry_payload = gateway.calls[1][1]
    assert retry_payload["schema_retry"]["issues"]
    assert all(
        set(issue) == {"loc", "type"} for issue in retry_payload["schema_retry"]["issues"]
    )


def test_digest_document_excludes_after_second_schema_failure():
    gateway = SequencedGateway(schema_error(), schema_error())

    outcome = digest_document(
        gateway, document("A.pdf", 1), role=DocumentRole.PACKAGE, prefix="package",
        document_index=1,
    )

    assert outcome.digest is None
    assert outcome.evidence == ()
    assert "could not be summarised" in outcome.warning
    assert len(gateway.calls) == 2


def test_digest_document_excludes_when_the_request_fails():
    gateway = SequencedGateway(RuntimeError("provider unavailable"))

    outcome = digest_document(
        gateway, document("A.pdf", 1), role=DocumentRole.PACKAGE, prefix="package",
        document_index=1,
    )

    assert outcome.digest is None
    assert "summary request failed" in outcome.warning


def test_digest_documents_returns_outcomes_in_job_order_and_reports_progress():
    class EchoGateway:
        def generate(self, *, prompt_name, payload, output_type):
            return digest(DocumentDigestPoint(point=payload["document_title"]))

    jobs = [
        DigestJob(document(f"doc-{index}.pdf", 1), DocumentRole.PACKAGE, "package", index)
        for index in range(1, 6)
    ]
    progress = []

    outcomes = digest_documents(
        EchoGateway(), jobs, on_complete=lambda done, total: progress.append((done, total))
    )

    assert [outcome.document_name for outcome in outcomes] == [
        f"doc-{index}.pdf" for index in range(1, 6)
    ]
    assert progress[-1] == (5, 5)


# --- runtime evidence assembly -------------------------------------------------------------


class DigestingGateway:
    def __init__(self):
        self.digested = []

    def generate(self, *, prompt_name, payload, output_type):
        assert prompt_name == "document_digest"
        self.digested.append(payload["document_title"])
        first_id = payload["evidence"][0]["evidence_id"]
        return digest(DocumentDigestPoint(point="Key point.", source_evidence_ids=(first_id,)))


def _services(monkeypatch, gateway):
    class Unused:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("cpf_fcv_reviewer.runtime.AnthropicPublicResearchGateway", Unused)
    config = {
        "TESTING": False,
        "ANTHROPIC_API_KEY": "test-key",
        "ANTHROPIC_MODEL_ID": "test-model",
        "ANTHROPIC_REVIEW_MODEL_ID": "test-review-model",
        "REGISTRY_BUNDLE_PATH": str(FIXTURE),
        "REGISTRY_BUNDLE_SHA256": sha256(FIXTURE.read_bytes()).hexdigest(),
        "ALLOW_SYNTHETIC_REGISTRY": True,
        "RESEARCH_MAX_ATTEMPTS": 1,
        "RESEARCH_ATTEMPT_TIMEOUT_SECONDS": 5.0,
        "RESEARCH_TOTAL_BUDGET_SECONDS": 10.0,
        "RESEARCH_MINIMUM_CLAIMS": 1,
        "RESEARCH_MINIMUM_PUBLISHERS": 1,
        "RESEARCH_RETRY_BACKOFF_SECONDS": 0.0,
    }
    return runtime.build_runtime_services(config, model_gateway=gateway)


def _build_evidence(services, *, package_documents=(), context_documents=(), events=None):
    build_evidence = dict(services["review_orchestrator"].steps)["build_evidence"]
    return build_evidence(
        {
            "assessment_id": "large-package",
            "_emit": (lambda kind, data: events.append((kind, data)))
            if events is not None
            else (lambda kind, data: None),
            "payload": {
                "country": "Guinea",
                "review_stage": "concept_review",
                "detail_level": "standard",
                "cpf": {"name": "cpf.pdf", "bytes": b"primary"},
                "package_documents": [],
                "context_documents": [],
                "review_focus": "",
                "corrections": [],
            },
            "primary_document": document("cpf.pdf", 30, characters_per_page=3000),
            "package_documents": tuple(package_documents),
            "context_documents": tuple(context_documents),
            "research_result": ResearchResult((), {}, 0, CurrentEvidenceTier.FULL),
        }
    )


def test_review_model_is_recorded_in_run_metadata(monkeypatch):
    context = _build_evidence(_services(monkeypatch, DigestingGateway()))

    assert context["evidence_pack"].metadata.model_id == "test-review-model"


def test_primary_is_supplied_in_full(monkeypatch):
    context = _build_evidence(_services(monkeypatch, DigestingGateway()))

    primary = [
        item
        for item in context["evidence_pack"].evidence
        if item.document_role is DocumentRole.PRIMARY
    ]
    assert len(primary) == 30
    assert all(len(item.text) == 3000 for item in primary)


def test_oversized_package_digests_largest_document_and_discloses_it(monkeypatch):
    monkeypatch.setattr(runtime, "PACKAGE_DIRECT_MAX_CHARACTERS", 100)
    gateway = DigestingGateway()
    events = []
    context = _build_evidence(
        _services(monkeypatch, gateway),
        package_documents=(document("PLR.pdf", 4, 10), document("BOSIB.pdf", 20, 10)),
        events=events,
    )

    assert gateway.digested == ["BOSIB.pdf"]
    package_ids = [
        item.evidence_id
        for item in context["evidence_pack"].evidence
        if item.document_role is DocumentRole.PACKAGE
    ]
    assert package_ids[:4] == [f"package-doc-001-segment-{i:03d}" for i in range(1, 5)]
    assert package_ids[4:] == ["package-doc-002-digest", "package-doc-002-segment-001"]
    assert ("package_plan", {
        "package_documents": 2,
        "package_summarised": 1,
        "context_documents": 0,
        "context_summarised": 0,
    }) in events
    assert any(kind == "document_digest_progress" for kind, _data in events)
    assert any(
        "BOSIB.pdf: read in full (20 segments) and summarised" in warning
        for warning in context["evidence_pack"].warnings
    )
    assert runtime._incomplete_document_roles(context) == frozenset({DocumentRole.PACKAGE})


def test_small_package_is_supplied_verbatim_without_digest_calls(monkeypatch):
    gateway = DigestingGateway()
    context = _build_evidence(
        _services(monkeypatch, gateway),
        package_documents=(document("PLR.pdf", 4),),
    )

    assert gateway.digested == []
    assert runtime._incomplete_document_roles(context) == frozenset()


def test_large_context_analytics_are_digested_as_context(monkeypatch):
    monkeypatch.setattr(runtime, "CONTEXT_DIRECT_MAX_CHARACTERS", 10)
    gateway = DigestingGateway()
    context = _build_evidence(
        _services(monkeypatch, gateway),
        context_documents=(document("Background.pdf", 5),),
    )

    assert gateway.digested == ["Background.pdf"]
    context_items = [
        item
        for item in context["evidence_pack"].evidence
        if item.document_role is DocumentRole.CONTEXT
    ]
    assert context_items[0].evidence_id == "context-doc-001-digest"


# --- failure categories ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "code"),
    (
        (PackageDocumentCountExceeded("x"), "package_document_count_exceeded"),
        (PackageDocumentTooLarge("x"), "package_document_too_large"),
        (PackageDocumentUnreadable("x"), "package_document_unreadable"),
        (PackageCoverageUnavailable("x"), "package_coverage_unavailable"),
    ),
)
def test_package_failures_have_specific_safe_codes(error, code):
    assert safe_failure_code(error) == code


def test_oversized_package_document_reports_too_large(monkeypatch):
    def too_large(*args, **kwargs):
        raise runtime.ExtractionLimitExceeded("bound")

    monkeypatch.setattr(runtime, "extract_document", too_large)

    with pytest.raises(PackageDocumentTooLarge):
        runtime._extract_optional_uploads(
            ({"name": "annex.txt", "bytes": b"text"},), strict_package=True
        )


# --- frontend contract ----------------------------------------------------------------------

APP_JS = Path("src/cpf_fcv_reviewer/static/app.js").read_text(encoding="utf-8")
INDEX_HTML = Path("src/cpf_fcv_reviewer/templates/index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "code",
    (
        "package_document_count_exceeded",
        "package_document_too_large",
        "package_document_unreadable",
    ),
)
def test_frontend_explains_each_package_failure(code):
    assert f"  {code}: " in APP_JS


def test_frontend_mirrors_server_upload_limits_before_submission():
    assert f"const PACKAGE_MAX_DOCUMENTS = {runtime.PACKAGE_MAX_DOCUMENTS};" in APP_JS
    assert "const UPLOAD_MAX_BYTES = 80 * 1024 * 1024;" in APP_JS
    assert "|| uploadLimitExceeded;" in APP_JS
    assert 'id="upload-summary"' in INDEX_HTML


def test_frontend_reports_package_plan_and_digest_progress():
    assert 'source.addEventListener("package_plan"' in APP_JS
    assert 'source.addEventListener("document_digest_progress"' in APP_JS
