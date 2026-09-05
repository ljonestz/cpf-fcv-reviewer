from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from .extraction import ExtractedDocument

COUNTRY_DETECTION_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
COUNTRY_DETECTION_MAX_PDF_PAGES = 16
COUNTRY_DETECTION_MAX_SEGMENTS = 256
COUNTRY_DETECTION_MAX_CHARACTERS = 100_000
COUNTRY_DETECTION_MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024
COUNTRY_DETECTION_MAX_ARCHIVE_MEMBERS = 512


@dataclass(frozen=True)
class CountryDetection:
    country: str | None
    confidence: Literal["high", "low"]
    evidence: str | None


# This small, deterministic registry is deliberately local.  It prevents a title
# regex from promoting arbitrary text to a high-confidence country and records the
# common World Bank/CPF naming variants used in titles.
COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "Afghanistan": (),
    "Albania": (),
    "Algeria": (),
    "Angola": (),
    "Antigua and Barbuda": (),
    "Argentina": (),
    "Armenia": (),
    "Australia": (),
    "Austria": (),
    "Azerbaijan": (),
    "Bahamas": ("The Bahamas",),
    "Bahrain": (),
    "Bangladesh": (),
    "Barbados": (),
    "Belarus": (),
    "Belgium": (),
    "Belize": (),
    "Benin": (),
    "Bhutan": (),
    "Bolivia": ("Bolivia (Plurinational State of)",),
    "Bosnia and Herzegovina": (),
    "Botswana": (),
    "Brazil": (),
    "Brunei": ("Brunei Darussalam",),
    "Bulgaria": (),
    "Burkina Faso": (),
    "Burundi": (),
    "Cabo Verde": ("Cape Verde",),
    "Cambodia": (),
    "Cameroon": (),
    "Canada": (),
    "Central African Republic": (),
    "Chad": (),
    "Chile": (),
    "China": (),
    "Colombia": (),
    "Comoros": (),
    "Congo": ("Republic of Congo", "Republic of the Congo"),
    "Costa Rica": (),
    "Cote d'Ivoire": ("Côte d'Ivoire", "Ivory Coast"),
    "Croatia": (),
    "Cuba": (),
    "Cyprus": (),
    "Czechia": ("Czech Republic",),
    "Democratic Republic of the Congo": (
        "DRC",
        "D.R. Congo",
        "Democratic Republic of Congo",
    ),
    "Denmark": (),
    "Djibouti": (),
    "Dominica": (),
    "Dominican Republic": (),
    "Ecuador": (),
    "Egypt": ("Egypt, Arab Republic of",),
    "El Salvador": (),
    "Equatorial Guinea": (),
    "Eritrea": (),
    "Estonia": (),
    "Eswatini": ("Swaziland",),
    "Ethiopia": (),
    "Fiji": (),
    "Finland": (),
    "France": (),
    "Gabon": (),
    "The Gambia": ("Gambia",),
    "Georgia": (),
    "Germany": (),
    "Ghana": (),
    "Greece": (),
    "Grenada": (),
    "Guatemala": (),
    "Guinea": (),
    "Guinea-Bissau": (),
    "Guyana": (),
    "Haiti": (),
    "Honduras": (),
    "Hungary": (),
    "Iceland": (),
    "India": (),
    "Indonesia": (),
    "Iran": ("Iran, Islamic Republic of",),
    "Iraq": (),
    "Ireland": (),
    "Israel": (),
    "Italy": (),
    "Jamaica": (),
    "Japan": (),
    "Jordan": (),
    "Kazakhstan": (),
    "Kenya": (),
    "Kiribati": (),
    "Kosovo": (),
    "Kuwait": (),
    "Kyrgyz Republic": ("Kyrgyzstan",),
    "Lao PDR": ("Laos", "Lao People's Democratic Republic"),
    "Latvia": (),
    "Lebanon": (),
    "Lesotho": (),
    "Liberia": (),
    "Libya": (),
    "Liechtenstein": (),
    "Lithuania": (),
    "Luxembourg": (),
    "Madagascar": (),
    "Malawi": (),
    "Malaysia": (),
    "Maldives": (),
    "Mali": (),
    "Malta": (),
    "Marshall Islands": (),
    "Mauritania": (),
    "Mauritius": (),
    "Mexico": (),
    "Micronesia": ("Federated States of Micronesia",),
    "Moldova": ("Republic of Moldova",),
    "Monaco": (),
    "Mongolia": (),
    "Montenegro": (),
    "Morocco": (),
    "Mozambique": (),
    "Myanmar": ("Burma",),
    "Namibia": (),
    "Nauru": (),
    "Nepal": (),
    "Netherlands": (),
    "New Zealand": (),
    "Nicaragua": (),
    "Niger": (),
    "Nigeria": (),
    "North Korea": ("Democratic People's Republic of Korea",),
    "North Macedonia": ("Macedonia",),
    "Norway": (),
    "Oman": (),
    "Pakistan": (),
    "Palau": (),
    "Panama": (),
    "Papua New Guinea": (),
    "Paraguay": (),
    "Peru": (),
    "Philippines": (),
    "Poland": (),
    "Portugal": (),
    "Qatar": (),
    "Romania": (),
    "Russia": ("Russian Federation",),
    "Rwanda": (),
    "Saint Kitts and Nevis": (),
    "Saint Lucia": (),
    "Saint Vincent and the Grenadines": (),
    "Samoa": (),
    "San Marino": (),
    "São Tomé and Príncipe": ("Sao Tome and Principe",),
    "Saudi Arabia": (),
    "Senegal": (),
    "Serbia": (),
    "Seychelles": (),
    "Sierra Leone": (),
    "Singapore": (),
    "Slovakia": (),
    "Slovenia": (),
    "Solomon Islands": (),
    "Somalia": (),
    "South Africa": (),
    "South Korea": ("Republic of Korea",),
    "South Sudan": (),
    "Spain": (),
    "Sri Lanka": (),
    "Sudan": (),
    "Suriname": (),
    "Sweden": (),
    "Switzerland": (),
    "Syria": ("Syrian Arab Republic",),
    "Taiwan": (),
    "Tajikistan": (),
    "Tanzania": ("United Republic of Tanzania",),
    "Thailand": (),
    "Timor-Leste": ("East Timor",),
    "Togo": (),
    "Tonga": (),
    "Trinidad and Tobago": (),
    "Tunisia": (),
    "Türkiye": ("Turkey",),
    "Turkmenistan": (),
    "Tuvalu": (),
    "Uganda": (),
    "Ukraine": (),
    "United Arab Emirates": (),
    "United Kingdom": ("UK",),
    "United States": ("USA", "United States of America"),
    "Uruguay": (),
    "Uzbekistan": (),
    "Vanuatu": (),
    "Vatican City": ("Holy See",),
    "Venezuela": ("Venezuela, RB",),
    "Vietnam": ("Viet Nam",),
    "West Bank and Gaza": ("Palestinian Territories", "West Bank & Gaza"),
    "Yemen": (),
    "Zambia": (),
    "Zimbabwe": (),
}


