from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime
from html.parser import HTMLParser
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    field_validator,
    model_validator,
)

from .country_detection import COUNTRY_ALIASES


MAX_SEARCH_OUTPUT_TOKENS = 2_000
MAX_ARTICLE_METADATA_BYTES = 256 * 1_024
PUBLICATION_DATE_BASIS = Literal[
    "provider_metadata",
    "canonical_url",
    "source_excerpt",
    "article_metadata",
    "conflicting",
]
MAX_RETAINED_SOURCES = 3
MAX_RETAINED_FINDINGS = 6
MAX_SOURCE_EXCERPT_CHARACTERS = 1_500
MAX_SOURCE_BUNDLE_CHARACTERS = 6_000
PREFERRED_SEARCH_DOMAINS = (
    "crisisgroup.org",
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "rescue.org",
    "acleddata.com",
)
SECONDARY_SEARCH_DOMAINS = (
    "un.org",
    "unhcr.org",
    "unocha.org",
    "wfp.org",
    "icrc.org",
    "iom.int",
    "reliefweb.int",
    "issafrica.org",
    "africacenter.org",
)
SEARCH_ALLOWED_DOMAINS = PREFERRED_SEARCH_DOMAINS + SECONDARY_SEARCH_DOMAINS


def Anthropic(*args, **kwargs):
    from anthropic import Anthropic as AnthropicClient

    return AnthropicClient(*args, **kwargs)


class CurrentContextClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    text: str
    publisher: str
    source_title: str
    source_url: str | None
    source_date: date
    supporting_quote: str | None = Field(default=None, max_length=MAX_SOURCE_EXCERPT_CHARACTERS)
    publication_date_basis: PUBLICATION_DATE_BASIS | None = None
    source_type: str
    relevance: str
    context_kind: Literal[
        "structural_dynamic",
        "current_development",
        "resilience_factor",
        "implementation_condition",
    ]
    relationship: Literal[
        "corroborates",
        "qualifies",
        "contradicts",
        "unresolved",
        "establishes",
    ]
    licensed_data_required: StrictBool

    @field_validator("claim_id", "text", "publisher", "source_title", "source_type")
    @classmethod
    def requires_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Current-context claim text fields cannot be blank.")
        return value.strip()

    @field_validator("source_url")
    @classmethod
    def normalizes_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(ord(character) < 32 for character in value):
            return value
        return value.strip()


class ResearchSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    url: str
    publisher: str | None = None
    published_at: date | None = None
    publication_date_basis: PUBLICATION_DATE_BASIS | None = None
    excerpt: str | None = Field(default=None, max_length=MAX_SOURCE_EXCERPT_CHARACTERS)


class SearchArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    narrative: str = Field(max_length=MAX_SOURCE_BUNDLE_CHARACTERS)
    sources: tuple[ResearchSource, ...] = Field(max_length=MAX_RETAINED_SOURCES)

    @model_validator(mode="after")
    def caps_complete_serialized_bundle(self) -> "SearchArtifact":
        if len(self.model_dump_json()) > MAX_SOURCE_BUNDLE_CHARACTERS:
            raise ValueError("Serialized source bundle exceeds the character limit.")
        return self



class ResearchClaimBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claims: tuple[CurrentContextClaim, ...] = Field(max_length=MAX_RETAINED_FINDINGS)


def retain_public_claims(
    claims: tuple[CurrentContextClaim, ...],
) -> tuple[tuple[CurrentContextClaim, ...], dict[str, str]]:
    retained: list[CurrentContextClaim] = []
    rejected: dict[str, str] = {}
    duplicate_claim_ids = {
        claim_id
        for claim_id, count in Counter(claim.claim_id for claim in claims).items()
        if count > 1
    }

    for claim in claims:
        if claim.claim_id in duplicate_claim_ids:
            rejected[claim.claim_id] = "duplicate claim ID is not permitted"
        elif claim.licensed_data_required:
            rejected[claim.claim_id] = "licensed data is not permitted"
        elif not _is_public_http_url(claim.source_url):
            rejected[claim.claim_id] = "public source URL is required"
        elif not claim.relevance.strip():
            rejected[claim.claim_id] = "material relevance is required"
        elif not _is_permitted_public_source(claim):
            rejected[claim.claim_id] = "permitted institutional public source is required"
        else:
            retained.append(claim)

    return tuple(retained), rejected


