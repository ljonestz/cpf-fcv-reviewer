import pytest

from cpf_fcv_reviewer.prompts import load_prompt


def normalize_whitespace(content: str) -> str:
    return " ".join(content.split())


@pytest.mark.parametrize("name", ["review", "repair"])
def test_prompts_require_source_backed_numeric_targets_and_scoped_options(name):
    prompt = normalize_whitespace(load_prompt(name))

    for phrase in (
        "numeric baselines, targets, quotas, beneficiary counts, or financing amounts",
        "only when the exact value is stated in supplied evidence",
        "Never invent a number",
        "indicator, baseline, target-setting method, or disaggregation",
        "source-supported commitment",
        "feasible option for expert consideration",
        "do not write that IDA, IFC, MIGA",
        "Do not weaken every action",
    ):
        assert phrase in prompt


def test_review_prompt_narrows_gaps_and_recommendations_to_supported_concise_actions():
    prompt = normalize_whitespace(load_prompt("review"))

    for phrase in (
        "Before identifying a gap, state what the CPF or supplied package already provides",
        "including existing roles, responsibilities, mechanisms, safeguards, "
        "indicators, or targets",
        "identify only the specific remaining gap or ambiguity supported by evidence",
        "Do not describe roles as missing when the CPF already assigns them",
        "Keep recommended_action concise, specific, and forward-looking",
        "avoid repeating the diagnosis, evidence summary, or why_it_matters",
        "Use the shortest stage-appropriate wording",
    ):
        assert phrase in prompt


@pytest.mark.parametrize("name", ["review", "repair"])
def test_review_and_repair_prompts_bind_temporal_claims_to_assessment_and_dated_support(name):
    prompt = normalize_whitespace(load_prompt(name))

    for phrase in (
        "assessment_as_of",
        "Distinguish source publication date from event date",
        "after the RRA does not by itself establish the present status",
        "a verified quote confirms only the quoted passage",
        "not comprehensive or current",
        "state that present status is unestablished",
        "reduced current-evidence tier",
        "Do not impose a fixed age cutoff",
        "arbitrary freshness claim",
    ):
        assert phrase in prompt


def test_repair_prompt_limits_grounding_edits_to_flagged_content_and_preserves_valid_priorities():
    prompt = normalize_whitespace(load_prompt("repair"))

    for phrase in (
        "only to the flagged content",
        "preserve valid sourced values elsewhere",
        "preserve a source-supported commitment",
        "correct only unsupported language",
        "preserve valid role content elsewhere",
        "preserve these qualifications",
        "do not globally rewrite unrelated text",
        "Retain every original priority_area_id, its order and linked revision-summary entry",
    ):
        assert phrase in prompt


def test_follow_on_prompt_reuses_review_date_and_does_not_amplify_unsupported_detail():
    prompt = normalize_whitespace(load_prompt("follow_on"))

    for phrase in (
        "review.metadata.created_at",
        "assessment date",
        "Distinguish source publication date from event date",
        "after the RRA does not by itself establish the present status",
        "a verified quote confirms only the quoted passage",
        "not comprehensive or current",
        "numeric baselines, targets, quotas, beneficiary counts, or financing amounts",
        "Never invent a number",
        "Do not treat the completed review as primary evidence",
        "do not amplify an unsupported target or commitment",
        "Keep recommendations concise",
    ):
        assert phrase in prompt
