import pytest

from cpf_fcv_reviewer.validators import assert_no_unsupported_policy_claims


@pytest.mark.parametrize(
    "text",
    [
        "The package is eligible for the PRA.",
        "OP 7.30 is triggered.",
        "The CPF complies with PC14.",
        "The FCV Envelope criteria are met.",
        "OPCS has cleared this approach.",
    ],
)
def test_determination_language_is_blocked(text):
    with pytest.raises(ValueError, match="Unsupported policy or determination"):
        assert_no_unsupported_policy_claims(text, set())


@pytest.mark.parametrize(
    "text",
    [
        "THE PACKAGE IS ELIGIBLE FOR THE PRA.",
        "OP 7.30 IS TRIGGERED.",
        "The CPF COMPLIES WITH PC14.",
    ],
)
def test_determination_language_is_case_insensitive(text):
    with pytest.raises(ValueError, match="Unsupported policy or determination"):
        assert_no_unsupported_policy_claims(text, set())


@pytest.mark.parametrize(
    "text",
    [
        "The package discusses ineligible financing.",
        "The word triggeredly is not a determination.",
        "Compliance work is still under discussion.",
    ],
)
def test_determination_patterns_do_not_match_obvious_substrings(text):
    assert_no_unsupported_policy_claims(text, set())
