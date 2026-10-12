"""Separate earlier review comments and assess follow-through after fresh analysis."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .contracts import (
    DocumentRole,
    EvidenceItem,
    FrozenModel,
    ReviewNarrative,
    ReviewResult,
)
from .document_digest import segment_evidence
from .extraction import ExtractedDocument
from .validators import assert_no_unsupported_policy_claims

_PRIOR_NAME = re.compile(
    r"(?:previous|earlier|prior)[ _-]+(?:fcv[ _-]+)?comments|"
    r"fcv[ _-]+(?:team[ _-]+)?comments|comments[ _-]+matrix|"
    r"(?:roc|oc|concept)[ _-]+(?:review[ _-]+)?(?:minutes|decision)|decision[ _-]+note",
    re.I,
)
_PRIOR_HEADING = re.compile(
    r"^\s*(?:(?:annex|section)\s+[\w.-]+\s*[:.-]\s*)?"
    r"(?:previous|earlier|prior|concept.stage)\s+(?:fcv\s+)?"
    r"(?:review\s+)?comments\b|^\s*(?:fcv\s+(?:team\s+)?comments|peer reviewer:)\b",
    re.I,
)
_NEXT_SECTION = re.compile(r"^\s*(?:annex|section)\s+[\w.-]+\b", re.I)


class PriorCommentCheck(FrozenModel):
    comment_label: ReviewNarrative = Field(max_length=250)
    assessment: ReviewNarrative = Field(max_length=1600)
    status: Literal["addressed", "partly_addressed", "unresolved", "not_assessable"]
    prior_evidence_ids: tuple[str, ...] = Field(min_length=1)
    current_evidence_ids: tuple[str, ...] = ()

    @field_validator("comment_label", "assessment")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A follow-through description cannot be blank.")
        return value

    @field_validator("prior_evidence_ids", "current_evidence_ids")
    @classmethod
    def nonblank_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("Follow-through evidence references cannot be blank.")
        return value

    @model_validator(mode="after")
    def requires_current_support(self) -> PriorCommentCheck:
        if self.status != "not_assessable" and not self.current_evidence_ids:
            raise ValueError("A follow-through finding requires current evidence.")
        return self


class PriorCommentReport(FrozenModel):
    checks: tuple[PriorCommentCheck, ...] = Field(max_length=20)
    coverage_note: ReviewNarrative = Field(max_length=2000)

    @field_validator("coverage_note")
    @classmethod
    def nonblank_coverage(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Follow-through coverage cannot be blank.")
        return value


def partition_document(
    document: ExtractedDocument,
) -> tuple[ExtractedDocument | None, ExtractedDocument | None]:
    """Keep real source coordinates while withholding clearly labelled commentary."""
    first_text = document.segments[0].text if document.segments else ""
    if _PRIOR_NAME.search(document.name) or _PRIOR_HEADING.match(first_text):
        return None, document
    current, prior = [], []
    in_prior = False
    for segment in document.segments:
        if segment.heading and _PRIOR_HEADING.match(segment.heading):
            in_prior = True
        parts = {False: [], True: []}
        for line in segment.text.splitlines(keepends=True):
            if _PRIOR_HEADING.match(line):
                in_prior = True
            elif in_prior and _NEXT_SECTION.match(line):
                in_prior = False
            parts[in_prior].append(line)
        for target, flag in ((current, False), (prior, True)):
            text = "".join(parts[flag]).strip()
            if text:
                target.append(replace(segment, text=text))
    if not prior:
        return document, None
    return (
        replace(document, segments=tuple(current)) if current else None,
        replace(document, segments=tuple(prior)),
    )


def check_prior_comments(
    result: ReviewResult,
    evidence: dict[str, EvidenceItem],
    documents: tuple[ExtractedDocument, ...],
    gateway,
    *,
    prohibited_terms: set[str],
    incomplete_document_roles=frozenset(),
) -> tuple[PriorCommentReport, tuple[EvidenceItem, ...]]:
    """Return separate annotations; never rewrite the independent result."""
    prior_evidence = tuple(
        item
        for index, document in enumerate(documents, 1)
        for item in segment_evidence(
            document, role=DocumentRole.PACKAGE, prefix="prior", document_index=index,
        )
    )
    if not prior_evidence or sum(len(item.text) for item in prior_evidence) > 150_000:
        raise ValueError("Previous-comment coverage is unavailable.")
    current = {
        key: item for key, item in evidence.items()
        if item.document_role in {DocumentRole.PRIMARY, DocumentRole.PACKAGE}
    }
    payload = {
        "review_stage": result.metadata.review_stage,
        "assessment_as_of": result.metadata.created_at.date().isoformat(),
        "independent_findings": result.model_dump(mode="json"),
        "prior_evidence": [item.model_dump(mode="json") for item in prior_evidence],
        "current_evidence": [item.model_dump(mode="json") for item in current.values()],
        "coverage_limited": bool(incomplete_document_roles),
    }
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 2_000_000:
        raise ValueError("Follow-through input exceeds the safe budget.")
    report = gateway.generate(
        prompt_name="prior_comments", payload=payload, output_type=PriorCommentReport,
    )
    prior_ids = {item.evidence_id for item in prior_evidence}
    checks = []
    for check in report.checks:
        if not set(check.prior_evidence_ids) <= prior_ids or not (
            set(check.current_evidence_ids) <= current.keys()
        ):
            raise ValueError("Follow-through references are invalid.")
        if incomplete_document_roles and check.status == "unresolved":
            check = check.model_copy(update={
                "status": "not_assessable",
                "assessment": (
                    "Current package coverage limits whether this earlier point remains unresolved."
                ),
            })
        checks.append(check)
    text = "\n".join((
        report.coverage_note,
        *(item.comment_label + "\n" + item.assessment for item in checks),
    ))
    assert_no_unsupported_policy_claims(text, prohibited_terms)
    for key in prior_ids | current.keys():
        if re.search(rf"(?<![\w-]){re.escape(key)}(?![\w-])", text):
            raise ValueError("Follow-through prose contains raw evidence identifiers.")
    return report.model_copy(update={"checks": tuple(checks)}), prior_evidence
