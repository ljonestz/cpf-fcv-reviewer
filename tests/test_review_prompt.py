from cpf_fcv_reviewer.prompts import load_prompt


def test_review_prompt_states_tiered_current_context_influence():
    prompt = load_prompt("review").casefold()
    assert "verify before use" in prompt
    assert "partially verified" in prompt
    assert "unverified" in prompt
    assert "context only" in prompt or "context-only" in prompt
