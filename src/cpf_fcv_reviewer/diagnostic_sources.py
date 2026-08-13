from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

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
    kind: DiagnosticKind
    publication_date: date | None


def _candidate_text(document: object) -> str:
    name = str(getattr(document, "name", ""))
    segments = getattr(document, "segments", ())
    segment_text = " ".join(str(getattr(segment, "text", "")) for segment in segments[:3])
    return f"{name} {segment_text}"[:6000]


def _publication_date(text: str) -> date | None:
    dates = {
        (int(year), MONTHS[month.lower()])
        for month, year in MONTH_YEAR_PATTERN.findall(text)
    }
    if len(dates) != 1:
        return None
    year, month = next(iter(dates))
    return date(year, month, 1)


def identify_uploaded_diagnostic(
    documents: tuple,
    *,
    country: str,
) -> UploadedDiagnostic | None:
    normalized_country = country.strip().casefold()
    if not normalized_country:
        return None

    matches: list[UploadedDiagnostic] = []
    for document in documents:
        text = _candidate_text(document)
        lowered = text.casefold()
        if normalized_country not in lowered:
            continue
        has_rra_marker = any(marker in lowered for marker in RRA_MARKERS)
        has_accepted_marker = ACCEPTED_EQUIVALENT_MARKER in lowered
        has_fcv_risk_marker = FCV_RISK_ASSESSMENT_MARKER in str(
            getattr(document, "name", "")
        ).casefold()
        if not (has_rra_marker or has_accepted_marker or has_fcv_risk_marker):
            continue
        kind: DiagnosticKind = "rra" if has_rra_marker else "accepted_equivalent"
        matches.append(
            UploadedDiagnostic(
                name=str(getattr(document, "name", "")),
                kind=kind,
                publication_date=_publication_date(text),
            )
        )

    return matches[0] if len(matches) == 1 else None
