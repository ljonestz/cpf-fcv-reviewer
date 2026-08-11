from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from .public_research import _is_public_http_url


def select_output_language(input_language: str) -> Literal["en"]:
    """Return the only output language supported by the MVP."""
    return "en"


def reject_source(source: Mapping[str, object]) -> bool:
    """Reject sources that cannot support a retained current-context claim."""
    provider = str(source.get("provider", "")).strip().casefold()
    license_name = str(source.get("license", "")).strip().casefold()
    url = source.get("url", source.get("source_url"))
    publication_date = source.get("publication_date", source.get("source_date"))
    relevance = source.get("relevance")

    if license_name == "licensed":
        return True
    if provider == "acled" and license_name != "public":
        return True
    if not isinstance(url, str) or not _is_public_http_url(url):
        return True
    if publication_date is None or not str(publication_date).strip():
        return True
    if not isinstance(relevance, str) or not relevance.strip():
        return True
    return False


def redact_log_value(value: object) -> str:
    """Replace arbitrary content with a stable non-content marker."""
    del value
    return "[content omitted]"
