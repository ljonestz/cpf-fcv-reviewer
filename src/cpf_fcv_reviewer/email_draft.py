"""Synthesize an unsigned peer-review email from validated analytical findings."""

from __future__ import annotations

import json
import re

from .contracts import PeerEmailDraft, ReviewResult
from .review_profiles import STAGE_PROFILES
from .validators import (
    assert_no_unsupported_policy_claims,
    result_text,
    validate_stage_behavior,
)

_CLOSING = "We hope these comments are useful and look forward to the discussion."
_SIGNATURE = re.compile(
    r"(?:\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s*$)|"
    r"(?im:^\s*(?:signature|signed by|kind regards|best regards|sincerely)\b)|"
    r"\bShubham(?:\s+on behalf[^\n]*)?\s*$"
)
_NUMBERS = re.compile(r"\b\d+(?:[.,]\d+)*\b")


def render_peer_email(draft: PeerEmailDraft) -> str:
    parts = ["Dear colleagues,", draft.opening]
    previous_tier = None
    for comment in draft.comments:
        if comment.tier is not None and comment.tier != previous_tier:
            parts.append(
                "Tier 1: Issues for the review meeting"
                if comment.tier == "tier_1" else "Tier 2: Additional guidance for the team"
            )
            previous_tier = comment.tier
        parts.extend((comment.heading, comment.text))
    parts.append(_CLOSING)
    return "\n\n".join(parts)


def generate_peer_email(
    result: ReviewResult,
    gateway,
    *,
    review_questions: str = "",
    follow_through: dict | None = None,
    style_entries=(),
    prohibited_terms=frozenset(),
) -> PeerEmailDraft:
    stage_profile = STAGE_PROFILES[result.metadata.review_stage]
    # Synthesis gets reviewed findings, not raw CPF packages or previous emails.
    payload = {
        "review_stage": result.metadata.review_stage,
        "stage_profile": {
            "instruction": stage_profile.instruction,
            "allowed_scales": [scale.value for scale in stage_profile.allowed_scales],
            "max_immediate_insertion_words": stage_profile.max_immediate_insertion_words,
        },
        "review_questions": review_questions[:4000],
        "validated_findings": {
            "overall_read": result.overall_read,
            "alignment_readout": result.alignment_readout,
            "strategy_readout": result.strategy_readout,
            "core_findings": [item.model_dump(mode="json") for item in result.core_findings],
            "priorities": [item.model_dump(mode="json") for item in result.priority_areas],
            "context_framing": (
                result.proposed_context_framing.model_dump(mode="json")
                if result.proposed_context_framing is not None else None
            ),
            "limitations": result.limitations,
        },
        "follow_through": follow_through,
        "approved_style_examples": [
            {"entry_id": entry.entry_id, "text": entry.approved_text}
            for entry in style_entries
        ],
    }
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 250_000:
        raise ValueError("Email synthesis exceeds the safe input budget.")
    draft = gateway.generate(prompt_name="peer_email", payload=payload, output_type=PeerEmailDraft)
    linked_ids = tuple(
        key for comment in draft.comments for key in comment.priority_area_ids
    )
    if linked_ids != tuple(area.priority_area_id for area in result.priority_areas):
        raise ValueError("Email priorities must preserve the validated review order.")
    tiers = {comment.tier for comment in draft.comments}
    if tiers and tiers not in ({None}, {"tier_1", "tier_2"}):
        raise ValueError("Use tiers only for a meaningful meeting/guidance distinction.")
    if any(
        a.tier == "tier_2" and b.tier == "tier_1"
        for a, b in zip(draft.comments, draft.comments[1:], strict=False)
    ):
        raise ValueError("Email tiers must preserve priority order.")
    model_text = "\n".join((
        draft.opening,
        *(comment.heading + "\n" + comment.text for comment in draft.comments),
    ))
    assert_no_unsupported_policy_claims(model_text, set(prohibited_terms))
    if _SIGNATURE.search(draft.opening) or any(
        _SIGNATURE.search(comment.text) for comment in draft.comments
    ):
        raise ValueError("Generated emails must be unsigned.")
    if set(_NUMBERS.findall(model_text)) - set(_NUMBERS.findall(result_text(result))):
        raise ValueError("Email synthesis added an unsupported number.")
    evidence_ids = {
        key for area in result.priority_areas for key in area.evidence_ids
    } | {key for finding in result.core_findings for key in finding.evidence_ids}
    for key in evidence_ids:
        if re.search(rf"(?<![\w-]){re.escape(key)}(?![\w-])", model_text):
            raise ValueError("Email prose contains raw evidence identifiers.")
    areas = {area.priority_area_id: area for area in result.priority_areas}
    for comment in draft.comments:
        for key in comment.priority_area_ids:
            issues = validate_stage_behavior(
                result.metadata.review_stage, comment.text, areas[key].recommendation_scale,
                priority_area_id=key,
            )
            if any(issue.severity != "advisory" for issue in issues):
                raise ValueError("Email advice exceeds the review stage.")
    return draft