def _is_public_http_url(url: str | None) -> bool:
    if url is None:
        return False

    if any(ord(character) < 32 for character in url):
        return False
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False

    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False

    normalized_hostname = hostname.rstrip(".").lower()

    try:
        address = ip_address(normalized_hostname)
        return (
            address.is_global
            and not address.is_multicast
            and not address.is_reserved
            and not address.is_unspecified
            and not address.is_loopback
            and not getattr(address, "is_site_local", False)
            and not address.is_link_local
            and not address.is_private
        )
    except ValueError:
        if _is_legacy_numeric_authority(normalized_hostname):
            return False
        return _is_valid_public_hostname(normalized_hostname)


def _is_legacy_numeric_authority(hostname: str) -> bool:
    return all(
        label.isdecimal()
        or (
            label.startswith("0x")
            and len(label) > 2
            and all(character in "0123456789abcdef" for character in label[2:])
        )
        for label in hostname.split(".")
    )


def _is_valid_public_hostname(hostname: str) -> bool:
    special_suffixes = (
        ".example",
        ".invalid",
        ".local",
        ".localhost",
        ".internal",
        ".home.arpa",
        ".onion",
        ".test",
    )
    if "." not in hostname or len(hostname) > 253 or hostname.endswith(special_suffixes):
        return False

    return all(
        label
        and len(label) <= 63
        and label.isascii()
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in label)
        for label in hostname.split(".")
    )


_INSTITUTIONAL_PUBLISHER_HOSTS = {
    "world bank": (("worldbank.org",), "World Bank"),
    "world bank group": (("worldbank.org",), "World Bank"),
    "the world bank": (("worldbank.org",), "World Bank"),
    "united nations development programme": (("undp.org",), "UNDP"),
    "undp": (("undp.org",), "UNDP"),
    "un development programme": (("undp.org",), "UNDP"),
    "unhcr": (("unhcr.org",), "UNHCR"),
    "united nations high commissioner for refugees": (("unhcr.org",), "UNHCR"),
    "ocha": (("unocha.org",), "OCHA"),
    "office for the coordination of humanitarian affairs": (("unocha.org",), "OCHA"),
    "united nations office for the coordination of humanitarian affairs": (
        ("unocha.org",),
        "OCHA",
    ),
    "wfp": (("wfp.org",), "WFP"),
    "world food programme": (("wfp.org",), "WFP"),
    "who": (("who.int",), "WHO"),
    "world health organization": (("who.int",), "WHO"),
    "unicef": (("unicef.org",), "UNICEF"),
    "united nations children s fund": (("unicef.org",), "UNICEF"),
    "unep": (("unep.org",), "UNEP"),
    "united nations environment programme": (("unep.org",), "UNEP"),
    "unodc": (("unodc.org",), "UNODC"),
    "united nations office on drugs and crime": (("unodc.org",), "UNODC"),
    "undrr": (("undrr.org",), "UNDRR"),
    "united nations office for disaster risk reduction": (("undrr.org",), "UNDRR"),
    "un women": (("unwomen.org",), "UN Women"),
    "unwomen": (("unwomen.org",), "UN Women"),
    "united nations": (("un.org",), "United Nations"),
    "united nations entity for gender equality and the empowerment of women": (
        ("unwomen.org",),
        "UN Women",
    ),
    "oecd": (("oecd.org",), "OECD"),
    "international monetary fund": (("imf.org",), "IMF"),
    "imf": (("imf.org",), "IMF"),
    "african development bank": (("afdb.org",), "AfDB"),
    "afdb": (("afdb.org",), "AfDB"),
    "asian development bank": (("adb.org",), "ADB"),
    "adb": (("adb.org",), "ADB"),
    "inter american development bank": (("iadb.org",), "IDB"),
    "iadb": (("iadb.org",), "IDB"),
    "idb": (("iadb.org",), "IDB"),
    "european bank for reconstruction and development": (("ebrd.com",), "EBRD"),
    "ebrd": (("ebrd.com",), "EBRD"),
    "european investment bank": (("eib.org",), "EIB"),
    "eib": (("eib.org",), "EIB"),
    "islamic development bank": (("isdb.org",), "IsDB"),
    "isdb": (("isdb.org",), "IsDB"),
    "international committee of the red cross": (("icrc.org",), "ICRC"),
    "icrc": (("icrc.org",), "ICRC"),
    "international rescue committee": (
        ("rescue.org",),
        "International Rescue Committee",
    ),
    "irc": (("rescue.org",), "International Rescue Committee"),
    "the irc": (("rescue.org",), "International Rescue Committee"),
    "international organization for migration": (("iom.int",), "IOM"),
    "iom": (("iom.int",), "IOM"),
    "reliefweb": (("reliefweb.int",), "ReliefWeb"),
    "reuters": (("reuters.com",), "Reuters"),
    "associated press": (("apnews.com",), "Associated Press"),
    "ap": (("apnews.com",), "Associated Press"),
    "bbc": (("bbc.com", "bbc.co.uk"), "BBC"),
    "international crisis group": (("crisisgroup.org",), "International Crisis Group"),
    "crisis group": (("crisisgroup.org",), "International Crisis Group"),
    "armed conflict location & event data": (("acleddata.com",), "ACLED"),
    "acled": (("acleddata.com",), "ACLED"),
    "iss africa": (("issafrica.org",), "ISS Africa"),
    "africa center for strategic studies": (
        ("africacenter.org",),
        "Africa Center for Strategic Studies",
    ),
}
# The full publisher map below remains the broader validation allowlist.

