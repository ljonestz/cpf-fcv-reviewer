from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError, field_validator


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
    published_at: date | None = None


class SearchArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    narrative: str
    sources: tuple[ResearchSource, ...]


class ResearchClaimBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claims: tuple[CurrentContextClaim, ...]


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
    "international organization for migration": (("iom.int",), "IOM"),
    "iom": (("iom.int",), "IOM"),
    "reliefweb": (("reliefweb.int",), "ReliefWeb"),
}

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
    ) -> None:
        self._client = Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._model_id = model_id

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
            response = self._create_web_search_response(messages)
            content_blocks.extend(_response_content(response))

        artifact, grounded_segments = _extract_search_artifact(tuple(content_blocks))
        try:
            normalization_response = self._client.messages.parse(
                model=self._model_id,
                max_tokens=5000,
                system=(
                    "Normalize the cited research synthesis into the supplied output schema. "
                    "Use only the cited narrative and preserve its source metadata."
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
            salvaged = _salvage_grounded_segments(grounded_segments)
            if salvaged:
                return salvaged
            raise

        parsed_output = getattr(normalization_response, "parsed_output", None)
        if isinstance(parsed_output, ResearchClaimBatch):
            valid_claims = _validate_normalized_claims(parsed_output.claims, artifact)
            if valid_claims:
                return valid_claims

        salvaged = _salvage_grounded_segments(grounded_segments)
        if salvaged:
            return salvaged
        raise ValueError("Anthropic response contained no parsed output.")

    def _create_web_search_response(self, messages: list[dict[str, object]]):
        return self._client.beta.messages.create(
            model=self._model_id,
            max_tokens=5000,
            system=(
                "Return a concise cited synthesis in plain text, not JSON. "
                "Use source-linked claims and include publication dates when available."
            ),
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
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


def _source_metadata(item: object) -> tuple[str | None, str | None, date | None]:
    title = _as_nonblank_string(_value(item, "title"))
    url = _normalize_source_url(_value(item, "url"))
    published_at = _parse_source_date(
        next(
            (
                _value(item, field)
                for field in (
                    "page_age",
                    "published_at",
                    "published_date",
                    "publication_date",
                    "date",
                )
                if _value(item, field) is not None
            ),
            None,
        )
    )
    return title, url, published_at


def _merge_source(
    sources: dict[str, ResearchSource],
    *,
    title: str | None,
    url: str | None,
    published_at: date | None,
) -> ResearchSource | None:
    normalized_url = _normalize_source_url(url)
    if not title or normalized_url is None:
        return None
    previous = sources.get(normalized_url)
    if previous is None:
        source = ResearchSource(title=title.strip(), url=normalized_url, published_at=published_at)
    else:
        source = ResearchSource(
            title=previous.title or title.strip(),
            url=previous.url,
            published_at=previous.published_at or published_at,
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


def _extract_search_artifact(
    content_blocks: tuple[object, ...],
) -> tuple[SearchArtifact, tuple[tuple[str, tuple[ResearchSource, ...]], ...]]:
    sources: dict[str, ResearchSource] = {}
    grounded_segments: list[tuple[str, tuple[ResearchSource, ...]]] = []
    saw_search_result = False

    for block in content_blocks:
        block_type = _value(block, "type")
        if block_type == "web_search_tool_result":
            saw_search_result = True
            for item in _web_search_result_items(block):
                title, url, published_at = _source_metadata(item)
                _merge_source(
                    sources,
                    title=title,
                    url=url,
                    published_at=published_at,
                )
        elif block_type == "text" and saw_search_result:
            text = _as_nonblank_string(_value(block, "text"))
            citations = _citation_items(block)
            if not text or not citations:
                continue
            attached_sources: list[ResearchSource] = []
            for citation in citations:
                title, url, _ = _source_metadata(citation)
                if url is None:
                    continue
                source = sources.get(url)
                if source is None or (title is not None and title != source.title):
                    continue
                if source not in attached_sources:
                    attached_sources.append(source)
            if attached_sources:
                grounded_segments.append((text, tuple(attached_sources)))

    if not grounded_segments:
        raise ValueError("Public research response contained no cited synthesis.")

    narrative = "\n".join(segment for segment, _ in grounded_segments)
    resolved_urls = {
        source.url for _, attached_sources in grounded_segments for source in attached_sources
    }
    resolved_sources = tuple(source for url, source in sources.items() if url in resolved_urls)
    return SearchArtifact(narrative=narrative, sources=resolved_sources), tuple(grounded_segments)


def _publisher_from_source(source: ResearchSource) -> str:
    for hosts, publisher in _INSTITUTIONAL_PUBLISHER_HOSTS.values():
        if _host_matches(source.url, hosts):
            return publisher
    return source.title


def _validate_normalized_claims(
    claims: tuple[CurrentContextClaim, ...], artifact: SearchArtifact
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
        if claim.source_title != source.title:
            continue
        if source.published_at is None or claim.source_date != source.published_at:
            continue
        matched_claims.append(claim.model_copy(update={"source_url": source.url}))

    retained, _ = retain_public_claims(tuple(matched_claims))
    return retained


def _salvage_grounded_segments(
    grounded_segments: tuple[tuple[str, tuple[ResearchSource, ...]], ...],
) -> tuple[CurrentContextClaim, ...]:
    claims: list[CurrentContextClaim] = []
    seen: set[tuple[str, str]] = set()
    for narrative, sources in grounded_segments:
        if not _is_unambiguous_single_sentence(narrative):
            continue
        for source in sources:
            if source.published_at is None:
                continue
            key = (narrative, source.url)
            if key in seen:
                continue
            seen.add(key)
            digest_input = json.dumps(
                {
                    "source_date": source.published_at.isoformat(),
                    "source_title": source.title,
                    "source_url": source.url,
                    "text": narrative,
                },
                sort_keys=True,
            ).encode("utf-8")
            claims.append(
                CurrentContextClaim(
                    claim_id=f"sha256:{hashlib.sha256(digest_input).hexdigest()}",
                    text=narrative,
                    publisher=_publisher_from_source(source),
                    source_title=source.title,
                    source_url=source.url,
                    source_date=source.published_at,
                    source_type="public institutional source",
                    relevance="Salvaged from a cited synthesis block.",
                    context_kind="current_development",
                    relationship="establishes",
                    licensed_data_required=False,
                )
            )

    retained, _ = retain_public_claims(tuple(claims))
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
