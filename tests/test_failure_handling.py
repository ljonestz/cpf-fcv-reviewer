import logging
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import ReviewDraft
from cpf_fcv_reviewer.extraction import (
    DiagnosticCoverageUnavailable,
    DocumentUnreadable,
    require_readable_primary,
)
from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator, safe_failure_code
from cpf_fcv_reviewer.review_engine import ReviewSchemaUnavailable
from cpf_fcv_reviewer.registry import RegistryUnavailable
from cpf_fcv_reviewer.research_controller import (
    InsufficientResearch,
    MalformedResearch,
    ResearchConfigurationError,
    ResearchProviderFailure,
    ResearchSourceRejected,
    ResearchTimeout,
)
from cpf_fcv_reviewer.routes import run_assessment


def review_schema_failure() -> ReviewSchemaUnavailable:
    with pytest.raises(ValidationError) as first:
        ReviewDraft.model_validate(
            {
                "overall_read": {
                    "secret": "FIRST-ATTEMPT-SECRET",
                    "model": "MODEL-ID-SECRET",
                    "document": "DOCUMENT-TEXT-SECRET",
                }
            }
        )
    with pytest.raises(ValidationError) as second:
        ReviewDraft.model_validate(
            {"unknown_secret_field": "SECOND-ATTEMPT-SECRET"}
        )
    return ReviewSchemaUnavailable(first.value, second.value)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), "model_timeout"),
        (RegistryUnavailable(), "registry_unavailable"),
        (DocumentUnreadable(), "document_unreadable"),
        (DiagnosticCoverageUnavailable(), "diagnostic_coverage_unavailable"),
        (ResearchTimeout(), "research_timeout"),
        (ResearchProviderFailure(), "research_provider_failed"),
        (MalformedResearch(), "research_malformed"),
        (ResearchConfigurationError(), "research_configuration"),
        (ResearchSourceRejected(), "research_source_rejected"),
        (InsufficientResearch(), "research_insufficient"),
        (RuntimeError(), "review_failed"),
    ],
)
def test_safe_failure_code_is_stable(error, expected):
    assert safe_failure_code(error) == expected


def test_unreadable_primary_uses_dedicated_exception():
    with pytest.raises(DocumentUnreadable):
        require_readable_primary(type("Doc", (), {"segments": (), "warnings": ()})())


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (TimeoutError("request abc failed"), "model_timeout"),
        (DiagnosticCoverageUnavailable("threshold detail"), "diagnostic_coverage_unavailable"),
        (
            RegistryUnavailable("registry path C:/secret unavailable"),
            "registry_unavailable",
        ),
        (ResearchTimeout("provider detail"), "research_timeout"),
        (ResearchProviderFailure("provider detail"), "research_provider_failed"),
        (MalformedResearch("provider detail"), "research_malformed"),
        (ResearchConfigurationError("provider detail"), "research_configuration"),
        (ResearchSourceRejected("provider detail"), "research_source_rejected"),
        (InsufficientResearch("provider detail"), "research_insufficient"),
    ],
)
def test_failure_event_exposes_only_a_stable_error_code(error, expected_code):
    events = []

    def fail(context):
        context["result"] = "partial model prose"
        raise error

    context = {}
    orchestrator = ReviewOrchestrator(
        steps=(("review", fail),),
        repair=lambda ctx, issues: ctx,
    )

    with pytest.raises(type(error)):
        orchestrator.run(context, lambda kind, data: events.append((kind, data)))

    assert events[-1] == ("run_failed", {"error": expected_code})
    assert "partial model prose" not in context.values()
    assert context == {"status": "failed"}


def test_review_schema_failure_event_retains_only_safe_diagnostics():
    events = []
    context = {"result": "partial model prose"}
    error = review_schema_failure()

    def fail(_context):
        raise error

    orchestrator = ReviewOrchestrator(
        steps=(("review", fail),),
        repair=lambda ctx, issues: ctx,
    )

    with pytest.raises(ReviewSchemaUnavailable):
        orchestrator.run(context, lambda kind, data: events.append((kind, data)))

    data = events[-1][1]
    assert events[-1][0] == "run_failed"
    assert data["error"] == "review_schema_invalid"
    assert safe_failure_code(error) == "review_schema_invalid"
    assert data["schema_diagnostics"] == error.safe_diagnostics
    serialized = repr(data)
    assert "MODEL-ID-SECRET" not in serialized
    assert "DOCUMENT-TEXT-SECRET" not in serialized
    assert "Input should be a valid string" not in serialized
    assert "Extra inputs are not permitted" not in serialized
    for unsafe_key in ("msg", "input", "ctx"):
        assert unsafe_key not in serialized
    assert "FIRST-ATTEMPT-SECRET" not in serialized
    assert "SECOND-ATTEMPT-SECRET" not in serialized
    assert "unknown_secret_field" not in serialized
    assert context == {"status": "failed"}


