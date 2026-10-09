"""Read-in-full digests for supporting documents too large to supply verbatim.

Package and context documents are never sampled. When a role's documents fit its
direct budget they are supplied to the review in full. Otherwise the largest documents
are read in full by the model, one call per document, and replaced by a structured
digest plus the verbatim text of the pages the digest cites. Core package material
must cite pages; background material may not.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from pydantic import ValidationError

from .contracts import DocumentDigest, DocumentRole, EvidenceItem, EvidenceLocator

# Combined verbatim text a role may contribute to the review request. The review model
# has a 1M-token context; the full primary CPF (up to 600,000 characters) and these
# budgets together stay well inside it.
PACKAGE_DIRECT_MAX_CHARACTERS = 900_000
CONTEXT_DIRECT_MAX_CHARACTERS = 120_000
DIGEST_MAX_ESTIMATED_INPUT_TOKENS = 800_000
DIGEST_MAX_WORKERS = 4
MAX_CITED_SEGMENTS_PER_DOCUMENT = 40
CITED_SEGMENT_MAX_CHARACTERS = 4_000
_EXCERPT_CHARACTERS = 600
_MAX_SCHEMA_RETRY_ISSUES = 25
_DIGEST_SCHEMA_FIELDS = frozenset(
    {
        "document_type",
        "significance",
        "summary",
        "key_points",
        "point",
        "source_evidence_ids",
    }
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestOutcome:
    document_name: str
    digest: DocumentDigest | None
    evidence: tuple[EvidenceItem, ...]
    warning: str


def document_characters(document) -> int:
    return sum(len(segment.text) for segment in document.segments)


def plan_digests(documents: Sequence, direct_budget: int) -> frozenset[int]:
    """Return positions to digest: the largest documents until the rest fit."""
    sizes = [document_characters(document) for document in documents]
    remaining = sum(sizes)
    selected: set[int] = set()
    for position in sorted(range(len(documents)), key=lambda index: (-sizes[index], index)):
        if remaining <= direct_budget:
            break
        selected.add(position)
        remaining -= sizes[position]
    return frozenset(selected)


def _truncate(text: str, maximum: int) -> str:
    if len(text) <= maximum:
        return text
    truncated = text[:maximum]
    parts = truncated.rsplit(maxsplit=1)
    return parts[0].rstrip() if len(parts) == 2 else truncated


def segment_evidence(
    document,
    *,
    role: DocumentRole,
    prefix: str,
    document_index: int,
    max_characters: int | None = None,
) -> tuple[EvidenceItem, ...]:
    """Evidence items for every segment of one document, in document order."""
    items = []
    for segment_index, segment in enumerate(document.segments, start=1):
        text = segment.text if max_characters is None else _truncate(segment.text, max_characters)
        items.append(
            EvidenceItem(
                evidence_id=f"{prefix}-doc-{document_index:03d}-segment-{segment_index:03d}",
                evidence_type="document_fact",
                text=text,
                locator=EvidenceLocator(
                    document_title=document.name,
                    page=segment.page,
                    heading=segment.heading,
                    element=segment.element,
                    excerpt=_truncate(segment.text, _EXCERPT_CHARACTERS),
                ),
                confidence="high",
                document_role=role,
            )
        )
    return tuple(items)


def _estimated_tokens(payload: dict) -> int:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (max(len(serialized), len(serialized.encode("utf-8"))) + 2) // 3


def _safe_schema_issues(error: ValidationError) -> list[dict[str, object]]:
    issues = []
    for item in error.errors(
        include_url=False, include_context=False, include_input=False
    )[:_MAX_SCHEMA_RETRY_ISSUES]:
        location = []
        for part in item.get("loc", ())[:8]:
            if type(part) is int and 0 <= part <= 9999:
                location.append(part)
            elif isinstance(part, str) and part in _DIGEST_SCHEMA_FIELDS:
                location.append(part)
            else:
                location.append("unrecognized_field")
        issue_type = str(item.get("type", "validation_error"))
        if not re.fullmatch(r"[a-z0-9_]{1,64}", issue_type):
            issue_type = "validation_error"
        issues.append({"loc": location, "type": issue_type})
    return issues


def _excluded(document, reason: str) -> DigestOutcome:
    return DigestOutcome(
        document_name=document.name,
        digest=None,
        evidence=(),
        warning=(
            f"{document.name}: could not be summarised ({reason}) and was excluded "
            "from the review."
        ),
    )


def _page_label(item: EvidenceItem) -> str:
    locator = item.locator
    if locator is not None and locator.page is not None:
        return f"p. {locator.page}"
    if locator is not None and locator.element:
        return locator.element
    return item.evidence_id


def digest_document(
    gateway,
    document,
    *,
    role: DocumentRole,
    prefix: str,
    document_index: int,
) -> DigestOutcome:
    pages = segment_evidence(
        document, role=role, prefix=prefix, document_index=document_index
    )
    if not pages:
        return _excluded(document, "no extractable text")
    payload = {
        "document_title": document.name,
        "document_role": role.value,
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "page": item.locator.page,
                "heading": item.locator.heading,
                "element": item.locator.element,
                "text": item.text,
            }
            for item in pages
        ],
    }
    if _estimated_tokens(payload) > DIGEST_MAX_ESTIMATED_INPUT_TOKENS:
        return _excluded(document, "too large to read in one request")
    try:
        try:
            digest = gateway.generate(
                prompt_name="document_digest",
                payload=payload,
                output_type=DocumentDigest,
            )
        except ValidationError as error:
            digest = gateway.generate(
                prompt_name="document_digest",
                payload={**payload, "schema_retry": {"issues": _safe_schema_issues(error)}},
                output_type=DocumentDigest,
            )
    except ValidationError as error:
        logger.warning(
            "document_digest_schema_invalid attempt=2 schema_diagnostics=%s",
            json.dumps(_safe_schema_issues(error)),
        )
        return _excluded(document, "the summary did not satisfy the required schema")
    except Exception as exc:  # noqa: BLE001 - one document must not stop the review
        logger.warning("document_digest_failed error_type=%s", type(exc).__name__)
        return _excluded(document, "the summary request failed")

    page_by_id = {item.evidence_id: item for item in pages}
    cited: list[str] = []
    lines = []
    for point in digest.key_points:
        known = tuple(dict.fromkeys(i for i in point.source_evidence_ids if i in page_by_id))
        for evidence_id in known:
            if evidence_id not in cited and len(cited) < MAX_CITED_SEGMENTS_PER_DOCUMENT:
                cited.append(evidence_id)
        references = ", ".join(_page_label(page_by_id[i]) for i in known)
        lines.append(f"- {point.point}" + (f" ({references})" if references else ""))

    digest_item = EvidenceItem(
        evidence_id=f"{prefix}-doc-{document_index:03d}-digest",
        evidence_type="document_fact",
        text=(
            f"Digest of {document.name}, a {digest.significance} {digest.document_type} "
            f"read in full ({len(pages)} segments) and summarised by the model. "
            f"{digest.summary}\n" + "\n".join(lines)
        ),
        locator=EvidenceLocator(
            document_title=document.name,
            element="full-document digest",
            excerpt=_truncate(digest.summary, _EXCERPT_CHARACTERS),
            is_paraphrase=True,
        ),
        confidence="medium",
        document_role=role,
    )
    cited_items = tuple(
        page_by_id[evidence_id].model_copy(
            update={
                "text": _truncate(page_by_id[evidence_id].text, CITED_SEGMENT_MAX_CHARACTERS)
            }
        )
        for evidence_id in sorted(cited)
    )
    return DigestOutcome(
        document_name=document.name,
        digest=digest,
        evidence=(digest_item, *cited_items),
        warning=(
            f"{document.name}: read in full ({len(pages)} segments) and summarised as "
            f"{digest.significance} material; not supplied verbatim."
        ),
    )


@dataclass(frozen=True)
class DigestJob:
    document: object
    role: DocumentRole
    prefix: str
    document_index: int


def digest_documents(
    gateway,
    jobs: Sequence[DigestJob],
    *,
    on_complete: Callable[[int, int], None] | None = None,
) -> tuple[DigestOutcome, ...]:
    """Digest documents in parallel and return outcomes in job order."""
    if not jobs:
        return ()

    def run(job: DigestJob) -> DigestOutcome:
        return digest_document(
            gateway,
            job.document,
            role=job.role,
            prefix=job.prefix,
            document_index=job.document_index,
        )

    outcomes: list[DigestOutcome | None] = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=min(DIGEST_MAX_WORKERS, len(jobs))) as pool:
        futures = {pool.submit(run, job): position for position, job in enumerate(jobs)}
        completed = 0
        for future in futures:
            outcomes[futures[future]] = future.result()
            completed += 1
            if on_complete is not None:
                on_complete(completed, len(jobs))
    return tuple(outcome for outcome in outcomes if outcome is not None)