_DISALLOWED_SOURCE_MARKERS = (
    "licensed",
    "blog",
    "blogs",
    "social media",
    "user generated",
    "forum",
    "forums",
    "crowdsourced",
    "crowd sourced",
    "personal website",
    "wikipedia",
)

_SOCIAL_MEDIA_HOSTS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
}


def _is_permitted_public_source(claim: CurrentContextClaim) -> bool:
    if _is_disallowed_source_material(claim):
        return False

    normalized_publisher = _normalize_text(claim.publisher)
    source_url = _normalize_source_url(claim.source_url)
    if source_url is None:
        return False

    if normalized_publisher in {"acled", "armed conflict location event data"}:
        if _hostname(source_url) not in {"acleddata.com", "www.acleddata.com"}:
            return False

    if _hostname(source_url) == "api.worldbank.org":
        return False
    allowed_hosts = _publisher_host_allowlist(normalized_publisher)
    return bool(allowed_hosts and _host_matches(source_url, allowed_hosts))


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _publisher_host_allowlist(publisher: str) -> tuple[str, ...]:
    entry = _INSTITUTIONAL_PUBLISHER_HOSTS.get(publisher)
    return entry[0] if entry is not None else ()


def _hostname(url: str | None) -> str | None:
    if url is None:
        return None
    try:
        hostname = urlparse(url).hostname
    except ValueError:
        return None
    return hostname.rstrip(".").casefold() if hostname else None


def _host_matches(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    hostname = _hostname(url)
    return bool(
        hostname
        and any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed_hosts)
    )


def _is_disallowed_source_material(claim: CurrentContextClaim) -> bool:
    if _contains_source_marker(claim.source_type) or _contains_source_marker(claim.source_title):
        return True
    url = _normalize_source_url(claim.source_url)
    if url is None:
        return True
    if _is_social_media_url(url):
        return True
    parsed = urlparse(url)
    path_markers = {
        "blog",
        "blogs",
        "community",
        "forum",
        "forums",
        "profile",
        "social",
        "status",
        "user",
        "users",
    }
    path_labels = {label for label in parsed.path.casefold().split("/") if label}
    host_labels = set((_hostname(url) or "").split("."))
    path_has_marker = bool(
        path_labels & path_markers
        or re.search(
            r"(?:^|[/_-])(?:blogs?|community|forums?|profiles?|social|status|users?)(?:$|[/_-])",
            parsed.path.casefold(),
        )
    )
    return bool(path_has_marker or host_labels & {"blog", "blogs", "forum", "forums"})


