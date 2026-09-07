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


def test_repair_start_exposes_only_safe_validation_metadata():
    events = []
    captured = {}
    sensitive_message = "Sensitive evidence excerpt: operation quartz-739."
    sensitive_id = "assessment-secret-123"

    def validate(context):
        context["validation_issues"] = [
            {
                "code": "stage_overreach",
                "message": sensitive_message,
                "assessment_id": sensitive_id,
            }
        ]
        return context

    def repair(context, issues):
        captured["issues"] = issues
        context["validation_issues"] = []
        return context

    ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    ).run({}, lambda kind, data: events.append((kind, data)))

    repair_event = next(data for kind, data in events if kind == "repair_start")
    assert captured["issues"][0]["message"] == sensitive_message
    assert repair_event == {"issue_count": 1, "codes": ["stage_overreach"]}
    assert sensitive_message not in str(repair_event)
    assert sensitive_id not in str(repair_event)


def test_failed_repair_emits_terminal_failure_without_completion():
    events = []
    sensitive_message = "Sensitive evidence excerpt: operation quartz-739."

    def validate(context):
        context["validation_issues"] = [
            {
                "code": "stage_length_overreach",
                "message": sensitive_message,
            },
            {
                "code": "prohibited_policy_language",
                "message": "Sensitive forbidden phrase.",
            },
        ]
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=lambda context, issues: context,
    )

    with pytest.raises(ValueError, match="only repair"):
        orchestrator.run({}, lambda kind, data: events.append((kind, data)))

    repair_failure = next(data for kind, data in events if kind == "repair_failed")
    assert repair_failure == {
        "issue_count": 2,
        "codes": ["stage_length_overreach", "prohibited_policy_language"],
    }
    assert sensitive_message not in str(repair_failure)
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


def test_advisory_only_issues_do_not_fail_the_run():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator

    events = []

    def emit(name, data):
        events.append((name, data))

    def validate(context):
        context["validation_issues"] = [
            {
                "code": "missing_current_context_support",
                "message": "advisory",
                "severity": "advisory",
            }
        ]
        return context

    def repair(context, issues):
        raise AssertionError("repair must not run for advisory-only issues")

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    orchestrator.run({}, emit)
    names = [name for name, _ in events]
    assert "run_complete" in names
    assert "run_failed" not in names
    assert "repair_start" not in names


def test_fatal_issue_still_repairs_and_can_fail():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator

    events = []

    def emit(name, data):
        events.append((name, data))

    def validate(context):
        context["validation_issues"] = [
            {"code": "stage_overreach", "message": "fatal", "severity": "fatal"}
        ]
        return context

    def repair(context, issues):
        context["validation_issues"] = [
            {"code": "stage_overreach", "message": "fatal", "severity": "fatal"}
        ]
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    try:
        orchestrator.run({}, emit)
    except ValueError:
        pass
    names = [name for name, _ in events]
    assert "repair_start" in names
    assert "run_failed" in names


def test_repair_receives_only_fatal_issues():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator

    received = []

    def emit(name, data):
        pass

    def validate(context):
        context["validation_issues"] = [
            {"code": "stage_overreach", "message": "f", "severity": "fatal"},
            {"code": "missing_current_context_support", "message": "a", "severity": "advisory"},
        ]
        return context

    def repair(context, issues):
        received.extend(issues)
        context["validation_issues"] = []
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    orchestrator.run({}, emit)
    codes = [i["code"] for i in received]
    assert codes == ["stage_overreach"]


@pytest.mark.parametrize("fatal_code", [None, "unknown_evidence", "missing_registry_support"])
def test_actual_length_advisory_completes_without_repair_but_evidence_errors_block(fatal_code):
    from dataclasses import asdict

    from cpf_fcv_reviewer.validators import ValidationIssue, validate_stage_behavior

    issues = [asdict(issue) for issue in validate_stage_behavior(
        "finalization", " ".join(["word"] * 61),
    )]
    if fatal_code:
        issues.append(asdict(ValidationIssue(fatal_code, "Invalid evidence link.")))
    events = []
    repairs = []

    def validate(context):
        context["validation_issues"] = issues
        return context

    def repair(context, fatal_issues):
        repairs.extend(fatal_issues)
        return context

    runner = ReviewOrchestrator(steps=(("validate", validate),), repair=repair)
    if fatal_code:
        with pytest.raises(ValueError):
            runner.run({}, lambda name, data: events.append(name))
        assert [issue["code"] for issue in repairs] == [fatal_code]
        assert "run_failed" in events
    else:
        runner.run({}, lambda name, data: events.append(name))
        assert repairs == []
        assert "advisory_notice" in events
        assert "run_complete" in events