def test_invalid_repair_is_attempted_once_then_fails_without_partial_result():
    events = []
    repair_calls = []
    context = {}

    def validate(ctx):
        ctx["result"] = "partial model prose"
        ctx["validation_issues"] = ["invalid structure"]
        return ctx

    def repair(ctx, issues):
        repair_calls.append(tuple(issues))
        ctx["result"] = "still invalid model prose"
        ctx["validation_issues"] = ["still invalid"]
        return ctx

    orchestrator = ReviewOrchestrator(steps=(("validate", validate),), repair=repair)

    with pytest.raises(ValueError, match="only repair"):
        orchestrator.run(context, lambda kind, data: events.append((kind, data)))

    assert repair_calls == [("invalid structure",)]
    assert events[-1] == ("run_failed", {"error": "review_failed"})
    assert context == {"status": "failed"}


def test_frontend_uses_only_safe_failure_codes():
    javascript = Path("src/cpf_fcv_reviewer/static/app.js").read_text(encoding="utf-8")
    assert "failureLabels[data.error]" in javascript
    assert "diagnostic_coverage_unavailable" in javascript
    assert "review_schema_invalid" in javascript
    assert (
        "The uploaded diagnostic could not be assessed in full. Upload a shorter "
        "or text-searchable version, or start a new review without it."
    ) in javascript
    assert "data.message" not in javascript
    assert "data.schema_diagnostics" not in javascript


def test_background_failure_logs_only_exception_type_and_http_status(caplog):
    secret = "TOP-SECRET-PROVIDER-DETAIL"

    class ProviderFailure(RuntimeError):
        status_code = 404

    class TransportFailure(RuntimeError):
        pass

    class FailingOrchestrator:
        def run(self, context, emit):
            try:
                raise TransportFailure(secret)
            except TransportFailure as exc:
                raise ProviderFailure(secret) from exc

    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    app.extensions["review_orchestrator"] = FailingOrchestrator()
    created = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Benin",
            "review_stage": "finalization",
            "cpf": (BytesIO(b"Readable public CPF text " * 20), "public-cpf.txt"),
        },
        content_type="multipart/form-data",
    ).get_json()

    with caplog.at_level(logging.ERROR):
        run_assessment(app, created["assessment_id"])

    assert "ProviderFailure" in caplog.text
    assert "cause_chain=TransportFailure" in caplog.text
    assert "status_code=404" in caplog.text
    assert secret not in caplog.text


def test_background_schema_failure_emits_and_logs_safe_diagnostics(caplog):
    error = review_schema_failure()

    class FailingOrchestrator:
        def run(self, context, emit):
            raise error

    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    app.extensions["review_orchestrator"] = FailingOrchestrator()
    created = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Benin",
            "review_stage": "finalization",
            "cpf": (BytesIO(b"Readable public CPF text " * 20), "public-cpf.txt"),
        },
        content_type="multipart/form-data",
    ).get_json()

    with caplog.at_level(logging.ERROR):
        run_assessment(app, created["assessment_id"])

    failure_event = None
    while event := app.extensions["session_store"].next_event(
        created["assessment_id"]
    ):
        if event["type"] == "run_failed":
            failure_event = event
    assert failure_event is not None
    assert failure_event["data"]["error"] == "review_schema_invalid"
    assert failure_event["data"]["schema_diagnostics"] == error.safe_diagnostics
    assert "schema_diagnostics=" in caplog.text
    assert '"attempt":1' in caplog.text
    assert '"attempt":2' in caplog.text
    assert "MODEL-ID-SECRET" not in caplog.text
    assert "DOCUMENT-TEXT-SECRET" not in caplog.text
    assert "Input should be a valid string" not in caplog.text
    assert "Extra inputs are not permitted" not in caplog.text
    for unsafe_key in ('"msg"', '"input"', '"ctx"'):
        assert unsafe_key not in caplog.text
    assert "FIRST-ATTEMPT-SECRET" not in caplog.text
    assert "SECOND-ATTEMPT-SECRET" not in caplog.text
    assert "unknown_secret_field" not in caplog.text
    state = app.extensions["session_store"].get(created["assessment_id"]).payload
    assert state["failure_code"] == "review_schema_invalid"
    assert "schema_diagnostics" not in state
