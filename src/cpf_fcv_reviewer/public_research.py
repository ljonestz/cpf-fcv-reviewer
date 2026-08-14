from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import date
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlparse

from anthropic import Anthropic
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator


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


_INSTITUTIONAL_PUBLISHER_PATTERNS = (
    r"\bworld bank\b",
    r"\bunited nations\b",
    r"\b(?:unhcr|undp|ocha|wfp|who|unicef|unep|unodc|undrr|un women)\b",
    r"\boecd\b",
    r"\b(?:international monetary fund|imf)\b",
    r"\b(?:african development bank|afdb)\b",
    r"\b(?:asian development bank|adb)\b",
    r"\b(?:inter american development bank|iadb|idb)\b",
    r"\b(?:european bank for reconstruction and development|ebrd)\b",
    r"\b(?:european investment bank|eib)\b",
    r"\b(?:islamic development bank|isdb)\b",
    r"\b(?:caribbean development bank|central american bank for economic integration)\b",
    r"\b(?:international committee of the red cross|icrc)\b",
    r"\b(?:international organization for migration|iom)\b",
    r"\breliefweb\b",
)

_DISALLOWED_SOURCE_TYPE_TERMS = (
    "licensed",
    "blog",
    "social media",
    "user-generated",
    "user generated",
    "forum",
    "crowdsourced",
    "crowd-sourced",
    "personal website",
    "personal blog",
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
    normalized_publisher = re.sub(r"[^a-z0-9]+", " ", claim.publisher.casefold()).strip()
    is_institutional = any(
        re.search(pattern, normalized_publisher) for pattern in _INSTITUTIONAL_PUBLISHER_PATTERNS
    )
    is_national_government = any(
        phrase in normalized_publisher
        for phrase in (
            "government of ",
            "ministry of ",
            "national bureau of statistics",
            "national statistics office",
            "federal government of ",
            "republic of ",
        )
    )
    if not (is_institutional or is_national_government):
        return False

    normalized_source_type = claim.source_type.casefold()
    if any(term in normalized_source_type for term in _DISALLOWED_SOURCE_TYPE_TERMS):
        return False
    return not _is_social_media_url(claim.source_url)


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
        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        response = self._create_web_search_response(messages)
        content_blocks = list(_response_content(response))

        if getattr(response, "stop_reason", None) == "pause_turn":
            messages = [
                *messages,
                {"role": "assistant", "content": response.content},
            ]
            response = self._create_web_search_response(messages)
            content_blocks.extend(_response_content(response))

        artifact, cited_sentences = _extract_search_artifact(tuple(content_blocks))
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
        parsed_output = getattr(normalization_response, "parsed_output", None)
        if isinstance(parsed_output, ResearchClaimBatch):
            return tuple(parsed_output.claims)

        salvaged = _salvage_cited_sentences(cited_sentences)
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
    content = getattr(response, "content", ())
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


def _parse_source_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _source_metadata(item: object) -> tuple[str | None, str | None, date | None]:
    title = _as_nonblank_string(_value(item, "title"))
    url = _as_nonblank_string(_value(item, "url"))
    published_at = _parse_source_date(
        next(
            (
                _value(item, field)
                for field in ("published_at", "published_date", "publication_date", "date")
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
    if not title or not url:
        return None
    previous = sources.get(url)
    if previous is None:
        source = ResearchSource(title=title, url=url, published_at=published_at)
    else:
        source = ResearchSource(
            title=previous.title or title,
            url=previous.url,
            published_at=previous.published_at or published_at,
        )
    sources[url] = source
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
) -> tuple[SearchArtifact, tuple[tuple[str, ResearchSource], ...]]:
    sources: dict[str, ResearchSource] = {}
    final_text_block: object | None = None
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
            if text:
                final_text_block = block

    if final_text_block is None:
        raise ValueError("Public research response contained no cited synthesis.")

    narrative = _as_nonblank_string(_value(final_text_block, "text"))
    if narrative is None:
        raise ValueError("Public research response contained no cited synthesis.")

    cited_sentences: list[tuple[str, ResearchSource]] = []
    for citation in _citation_items(final_text_block):
        title, url, published_at = _source_metadata(citation)
        source = _merge_source(
            sources,
            title=title,
            url=url,
            published_at=published_at,
        )
        if source is None or source.url not in sources:
            continue
        sentence = _sentence_for_citation(narrative, citation)
        if sentence:
            cited_sentences.append((sentence, sources[source.url]))

    return SearchArtifact(narrative=narrative, sources=tuple(sources.values())), tuple(
        cited_sentences
    )


def _sentence_spans(text: str) -> tuple[tuple[int, int, str], ...]:
    spans: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", text, flags=re.DOTALL):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
        end = start + len(sentence)
        spans.append((start, end, sentence))
    return tuple(spans)


def _sentence_for_citation(text: str, citation: object) -> str | None:
    cited_text = _as_nonblank_string(_value(citation, "cited_text"))
    if cited_text:
        cited_start = text.find(cited_text)
        if cited_start >= 0:
            cited_end = cited_start + len(cited_text)
            for start, end, sentence in _sentence_spans(text):
                if start <= cited_start and cited_end <= end:
                    return sentence

    start = _value(citation, "start_char_index")
    end = _value(citation, "end_char_index")
    if isinstance(start, int) and isinstance(end, int) and start < end:
        for sentence_start, sentence_end, sentence in _sentence_spans(text):
            if sentence_start < end and start < sentence_end:
                return sentence
    return None


def _publisher_from_source(source: ResearchSource) -> str:
    hostname = urlparse(source.url).hostname or ""
    normalized_hostname = hostname.rstrip(".").casefold()
    host_publishers = (
        (("worldbank.org",), "World Bank"),
        (("un.org",), "United Nations"),
        (("oecd.org",), "OECD"),
        (("imf.org",), "International Monetary Fund"),
        (("afdb.org",), "African Development Bank"),
        (("adb.org",), "Asian Development Bank"),
        (("iadb.org",), "Inter-American Development Bank"),
        (("icrc.org",), "International Committee of the Red Cross"),
        (("iom.int",), "International Organization for Migration"),
        (("reliefweb.int",), "ReliefWeb"),
    )
    for domains, publisher in host_publishers:
        if any(
            normalized_hostname == domain or normalized_hostname.endswith(f".{domain}")
            for domain in domains
        ):
            return publisher
    return source.title


def _salvage_cited_sentences(
    cited_sentences: tuple[tuple[str, ResearchSource], ...],
) -> tuple[CurrentContextClaim, ...]:
    claims: list[CurrentContextClaim] = []
    seen: set[tuple[str, str]] = set()
    for sentence, source in cited_sentences:
        if source.published_at is None:
            continue
        key = (sentence, source.url)
        if key in seen:
            continue
        seen.add(key)
        digest_input = json.dumps(
            {
                "source_date": source.published_at.isoformat(),
                "source_title": source.title,
                "source_url": source.url,
                "text": sentence,
            },
            sort_keys=True,
        ).encode("utf-8")
        claims.append(
            CurrentContextClaim(
                claim_id=f"sha256:{hashlib.sha256(digest_input).hexdigest()}",
                text=sentence,
                publisher=_publisher_from_source(source),
                source_title=source.title,
                source_url=source.url,
                source_date=source.published_at,
                source_type="public institutional source",
                relevance="Salvaged from a sentence with an explicit source citation.",
                context_kind="current_development",
                relationship="establishes",
                licensed_data_required=False,
            )
        )
    return tuple(claims)


def load_research_prompt() -> str:
    prompt_path = Path(__file__).parents[2] / "prompts" / "public_research.md"
    return prompt_path.read_text(encoding="utf-8")
