from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from .contracts import DiagnosticProvenance, EvidenceLocator
from .extraction import ExtractedDocument

DiagnosticKind = Literal["rra", "accepted_equivalent"]

RRA_MARKERS = ("risk and resilience assessment", "risk & resilience assessment")
ACCEPTED_EQUIVALENT_MARKER = "accepted equivalent diagnostic"
FCV_RISK_ASSESSMENT_MARKER = "fcv risk assessment"
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
MONTH_YEAR_PATTERN = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UploadedDiagnostic:
    name: str
    source_index: int
    kind: DiagnosticKind
    publication_date: date | None


def _candidate_text(document: ExtractedDocument) -> str:
    segment_text = " ".join(segment.text for segment in document.segments[:4])
    return f"{document.name} {segment_text}"[:6000]


def _publication_date(text: str) -> date | None:
    dates = {
        (int(year), MONTHS[month.lower()])
        for month, year in MONTH_YEAR_PATTERN.findall(text)
    }
    if len(dates) != 1:
        return None
    year, month = next(iter(dates))
    return date(year, month, 1) if year > 0 else None


_MONTH_YEAR_TEXT = r"(?:" + "|".join(MONTHS) + r")\s+\d{4}"
_PUBLICATION_STATEMENT = re.compile(
    rf"\b(?:publication(?:\s+date)?|date\s+of\s+publication|published|issued)"
    rf"\s*[:,-]?\s*(?:in\s+)?(?P<date>{_MONTH_YEAR_TEXT})\b", re.I,
)
_TITLE_DATE = re.compile(
    r"\b(?:risk\s+(?:and|&)\s+resilience\s+assessment|rra|"
    r"accepted\s+equivalent\s+diagnostic|fcv\s+risk\s+assessment)"
    rf"\s*[,:(.-]?\s*(?P<date>{_MONTH_YEAR_TEXT})\b", re.I,
)
_STANDALONE_DATE = re.compile(rf"^\s*(?P<date>{_MONTH_YEAR_TEXT})[.\s]*$", re.I | re.M)


def diagnostic_provenance(document: ExtractedDocument) -> DiagnosticProvenance:
    """Read a publication month from bounded frontmatter, retaining its source.

    Physical PDF pages matter: the first extractable page is not necessarily the
    cover. Filenames and file-creation timestamps are never publication evidence.
    Conflicting cover/publication statements remain explicitly unestablished.
    """
    unknown = DiagnosticProvenance(document_title=document.name)
    front = tuple(segment for segment in document.segments[:8]
                  if segment.page is None or segment.page <= 4)
    candidates = []
    for index, segment in enumerate(front):
        text = segment.text[:6000]
        matches = [(match, "publication_statement")
                   for match in _PUBLICATION_STATEMENT.finditer(text)]
        if segment.page == 1 or (segment.page is None and index < 4):
            matches.extend((match, "cover") for match in _TITLE_DATE.finditer(text))
            for match in _STANDALONE_DATE.finditer(text):
                preceding = text[:match.start()].strip()
                if not preceding and index:
                    preceding = front[index - 1].text.strip()
                label = preceding.splitlines()[-1] if preceding else ""
                if not re.search(
                    r"\b(?:mission|fieldwork|consultations?|workshop|copyright|revised)\b",
                    label[-150:], re.I,
                ):
                    matches.append((match, "cover"))
        for match, basis in matches:
            publication_date = _publication_date(match.group("date"))
            if publication_date is not None:
                candidates.append((publication_date, basis, segment, match.group("date")))
    if len({candidate[0] for candidate in candidates}) != 1:
        return unknown
    publication_date, basis, segment, quote = candidates[0]
    return DiagnosticProvenance(
        document_title=document.name,
        publication_date=publication_date,
        date_basis=basis,
        locator=EvidenceLocator(
            document_title=document.name, page=segment.page, heading=segment.heading,
            element=segment.element, excerpt=quote,
        ),
    )


def identify_uploaded_diagnostic(
    documents: tuple[ExtractedDocument, ...],
    *,
    country: str,
) -> UploadedDiagnostic | None:
    normalized_country = country.strip().casefold()
    if not normalized_country:
        return None

    matches: list[UploadedDiagnostic] = []
    for source_index, document in enumerate(documents):
        text = _candidate_text(document)
        lowered = text.casefold()
        country_pattern = rf"(?<!\w){re.escape(normalized_country)}(?!\w)"
        if re.search(country_pattern, lowered) is None:
            continue
        has_rra_marker = any(marker in lowered for marker in RRA_MARKERS)
        has_accepted_marker = ACCEPTED_EQUIVALENT_MARKER in lowered
        has_fcv_risk_marker = FCV_RISK_ASSESSMENT_MARKER in lowered
        if not (has_rra_marker or has_accepted_marker or has_fcv_risk_marker):
            continue
        kind: DiagnosticKind = "rra" if has_rra_marker else "accepted_equivalent"
        matches.append(
            UploadedDiagnostic(
                name=document.name,
                source_index=source_index,
                kind=kind,
                publication_date=diagnostic_provenance(document).publication_date,
            )
        )

    return matches[0] if len(matches) == 1 else None