def _contains_source_marker(value: str) -> bool:
    normalized = _normalize_text(value)
    return any(
        re.search(rf"\b{re.escape(marker)}\b", normalized)
        for marker in _DISALLOWED_SOURCE_MARKERS
    )


def _is_social_media_url(url: str | None) -> bool:
    if url is None:
        return False
    try:
        hostname = urlparse(url).hostname
    except ValueError:
        return False
    if not hostname:
        return False
    normalized_hostname = hostname.rstrip(".").casefold()
    return normalized_hostname in _SOCIAL_MEDIA_HOSTS or any(
        normalized_hostname.endswith(f".{host}") for host in _SOCIAL_MEDIA_HOSTS
    )


class PublicResearchGateway(Protocol):
    def search(self, prompt: str) -> tuple[CurrentContextClaim, ...]: ...


class AnthropicPublicResearchGateway:
    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        timeout_seconds: float = 60.0,
        metadata_client: object | None = None,
    ) -> None:
        self._client = Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._model_id = model_id
        self._metadata_client = metadata_client
        self._metadata_timeout_seconds = timeout_seconds

    def search(self, prompt: str) -> tuple[CurrentContextClaim, ...]:
        from anthropic import APIConnectionError, APITimeoutError

        try:
            return self._search(prompt)
        except APITimeoutError:
            raise TimeoutError("Anthropic research request timed out.") from None
        except APIConnectionError:
            raise ConnectionError("Anthropic research provider was unavailable.") from None

    def _search(self, prompt: str) -> tuple[CurrentContextClaim, ...]:
        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        response = self._create_web_search_response(messages)
        content_blocks = list(_response_content(response))

        if _value(response, "stop_reason") == "pause_turn":
            messages = [
                *messages,
                {"role": "assistant", "content": _value(response, "content", ())},
            ]
            response = self._create_web_search_response(messages, max_uses=1)
            content_blocks.extend(_response_content(response))

        selected_country = _country_from_prompt(prompt)
        artifact, grounded_segments = _extract_search_artifact(
            tuple(content_blocks), selected_country=selected_country
        )
        artifact, grounded_segments = self._resolve_one_missing_source_date(
            artifact, grounded_segments
        )
        try:
            normalization_response = self._client.messages.parse(
                model=self._model_id,
                max_tokens=MAX_SEARCH_OUTPUT_TOKENS,
                system=(
                    "Normalize the cited research synthesis into the supplied output schema. "
                    "Use only the cited source excerpts, copy the exact supporting quote, "
                    "and preserve its source metadata."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": artifact.model_dump_json(),
                    }
                ],
                output_format=ResearchClaimBatch,
            )
        except ValidationError:
            salvaged = _salvage_grounded_segments(
                grounded_segments, selected_country=selected_country
            )
            if salvaged:
                return salvaged
            raise

        parsed_output = getattr(normalization_response, "parsed_output", None)
        if isinstance(parsed_output, ResearchClaimBatch):
            valid_claims = _validate_normalized_claims(
                parsed_output.claims, artifact, selected_country=selected_country
            )
            if valid_claims:
                return valid_claims

        salvaged = _salvage_grounded_segments(
            grounded_segments, selected_country=selected_country
        )
        if salvaged:
            return salvaged
        raise ValueError("Anthropic response contained no parsed output.")

    def _resolve_one_missing_source_date(
        self,
        artifact: SearchArtifact,
        grounded_segments: tuple[tuple[str, tuple[ResearchSource, ...]], ...],
    ) -> tuple[SearchArtifact, tuple[tuple[str, tuple[ResearchSource, ...]], ...]]:
        source = next(
            (
                candidate
                for candidate in artifact.sources
                if candidate.published_at is None
                and candidate.publication_date_basis != "conflicting"
            ),
            None,
        )
        if source is None:
            return artifact, grounded_segments
        if self._metadata_client is None:
            with httpx.Client(
                timeout=self._metadata_timeout_seconds, follow_redirects=False
            ) as metadata_client:
                published_at = _fetch_article_publication_date(source.url, metadata_client)
        else:
            published_at = _fetch_article_publication_date(
                source.url, self._metadata_client
            )
        if published_at is None:
            return artifact, grounded_segments
        resolved = source.model_copy(
            update={
                "published_at": published_at,
                "publication_date_basis": "article_metadata",
            }
        )
        replacements = {resolved.url: resolved}
        updated_sources = tuple(replacements.get(item.url, item) for item in artifact.sources)
        updated_segments = tuple(
            (
                narrative,
                tuple(replacements.get(item.url, item) for item in sources),
            )
            for narrative, sources in grounded_segments
        )
        return (
            SearchArtifact(narrative=artifact.narrative, sources=updated_sources),
            updated_segments,
        )

    def _create_web_search_response(
        self, messages: list[dict[str, object]], *, max_uses: int = 2
    ):
        return self._client.beta.messages.create(
            model=self._model_id,
            max_tokens=MAX_SEARCH_OUTPUT_TOKENS,
            system=(
                "Return a concise cited synthesis in plain text, not JSON. Prefer current "
                "ICG, Reuters, AP and BBC reporting; use UN, IRC, ACLED public analysis "
                "and other approved reporting as supplements. Include publication dates."
            ),
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": max_uses,
                    "allowed_domains": list(SEARCH_ALLOWED_DOMAINS),
                }
            ],
            messages=messages,
            betas=["web-search-2025-03-05"],
        )


