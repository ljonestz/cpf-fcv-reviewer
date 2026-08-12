from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .extraction import ExtractedDocument


@dataclass(frozen=True)
class CountryDetection:
    country: str | None
    confidence: Literal["high", "low"]
    evidence: str | None


TITLE_PATTERNS = (
    re.compile(
        r"(?:country partnership framework|country engagement note)\s+for\s+"
        r"(?:the\s+)?(?P<country>[^\n,]+?)(?:\s+for\s+(?:fy|the period)|\s+fy\d|[,\n])",
        re.IGNORECASE,
    ),
)

PREFIXES = ("Republic of ", "The Republic of ", "Federal Republic of ")


def detect_country(document: ExtractedDocument) -> CountryDetection:
    sample = "\n".join(segment.text for segment in document.segments[:8])[:8000]
    for pattern in TITLE_PATTERNS:
        match = pattern.search(sample)
        if match:
            country = match.group("country").strip(" .:-")
            for prefix in PREFIXES:
                if country.casefold().startswith(prefix.casefold()):
                    country = country[len(prefix) :]
                    break
            return CountryDetection(country, "high", match.group(0)[:240])
    return CountryDetection(None, "low", None)
