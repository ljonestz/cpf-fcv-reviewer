from pathlib import Path

import pytest

from cpf_fcv_reviewer.extraction import DocumentUnreadable, require_readable_primary
from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator, safe_failure_code
from cpf_fcv_reviewer.registry import RegistryUnavailable


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), "model_timeout"),
        (RegistryUnavailable(), "registry_unavailable"),
        (DocumentUnreadable(), "document_unreadable"),
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
        (
            RegistryUnavailable("registry path C:/secret unavailable"),
            "registry_unavailable",
        ),
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
    assert "data.message" not in javascript
