from hashlib import sha256

import pytest

from cpf_fcv_reviewer.prompts import load_prompt, prompt_hash


def test_review_prompt_prohibits_determinations_and_policy_paraphrase():
    prompt = load_prompt("review")
    for phrase in (
        "must not determine",
        "Do not paraphrase policy or guidance",
        "approved registry entry identifiers",
        "Limited FCV diagnostic-framing assessment",
        "page, heading, table, figure, or paragraph",
        "Never invent a page",
        "English",
    ):
        assert phrase in prompt


@pytest.mark.parametrize("name", ["diagnostic_map", "review", "repair"])
def test_prompts_are_versioned_and_hash_matches_loaded_content(name):
    prompt = load_prompt(name)

    assert prompt.startswith("Version: 1.0.0\n")
    assert prompt_hash(name) == sha256(prompt.encode("utf-8")).hexdigest()
    assert len(prompt_hash(name)) == 64


@pytest.mark.parametrize(
    "name",
    [
        "../review",
        "review.md",
        "missing",
        "",
    ],
)
def test_prompt_loader_rejects_unknown_or_unsafe_names(name):
    with pytest.raises(ValueError, match="Unknown prompt"):
        load_prompt(name)


def test_diagnostic_map_prompt_preserves_evidence_boundaries():
    prompt = load_prompt("diagnostic_map")

    assert "Preserve every supplied material evidence identifier exactly once" in prompt
    assert "Do not convert contextual background into a programming requirement" in prompt
