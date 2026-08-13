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


def test_orchestrator_injects_private_emitter_and_removes_it_after_success():
    seen = {}

    def step(context):
        seen["emit"] = context["_emit"]
        context["_emit"]("sub_event", {"ok": True})
        return context

    events = []
    result = ReviewOrchestrator(
        steps=(("research", step),),
        repair=lambda context, issues: context,
    ).run({}, lambda kind, data: events.append((kind, data)))

    assert callable(seen["emit"])
    assert ("sub_event", {"ok": True}) in events
    assert "_emit" not in result


def test_orchestrator_removes_private_emitter_after_failure():
    context = {}

    def step(current_context):
        assert callable(current_context["_emit"])
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        ReviewOrchestrator(
            steps=(("research", step),),
            repair=lambda current_context, issues: current_context,
        ).run(context, lambda *_: None)

    assert "_emit" not in context
