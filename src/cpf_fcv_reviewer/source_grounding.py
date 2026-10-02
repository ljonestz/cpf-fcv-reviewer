"""Resolve exact cited passages and classify failures without exposing their content."""

import re
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Literal, get_args

from .contracts import (
    AssessmentStatus, DocumentRole, EvidenceItem, EvidenceLocator, RRADriverAssessment,
)

QUOTE_SELECTION_PREFIX = "CPF_QUOTE:"
QuoteFailureReason = Literal[
    "empty_response", "absence_status_conflict", "invalid_quote_selection",
    "uncited_quote_selection", "no_cited_primary_package", "quote_not_in_cited_text",
]
QUOTE_FAILURE_REASONS = frozenset(get_args(QuoteFailureReason))

NO_CPF_QUOTE = "No verified CPF/package quotation is available for this driver."

LocatorFailureReason = Literal[
    "no_cited_document",
    "document_not_cited",
    "coordinate_not_cited",
    "empty_excerpt",
    "paraphrase_unverified",
    "excerpt_mismatch",
]
LOCATOR_FAILURE_REASONS = frozenset(get_args(LocatorFailureReason))
_WORD = re.compile(r"\w+")
_PERCENTAGE = re.compile(
    r"(?<![\w.])([+-]?\d+(?:\.\d+)?)\s*(?:%|percent\b|per\s+cent\b)",
    re.IGNORECASE,
)


def cited_document_evidence(
    evidence_ids: Iterable[str], evidence: Mapping[str, EvidenceItem],
) -> tuple[EvidenceItem, ...]:
    return tuple(
        evidence[evidence_id]
        for evidence_id in dict.fromkeys(evidence_ids)
        if evidence_id in evidence
        and evidence[evidence_id].evidence_type == "document_fact"
        and evidence[evidence_id].document_role in {DocumentRole.PRIMARY, DocumentRole.PACKAGE}
        and evidence[evidence_id].locator is not None
    )


def exact_source_excerpt(excerpt: str, text: str) -> str | None:
    """Match complete adjacent words and return their literal source span."""
    needle_words = [word.casefold() for word in _WORD.findall(excerpt)]
    if not needle_words:
        return None
    source_words = list(_WORD.finditer(text))
    normalized = " " + " ".join(word.group().casefold() for word in source_words) + " "
    index = normalized.find(" " + " ".join(needle_words) + " ")
    if index < 0:
        return None
    first = normalized[:index].count(" ")
    last = first + len(needle_words) - 1
    return text[source_words[first].start():source_words[last].end()]


def _same_location(target: EvidenceLocator, source: EvidenceLocator) -> bool:
    if target.document_title != source.document_title:
        return False
    if target.document_version is not None and target.document_version != source.document_version:
        return False
    if target.page is not None:
        return target.page == source.page
    if target.element is not None:
        return target.element == source.element
    return target.heading is not None and target.heading == source.heading


def locator_failure_reason(
    target: EvidenceLocator, evidence: Iterable[EvidenceItem],
) -> LocatorFailureReason | None:
    items = tuple(evidence)
    if not items:
        return "no_cited_document"
    if not any(item.locator.document_title == target.document_title for item in items):
        return "document_not_cited"
    located = [item for item in items if _same_location(target, item.locator)]
    if not located:
        return "coordinate_not_cited"
    if not _WORD.search(target.excerpt):
        return "empty_excerpt"
    if target.is_paraphrase:
        return "paraphrase_unverified"
    if not any(exact_source_excerpt(target.excerpt, item.text) is not None for item in located):
        return "excerpt_mismatch"
    return None


def resolve_target_locator(
    target: EvidenceLocator, evidence: Iterable[EvidenceItem],
) -> EvidenceLocator:
    candidates = [
        (item, excerpt)
        for item in evidence
        if (excerpt := exact_source_excerpt(target.excerpt, item.text)) is not None
    ]
    located = [(item, excerpt) for item, excerpt in candidates
               if _same_location(target, item.locator)]
    candidates = located or candidates
    locations = {
        (item.locator.document_title, item.locator.document_version,
         ("page", item.locator.page) if item.locator.page is not None
         else ("element", item.locator.element) if item.locator.element is not None
         else ("heading", item.locator.heading))
        for item, _ in candidates
    }
    if len(locations) != 1:
        return target
    source, excerpt = candidates[0]
    # Coordinates and the rendered quotation come from the source, never model memory.
    return source.locator.model_copy(update={"excerpt": excerpt, "is_paraphrase": False})


