from __future__ import annotations

from collections import Counter
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
    source_url: str | None
    source_date: date
    source_type: str
    relevance: str
    relationship: Literal["corroborates", "qualifies", "contradicts", "unresolved"]
    licensed_data_required: StrictBool

    @field_validator("claim_id", "text", "source_type")
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


class PublicResearchGateway(Protocol):
    def search(self, prompt: str) -> str: ...


class AnthropicPublicResearchGateway:
    def __init__(self, api_key: str, model_id: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model_id = model_id

    def search(self, prompt: str) -> str:
        response = self._client.beta.messages.create(
            model=self._model_id,
            max_tokens=5000,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            betas=["web-search-2025-03-05"],
        )
        return "\n".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()


def load_research_prompt() -> str:
    prompt_path = Path(__file__).parents[2] / "prompts" / "public_research.md"
    return prompt_path.read_text(encoding="utf-8")