def _registry_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(without_marks.replace("’", "'").split()).casefold()


COUNTRY_BY_ALIAS = {
    _registry_key(alias): country
    for country, aliases in COUNTRY_ALIASES.items()
    for alias in (country, *aliases)
}

TITLE_PATTERNS = (
    re.compile(
        r"(?:country partnership framework|country engagement note)\s+for\s+"
        r"(?:the\s+)?(?P<country>[^\n,]+?)(?:\s+for\s+(?:fy|the period)|\s+fy\d|[,\n])",
        re.IGNORECASE,
    ),
)

PREFIXES = (
    "Federal Republic of ",
    "Democratic Republic of ",
    "United Republic of ",
    "Islamic Republic of ",
    "The Republic of ",
    "Republic of ",
)


def _bounded_sample(document: ExtractedDocument, limit: int = 8000) -> str:
    parts: list[str] = []
    remaining = limit
    for segment in document.segments[:8]:
        if remaining <= 0:
            break
        text = segment.text[:remaining]
        parts.append(text)
        remaining -= len(text) + 1
    return "\n".join(parts)[:limit]


def _canonical_country(raw_candidate: str) -> str | None:
    candidate = unicodedata.normalize("NFKC", raw_candidate).strip(" .:-")
    if not candidate or any(unicodedata.category(char).startswith("C") for char in candidate):
        return None

    exact_match = COUNTRY_BY_ALIAS.get(_registry_key(candidate))
    if exact_match is not None:
        return exact_match

    for prefix in PREFIXES:
        if candidate.casefold().startswith(prefix.casefold()):
            candidate = candidate[len(prefix) :].strip(" .:-")
            break
    if any(char.isdigit() for char in candidate):
        return None
    return COUNTRY_BY_ALIAS.get(_registry_key(candidate))


def detect_country(document: ExtractedDocument) -> CountryDetection:
    sample = _bounded_sample(document)
    for pattern in TITLE_PATTERNS:
        match = pattern.search(sample)
        if match:
            country = _canonical_country(match.group("country"))
            if country is not None:
                return CountryDetection(country, "high", match.group(0)[:240])
    return CountryDetection(None, "low", None)