def percentage_values(text: str) -> set[Decimal]:
    """A value-presence guard only; this does not establish meaning or feasibility."""
    return {Decimal(match.group(1)) for match in _PERCENTAGE.finditer(text)}


def _quote_passages(text: str) -> tuple[str, ...]:
    # Long, unpunctuated blocks remain available through the literal-quote fallback.
    # Do not silently cut a source passage to make it selectable.
    return tuple(part.strip() for part in re.split(r"(?<=[.!?])\s+|\n\s*\n", text)
                 if _WORD.search(part) and len(part.strip()) <= 1500)


def cpf_quote_index(evidence: Mapping[str, EvidenceItem]) -> list[dict[str, str]]:
    """A compact selection aid; complete evidence text remains in the request."""
    return [
        {"quote_id": f"{QUOTE_SELECTION_PREFIX}{item.evidence_id}:{index}",
         "evidence_id": item.evidence_id, "preview": passage[:160]}
        for item in cited_document_evidence(evidence, evidence)
        for index, passage in enumerate(_quote_passages(item.text), 1)
    ]


def _quote_selection(
    response: str, evidence: Mapping[str, EvidenceItem],
) -> tuple[EvidenceItem, str] | None:
    match = re.fullmatch(r"CPF_QUOTE:(.+):([1-9]\d{0,5})", response.strip())
    if match is None:
        return None
    items = cited_document_evidence((match[1],), evidence)
    if not items:
        return None
    item = items[0]
    passages = _quote_passages(item.text)
    index = int(match[2]) - 1
    return (item, passages[index]) if index < len(passages) else None


def resolve_cpf_response(
    row: RRADriverAssessment, evidence: Mapping[str, EvidenceItem],
) -> str | None:
    """Materialize a selected, own-cited passage; literal quotations remain supported."""
    if row.cpf_response.strip().startswith(QUOTE_SELECTION_PREFIX):
        selected = _quote_selection(row.cpf_response, evidence)
        if selected is None or selected[0].evidence_id not in row.evidence_ids:
            return None
        row = row.model_copy(update={"cpf_response": selected[1]})
    return verified_cpf_response(row, evidence)


def cpf_response_failure_reason(
    row: RRADriverAssessment, evidence: Mapping[str, EvidenceItem],
) -> QuoteFailureReason | None:
    if verified_cpf_response(row, evidence) is not None:
        return None
    if row.cpf_response.strip().startswith(QUOTE_SELECTION_PREFIX):
        selected = _quote_selection(row.cpf_response, evidence)
        return ("uncited_quote_selection" if selected is not None
                and selected[0].evidence_id not in row.evidence_ids
                else "invalid_quote_selection")
    words = _WORD.findall(row.cpf_response.casefold())
    if not words:
        return "empty_response"
    if words == _WORD.findall(NO_CPF_QUOTE.casefold()):
        return "absence_status_conflict"
    if not cited_document_evidence(row.evidence_ids, evidence):
        return "no_cited_primary_package"
    return "quote_not_in_cited_text"


def verified_cpf_response(
    row: RRADriverAssessment, evidence: Mapping[str, EvidenceItem],
) -> str | None:
    if row.cpf_response.strip().startswith(QUOTE_SELECTION_PREFIX):
        return None
    if _WORD.findall(row.cpf_response.casefold()) == _WORD.findall(NO_CPF_QUOTE.casefold()):
        return NO_CPF_QUOTE if row.status in {
            AssessmentStatus.NOT_EVIDENCED, AssessmentStatus.NOT_ASSESSABLE,
        } else None
    for item in cited_document_evidence(row.evidence_ids, evidence):
        if (excerpt := exact_source_excerpt(row.cpf_response, item.text)) is not None:
            return excerpt
    return None
