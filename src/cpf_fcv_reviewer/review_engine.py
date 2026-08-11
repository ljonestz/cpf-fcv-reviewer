from __future__ import annotations

from .contracts import EvidencePack, ReviewDraft, ReviewResult
from .model_gateway import ModelGateway

STAGE_RULES = {
    "early_drafting": (
        "May challenge strategic framing, selectivity, causal logic, "
        "outcome structure, and theory of change."
    ),
    "concept_review": (
        "Prioritize diagnostic alignment, strategic choices, outcome "
        "architecture, One WBG roles, partnerships, and results logic."
    ),
    "decision_review": (
        "Focus on specific revisions to objectives, results, risks, "
        "implementation arrangements, calibration, and decisions."
    ),
    "roc_oc": (
        "Focus on specific revisions to objectives, results, risks, "
        "implementation arrangements, calibration, and decisions."
    ),
    "finalization": (
        "Limit advice to targeted, high-value edits, factual corrections, "
        "caveats, indicator refinements, and genuine confirmation needs."
    ),
    "response_to_comments": (
        "Link each option to the prior comment and document location; use "
        "accept, partially accept, explain, or verify options."
    ),
}


class ReviewEngine:
    def __init__(self, gateway: ModelGateway):
        self.gateway = gateway

    def review(
        self,
        evidence_pack: EvidencePack,
        *,
        priority_questions: tuple[str, ...] = (),
    ) -> ReviewResult:
        stage = evidence_pack.metadata.review_stage
        try:
            stage_rule = STAGE_RULES[stage]
        except KeyError as exc:
            raise ValueError(f"Unsupported review stage: {stage}") from exc
        draft = self.gateway.generate(
            prompt_name="review",
            payload={
                "evidence_pack": evidence_pack.model_dump(mode="json"),
                "stage_rule": stage_rule,
                "priority_questions": priority_questions,
            },
            output_type=ReviewDraft,
        )
        return ReviewResult(metadata=evidence_pack.metadata, **draft.model_dump())

    def repair(
        self,
        result: ReviewResult,
        issues: list[dict],
        *,
        forbidden_phrases: tuple[str, ...] = (),
    ) -> ReviewResult:
        draft = self.gateway.generate(
            prompt_name="repair",
            payload={
                "draft": result.model_dump(mode="json", exclude={"metadata"}),
                "validation_issues": issues,
                "forbidden_phrases": forbidden_phrases,
            },
            output_type=ReviewDraft,
        )
        metadata = result.metadata.model_copy(update={"repair_count": 1})
        return ReviewResult(metadata=metadata, **draft.model_dump())
