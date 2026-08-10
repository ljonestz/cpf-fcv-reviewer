from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlparse

from anthropic import Anthropic
from pydantic import BaseModel, ConfigDict


class CurrentContextClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    text: str
    source_url: str | None = None
    source_date: date
    source_type: str
    relevance: str
    relationship: Literal["corroborates", "qualifies", "contradicts", "unresolved"]
    licensed_data_required: bool


def retain_public_claims(
    claims: tuple[CurrentContextClaim, ...],
) -> tuple[tuple[CurrentContextClaim, ...], dict[str, str]]:
    retained: list[CurrentContextClaim] = []
    rejected: dict[str, str] = {}

    for claim in claims:
        if claim.licensed_data_required:
            rejected[claim.claim_id] = "licensed data is not permitted"
        elif not _is_public_http_url(claim.source_url):
            rejected[claim.claim_id] = "public source URL is required"
        elif not claim.relevance.strip():
            rejected[claim.claim_id] = "relevance is required"
        else:
            retained.append(claim)

    return tuple(retained), rejected


def _is_public_http_url(url: str | None) -> bool:
    if url is None:
        return False

    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class PublicResearchGateway(Protocol):
    def search(self, question: str) -> str: ...


class AnthropicPublicResearchGateway:
    def __init__(self, api_key: str, model_id: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model_id = model_id

    def search(self, question: str) -> str:
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
                    "content": f"{load_public_research_prompt()}\n\nQuestion: {question}",
                }
            ],
            betas=["web-search-2025-03-05"],
        )
        return "\n".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )


def load_public_research_prompt() -> str:
    prompt_path = Path(__file__).parents[2] / "prompts" / "public_research.md"
    return prompt_path.read_text(encoding="utf-8")
