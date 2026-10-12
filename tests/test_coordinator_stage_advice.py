"""Stage and coordinator guidance must reach the bounded analytical review."""
import inspect

from cpf_fcv_reviewer.prompts import load_prompt
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.review_profiles import STAGE_PROFILES


def test_cmu_questions_have_a_separate_review_input():
    assert "review_questions" in inspect.signature(ReviewEngine.review).parameters


def test_stage_specific_destinations_are_explicit():
    assert "meeting" in STAGE_PROFILES["roc_oc"].instruction.casefold()
    assert "before finalisation" in STAGE_PROFILES["roc_oc"].instruction.casefold()


def test_core_prompt_keeps_comparative_evidence_and_corporate_scope():
    prompt = load_prompt("review").casefold()
    for text in [
        "drivers_priorities", "actions_commitment", "program_implications",
        "if_then_calibration", "previous cpf", "completion and learning review",
        "no compliance rating", "recommendation destination",
    ]:
        assert text in prompt


def test_email_style_is_not_forced_into_the_four_questions():
    prompt = load_prompt("review").casefold()
    assert "one email comment per question" in prompt


def test_questions_and_override_reach_review_but_origin_is_owned(make_valid_result):
    from cpf_fcv_reviewer.contracts import (
        ContextFraming,
        DocumentRole,
        EvidencePack,
        ReviewDraft,
    )

    result, evidence = make_valid_result
    draft = ReviewDraft.model_validate({
        **result.model_dump(exclude={"metadata", "document_coverage"}),
        "coverage_note": result.document_coverage.coverage_note,
        "proposed_context_framing": ContextFraming(
            category="at_risk", rationale="Diagnostic supports prevention framing.",
            confidence="low", evidence_ids=("ev-1",), origin="coordinator_override",
        ),
    })
    pack = EvidencePack(
        metadata=result.metadata,
        evidence=(evidence["ev-1"].model_copy(update={"document_role": DocumentRole.PRIMARY}),),
        diagnostic_entries=(),
    )

    class Gateway:
        def generate(self, **kwargs):
            self.payload = kwargs["payload"]
            return draft

    gateway = Gateway()
    reviewed = ReviewEngine(gateway).review(pack, review_questions="Is selectivity clear?")
    assert gateway.payload["review_questions"] == "Is selectivity clear?"
    assert reviewed.proposed_context_framing.origin == "model_proposed"
    reviewed = ReviewEngine(gateway).review(pack, framing_override="in_crisis")
    assert gateway.payload["framing_override"] == "in_crisis"
    assert reviewed.proposed_context_framing.category == "in_crisis"
    assert reviewed.proposed_context_framing.origin == "coordinator_override"
