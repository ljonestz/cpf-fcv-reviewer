from __future__ import annotations

from .contracts import EvidencePack, ReviewResult
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

    def review(self, evidence_pack: EvidencePack) -> ReviewResult:
        stage = evidence_pack.metadata.review_stage
        try:
            stage_rule = STAGE_RULES[stage]
        except KeyError as exc:
            raise ValueError(f"Unsupported review stage: {stage}") from exc
        return self.gateway.generate(
            prompt_name="review",
            payload={
                "evidence_pack": evidence_pack.model_dump(mode="json"),
                "stage_rule": stage_rule,
            },
            output_type=ReviewResult,
        )
