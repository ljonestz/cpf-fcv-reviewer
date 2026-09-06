from cpf_fcv_reviewer.validators import ValidationIssue


def test_validation_issue_defaults_to_fatal_severity():
    issue = ValidationIssue("stage_overreach", "example")
    assert issue.severity == "fatal"


def test_missing_current_context_support_is_advisory():
    issue = ValidationIssue(
        "missing_current_context_support", "example", severity="advisory"
    )
    assert issue.severity == "advisory"