def _response_content(response: object) -> tuple[object, ...]:
    content = _value(response, "content", ())
    if content is None:
        return ()
    return tuple(content)


def _value(item: object, key: str, default: object = None) -> object:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _as_nonblank_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_source_url(url: object) -> str | None:
    value = _as_nonblank_string(url)
    if value is None or any(ord(character) < 32 for character in value):
        return None
    try:
        parsed = urlparse(value)
        if parsed.username is not None or parsed.password is not None:
            return value
        hostname = parsed.hostname
        if parsed.scheme not in {"http", "https"} or hostname is None:
            return value
        port = parsed.port
    except ValueError:
        return value

    normalized_scheme = parsed.scheme.casefold()
    netloc = hostname.rstrip(".").casefold()
    if ":" in netloc:
        netloc = f"[{netloc}]"
    if port is not None and not (
        (normalized_scheme == "http" and port == 80)
        or (normalized_scheme == "https" and port == 443)
    ):
        netloc = f"{netloc}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunparse(
        (normalized_scheme, netloc, path, parsed.params, parsed.query, "")
    )


def _parse_source_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None
    for display_format in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(normalized, display_format).date()
        except ValueError:
            continue
    return None


def _publication_date_from_url(url: str | None) -> date | None:
    if url is None or not _host_matches(url, ("reuters.com",)):
        return None
    path = urlparse(url).path
    match = re.search(r"/(20\d{2})/([01]\d)/([0-3]\d)(?:/|$)", path)
    if match is None:
        match = re.search(r"-(20\d{2})-([01]\d)-([0-3]\d)(?:/|$)", path)
    if match is None:
        return None
    try:
        return date(*(int(value) for value in match.groups()))
    except ValueError:
        return None


def _publication_date_from_excerpt(excerpt: str | None) -> date | None:
    if excerpt is None:
        return None
    match = re.search(
        r"\b(?:published|publication date)\s*[:|-]\s*(20\d{2}-[01]\d-[0-3]\d)\b",
        excerpt,
        re.IGNORECASE,
    )
    return _parse_source_date(match.group(1)) if match is not None else None


def _json_publication_dates(value: object) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        found = tuple(
            item
            for key, nested in value.items()
            for item in (
                (nested,)
                if key.casefold() == "datepublished" and isinstance(nested, str)
                else _json_publication_dates(nested)
            )
        )
        return found
    if isinstance(value, list):
        return tuple(item for nested in value for item in _json_publication_dates(nested))
    return ()


