from cpf_fcv_reviewer.contracts import PriorityQuestionResponse
from cpf_fcv_reviewer.validators import validate_priority_questions


def response(question_id, question):
    return PriorityQuestionResponse(
        question_id=question_id,
        question=question,
        direct_answer="The supplied evidence does not confirm it.",
        evidence_ids=(),
        confidence="low",
        limitation="Confirmation is needed from the country team.",
    )


def test_confirmed_question_requires_exactly_one_response(make_valid_result):
    result, _ = make_valid_result
    result = result.model_copy(
        update={
            "priority_question_responses": (
                response("pq-1", "Is the partnership logic credible?"),
            )
        }
    )

    issues = validate_priority_questions(
        (
            "Does the results framework track geographic distribution?",
            "Is the partnership logic credible?",
        ),
        result,
    )

    assert {issue.code for issue in issues} == {"missing_priority_response"}


def test_duplicate_response_to_confirmed_question_is_rejected(make_valid_result):
    result, _ = make_valid_result
    question = "Is the partnership logic credible?"
    result = result.model_copy(
        update={
            "priority_question_responses": (
                response("pq-1", question),
                response("pq-2", question),
            )
        }
    )

    issues = validate_priority_questions((question,), result)

    assert {issue.code for issue in issues} == {"duplicate_priority_response"}
