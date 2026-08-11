import pytest

from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator


class FakeStep:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, context):
        context[self.name] = self.value
        return context


def test_one_run_reports_real_internal_step_order():
    events = []
    orchestrator = ReviewOrchestrator(
        steps=(
            ("extract", FakeStep("extract", True)),
            ("resolve_sources", FakeStep("sources", True)),
            ("build_evidence", FakeStep("evidence", True)),
            ("map", FakeStep("map", True)),
            ("review", FakeStep("review", True)),
            ("validate", FakeStep("validated", True)),
            ("render", FakeStep("rendered", True)),
        ),
        repair=lambda context, issues: context,
    )

    result = orchestrator.run({}, lambda kind, data: events.append((kind, data)))

    assert [data["step"] for kind, data in events if kind == "step_start"] == [
        "extract",
        "resolve_sources",
        "build_evidence",
        "map",
        "review",
        "validate",
        "render",
    ]
    assert events[-1] == ("run_complete", {"repair_count": 0})
    assert result["rendered"] is True


def test_repair_runs_at_most_once():
    attempts = []

    def validate(context):
        context["validation_issues"] = [] if context.get("repaired") else ["bad"]
        return context

    def repair(context, issues):
        attempts.append(tuple(issues))
        context["repaired"] = True
        context["validation_issues"] = []
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )

    orchestrator.run({}, lambda *_: None)

    assert attempts == [("bad",)]


def test_failed_repair_emits_terminal_failure_without_completion():
    events = []

    def validate(context):
        context["validation_issues"] = ["still bad"]
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=lambda context, issues: context,
    )

    with pytest.raises(ValueError, match="only repair"):
        orchestrator.run({}, lambda kind, data: events.append((kind, data)))

    assert events[-1][0] == "run_failed"
    assert not any(kind == "run_complete" for kind, _ in events)