class _PublicationMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self._json_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value for key, value in attrs}
        if tag.casefold() == "meta":
            label = (attributes.get("property") or attributes.get("name") or "").casefold()
            content = attributes.get("content")
            if label == "article:published_time" and content:
                self.values.append(content)
        elif (
            tag.casefold() == "script"
            and (attributes.get("type") or "").casefold() == "application/ld+json"
        ):
            self._json_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_parts is not None:
            self._json_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "script" or self._json_parts is None:
            return
        payload = "".join(self._json_parts)
        self._json_parts = None
        try:
            self.values.extend(_json_publication_dates(json.loads(payload)))
        except json.JSONDecodeError:
            return


def _fetch_article_publication_date(url: str, client: object) -> date | None:
    normalized_url = _normalize_source_url(url)
    if normalized_url is None:
        return None
    parsed = urlparse(normalized_url)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or not _host_matches(normalized_url, SEARCH_ALLOWED_DOMAINS)
    ):
        return None
    try:
        with client.stream(
            "GET", normalized_url, follow_redirects=False
        ) as response:
            if not 200 <= response.status_code < 300:
                return None
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            if content_type.casefold().strip() not in {"text/html", "application/xhtml+xml"}:
                return None
            length = response.headers.get("content-length")
            if length is not None and (
                not length.isdigit() or int(length) > MAX_ARTICLE_METADATA_BYTES
            ):
                return None
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_ARTICLE_METADATA_BYTES:
                    return None
    except (AttributeError, OSError, httpx.HTTPError, TimeoutError, ValueError):
        return None
    parser = _PublicationMetadataParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    dates = {
        parsed
        for value in parser.values
        if (parsed := _parse_source_date(value)) is not None
    }
    return next(iter(dates)) if len(dates) == 1 else None


def _source_metadata(
    item: object,
) -> tuple[str | None, str | None, date | None, PUBLICATION_DATE_BASIS | None]:
    title = _as_nonblank_string(_value(item, "title"))
    url = _normalize_source_url(_value(item, "url"))
    explicit_dates = {
        parsed
        for field in ("published_at", "published_date", "publication_date")
        if (parsed := _parse_source_date(_value(item, field))) is not None
    }
    url_date = _publication_date_from_url(url)
    candidates = explicit_dates | ({url_date} if url_date is not None else set())
    if len(candidates) > 1:
        return title, url, None, "conflicting"
    if explicit_dates:
        return title, url, next(iter(explicit_dates)), "provider_metadata"
    if url_date is not None:
        return title, url, url_date, "canonical_url"
    return title, url, None, None


def _publisher_for_source_url(url: str) -> str | None:
    for hosts, publisher in _INSTITUTIONAL_PUBLISHER_HOSTS.values():
        if _host_matches(url, hosts):
            return publisher
    return None


def _merge_source(
    sources: dict[str, ResearchSource],
    *,
    title: str | None,
    url: str | None,
    published_at: date | None,
    publication_date_basis: PUBLICATION_DATE_BASIS | None,
) -> ResearchSource | None:
    normalized_url = _normalize_source_url(url)
    if not title or normalized_url is None:
        return None
    previous = sources.get(normalized_url)
    if previous is None:
        source = ResearchSource(
            title=title.strip(),
            url=normalized_url,
            publisher=_publisher_for_source_url(normalized_url),
            published_at=published_at,
            publication_date_basis=publication_date_basis,
        )
    else:
        conflict = (
            previous.publication_date_basis == "conflicting"
            or publication_date_basis == "conflicting"
            or (
                previous.published_at is not None
                and published_at is not None
                and previous.published_at != published_at
            )
        )
        source = ResearchSource(
            title=previous.title or title.strip(),
            url=previous.url,
            publisher=previous.publisher or _publisher_for_source_url(normalized_url),
            published_at=None if conflict else previous.published_at or published_at,
            publication_date_basis=(
                "conflicting"
                if conflict
                else previous.publication_date_basis or publication_date_basis
            ),
            excerpt=previous.excerpt,
        )
    sources[normalized_url] = source
    return source


