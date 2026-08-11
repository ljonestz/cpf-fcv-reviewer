from cpf_fcv_reviewer.priority_questions import detect_priority_questions


def test_detects_questions_without_turning_statements_into_questions():
    guidance = """
    Please pay attention to regional spillovers.
    Does the results framework track geographic distribution?
    Is the partnership logic credible?
    """

    assert detect_priority_questions(guidance) == (
        "Does the results framework track geographic distribution?",
        "Is the partnership logic credible?",
    )


def test_deduplicates_questions_case_insensitively():
    guidance = "Is access addressed?\nis access addressed?"

    assert detect_priority_questions(guidance) == ("Is access addressed?",)


def test_strips_leading_bullet_markers_and_whitespace_from_questions():
    guidance = "  -  Is delivery feasible?  \n\t-Has the risk been confirmed?\t"

    assert detect_priority_questions(guidance) == (
        "Is delivery feasible?",
        "Has the risk been confirmed?",
    )
