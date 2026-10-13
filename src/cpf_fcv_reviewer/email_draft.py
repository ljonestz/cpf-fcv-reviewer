"""Synthesize an unsigned peer-review email from validated analytical findings."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from .contracts import EvidenceItem, PeerEmailDraft, ReviewResult
from .review_profiles import STAGE_PROFILES
from .validators import (
    assert_no_unsupported_policy_claims,
    has_current_context_assertion,
    result_text,
    validate_current_context_support,
    validate_stage_behavior,
)

_CLOSING = "We hope these comments are useful and look forward to the discussion."
_SIGNATURE = re.compile(
    r"(?:\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s*$)|"
    r"(?im:^\s*(?:signature|signed by|kind regards|best regards|sincerely)\b)|"
    r"\bShubham(?:\s+on behalf[^\n]*)?\s*$"
)
_NUMBERS = re.compile(r"\b\d+(?:[.,]\d+)*\b")


def email_failure_reason(error: Exception) -> str:
    """Expose only fixed diagnostic codes, never provider or rejected-output text."""
    if isinstance(error, TimeoutError):
        return "timeout"
    return {
        "Email priorities must preserve the validated review order.": "priority_order",
        "Use tiers only for a meaningful meeting/guidance distinction.": "tier_structure",
        "Email tiers must preserve priority order.": "tier_order",
        "Generated emails must be unsigned.": "signature",
        "Email synthesis added an unsupported number.": "unsupported_number",
        "Email prose contains raw evidence identifiers.": "raw_evidence_id",
        "Email opening exceeds the review stage.": "review_stage",
        "Email advice exceeds the review stage.": "review_stage",
        "Email added a claim without current-context support.": "current_context",
    }.get(str(error), "draft_failed")


def _prose_units(text: str) -> tuple[str, ...]:
    # A salutation or introductory sentence must not hide prescriptive advice.
    return (text, *re.split(r"(?:\r?\n)+|(?<=[.!?])\s+", text))


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


def validate_email_refinement(
    result: ReviewResult, text: str, *, evidence: Mapping[str, EvidenceItem],
) -> None:
    if not text.strip() or len(text) > 12_000:
        raise ValueError("Review comments exceed their text budget.")
    assert_no_unsupported_policy_claims(text, set())
    if any(re.search(rf"(?<![\w-]){re.escape(key)}(?![\w-])", text) for key in evidence):
        raise ValueError("Review comments contain raw evidence identifiers.")
    if _SIGNATURE.search(text):
        raise ValueError("Review comments must be unsigned.")
    if any(issue.severity != "advisory" for unit in _prose_units(text)
           for issue in validate_stage_behavior(result.metadata.review_stage, unit)):
        raise ValueError("Review comments exceed the review stage.")
    supported = result_text(result) + " ".join(
        item.supporting_quote or item.text for item in evidence.values()
    )
    factual_text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    if set(_NUMBERS.findall(factual_text)) - set(_NUMBERS.findall(supported)):
        raise ValueError("Review comments added an unsupported number.")
    for unit in _prose_units(text)[1:]:
        if has_current_context_assertion(unit) and validate_current_context_support(
            label="review_comments", heading="", assertion_texts=(unit,),
            evidence_ids=tuple(evidence), evidence=evidence, evidence_pool=True,
        ):
            raise ValueError("Review comments added an unsupported current claim.")


def generate_peer_email(
    result: ReviewResult,
    gateway,
    *,
    review_questions: str = "",
    follow_through: dict | None = None,
    style_entries=(),
    prohibited_terms=frozenset(),
    evidence: Mapping[str, EvidenceItem] | None = None,
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
    if any(issue.severity != "advisory" for unit in _prose_units(draft.opening)
           for issue in validate_stage_behavior(result.metadata.review_stage, unit)):
        raise ValueError("Email opening exceeds the review stage.")
    claims = [(draft.opening, tuple(evidence_ids))]
    for comment in draft.comments:
        claims.append((comment.text, tuple(dict.fromkeys(
            item for key in comment.priority_area_ids for item in areas[key].evidence_ids
        ))))
        for key in comment.priority_area_ids:
            issues = tuple(
                issue for unit in _prose_units(comment.text)
                for issue in validate_stage_behavior(
                    result.metadata.review_stage, unit, areas[key].recommendation_scale,
                    priority_area_id=key,
                )
            )
            if any(issue.severity != "advisory" for issue in issues):
                raise ValueError("Email advice exceeds the review stage.")
    for text, linked_evidence in claims:
        for unit in _prose_units(text)[1:]:
            if unit in result_text(result) or not has_current_context_assertion(unit):
                continue
            if validate_current_context_support(
                label="email", heading="", assertion_texts=(unit,),
                evidence_ids=linked_evidence, evidence=evidence or {}, evidence_pool=True,
            ):
                raise ValueError("Email added a claim without current-context support.")
    return draft