def _web_search_result_items(block: object) -> tuple[object, ...]:
    nested = _value(block, "content", ())
    if isinstance(nested, Mapping):
        return (nested,)
    if isinstance(nested, (list, tuple)):
        return tuple(nested)
    return ()


def _citation_items(block: object) -> tuple[object, ...]:
    citations = _value(block, "citations", ())
    if isinstance(citations, Mapping):
        return (citations,)
    if isinstance(citations, (list, tuple)):
        return tuple(citations)
    return ()


def _country_from_prompt(prompt: str) -> str | None:
    match = re.search(r"(?m)^country:\s*([^\r\n]+)$", prompt)
    return match.group(1).strip() if match is not None else None


def _country_markers(country: str) -> tuple[str, ...]:
    normalized_country = _normalize_text(country)
    for canonical, aliases in COUNTRY_ALIASES.items():
        names = (canonical, *aliases)
        if normalized_country in {_normalize_text(name) for name in names}:
            return tuple(_normalize_text(name) for name in names)
    return (normalized_country,)


def _source_mentions_country(
    source: ResearchSource, selected_country: str | None
) -> bool:
    if selected_country is None:
        return True
    haystack = _normalize_text(f"{source.title} {source.excerpt or ''}")
    return any(
        re.search(rf"\b{re.escape(marker)}\b", haystack)
        for marker in _country_markers(selected_country)
        if marker
    )


def _quote_is_from_source(quote: str | None, excerpt: str | None) -> bool:
    if quote is None or excerpt is None:
        return False
    normalized_quote = " ".join(quote.split()).casefold()
    normalized_excerpt = " ".join(excerpt.split()).casefold()
    return bool(normalized_quote and normalized_quote in normalized_excerpt)


def _extract_search_artifact(
    content_blocks: tuple[object, ...],
    *, selected_country: str | None = None,
) -> tuple[SearchArtifact, tuple[tuple[str, tuple[ResearchSource, ...]], ...]]:
    sources: dict[str, ResearchSource] = {}
    grounded_segments: list[tuple[str, tuple[ResearchSource, ...]]] = []
    saw_search_result = False

    for block in content_blocks:
        block_type = _value(block, "type")
        if block_type == "web_search_tool_result":
            saw_search_result = True
            for item in _web_search_result_items(block):
                title, url, published_at, date_basis = _source_metadata(item)
                _merge_source(
                    sources,
                    title=title,
                    url=url,
                    published_at=published_at,
                    publication_date_basis=date_basis,
                )
        elif block_type == "text" and saw_search_result:
            text = _as_nonblank_string(_value(block, "text"))
            citations = _citation_items(block)
            if not text or not citations:
                continue
            attached_sources: list[ResearchSource] = []
            for citation in citations:
                title, url, cited_date, cited_date_basis = _source_metadata(citation)
                cited_text = _as_nonblank_string(_value(citation, "cited_text"))
                if cited_text is None or len(cited_text) > MAX_SOURCE_EXCERPT_CHARACTERS:
                    continue

                if url is None:
                    continue
                source = sources.get(url)
                if source is None or (title is not None and title != source.title):
                    continue
                excerpt_date = _publication_date_from_excerpt(cited_text)
                if excerpt_date is not None:
                    cited_date = excerpt_date
                    cited_date_basis = "source_excerpt"
                source = _merge_source(
                    sources,
                    title=source.title,
                    url=source.url,
                    published_at=cited_date,
                    publication_date_basis=cited_date_basis,
                )
                if source is None:
                    continue
                if source.excerpt is None:
                    source = source.model_copy(update={"excerpt": cited_text})
                    sources[source.url] = source
                if not _source_mentions_country(source, selected_country):
                    continue

                if source not in attached_sources:
                    attached_sources.append(source)
            if attached_sources:
                grounded_segments.append((text, tuple(attached_sources)))

    if not grounded_segments:
        raise ValueError("Public research response contained no cited synthesis.")

    resolved_urls = {
        source.url for _, attached_sources in grounded_segments for source in attached_sources
    }
    resolved_sources = tuple(
        source for url, source in sources.items() if url in resolved_urls
    )[:MAX_RETAINED_SOURCES]
    retained_urls = {source.url for source in resolved_sources}
    bounded_segments = tuple(
        (text, tuple(source for source in attached if source.url in retained_urls))
        for text, attached in grounded_segments
        if any(source.url in retained_urls for source in attached)
    )
    narrative = "\n".join(segment for segment, _ in bounded_segments)
    artifact = SearchArtifact(narrative=narrative, sources=resolved_sources)
    return artifact, bounded_segments


def _publisher_from_source(source: ResearchSource) -> str:
    return source.publisher or _publisher_for_source_url(source.url) or source.title


def _validate_normalized_claims(
    claims: tuple[CurrentContextClaim, ...],
    artifact: SearchArtifact,
    *, selected_country: str | None = None,
) -> tuple[CurrentContextClaim, ...]:
    sources_by_url = {source.url: source for source in artifact.sources}
    matched_claims: list[CurrentContextClaim] = []
    for claim in claims:
        source_url = _normalize_source_url(claim.source_url)
        if source_url is None:
            continue
        source = sources_by_url.get(source_url)
        if source is None:
            continue
        supporting_quote = _as_nonblank_string(claim.supporting_quote)
        if (
            source.published_at is None
            or not _quote_is_from_source(supporting_quote, source.excerpt)
            or not _source_mentions_country(source, selected_country)
        ):
            continue
        matched_claims.append(
            claim.model_copy(
                update={
                    "text": supporting_quote,
                    "publisher": _publisher_from_source(source),
                    "source_title": source.title,
                    "source_url": source.url,
                    "source_date": source.published_at,
                    "supporting_quote": supporting_quote,
                    "publication_date_basis": source.publication_date_basis,
                }
            )
        )

    retained, _ = retain_public_claims(tuple(matched_claims))
    return retained


def _salvage_grounded_segments(
    grounded_segments: tuple[tuple[str, tuple[ResearchSource, ...]], ...],
    *, selected_country: str | None = None,
) -> tuple[CurrentContextClaim, ...]:
    claims: list[CurrentContextClaim] = []
    seen: set[tuple[str, str]] = set()
    for _, sources in grounded_segments:
        for source in sources:
            supporting_quote = source.excerpt
            if (
                source.published_at is None
                or supporting_quote is None
                or not _is_unambiguous_single_sentence(supporting_quote)
                or not _source_mentions_country(source, selected_country)
            ):
                continue
            key = (supporting_quote, source.url)
            if key in seen:
                continue
            seen.add(key)
            digest_input = json.dumps(
                {
                    "source_date": source.published_at.isoformat(),
                    "source_title": source.title,
                    "source_url": source.url,
                    "text": supporting_quote,
                },
                sort_keys=True,
            ).encode("utf-8")
            claims.append(
                CurrentContextClaim(
                    claim_id=f"sha256:{hashlib.sha256(digest_input).hexdigest()}",
                    text=supporting_quote,
                    publisher=_publisher_from_source(source),
                    source_title=source.title,
                    source_url=source.url,
                    source_date=source.published_at,
                    supporting_quote=supporting_quote,
                    publication_date_basis=source.publication_date_basis,
                    source_type="public institutional source",
                    relevance="Salvaged from an exact cited source excerpt.",
                    context_kind="current_development",
                    relationship="establishes",
                    licensed_data_required=False,
                )
            )

    retained, _ = retain_public_claims(tuple(claims[:MAX_RETAINED_FINDINGS]))
    return retained


def _is_unambiguous_single_sentence(text: str) -> bool:
    text = text.strip()
    return (
        bool(text)
        and text[-1] in ".!?"
        and sum(text.count(mark) for mark in ".!?") == 1
    )


def load_research_prompt() -> str:
    prompt_path = Path(__file__).parents[2] / "prompts" / "public_research.md"
    return prompt_path.read_text(encoding="utf-8")
