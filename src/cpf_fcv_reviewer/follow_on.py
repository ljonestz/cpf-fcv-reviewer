"""Bounded, evidence-grounded follow-on assistance for completed reviews."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Protocol

from .prompts import load_prompt


class _LazyAnthropicModule:
    @staticmethod
    def Anthropic(*args, **kwargs):
        from anthropic import Anthropic

        return Anthropic(*args, **kwargs)


anthropic = _LazyAnthropicModule()


class FollowOnGateway(Protocol):
    def stream(
        self,
        *,
        review: dict,
        evidence: dict,
        history: tuple[dict[str, str], ...],
        message: str,
    ) -> Iterator[str]: ...


class AnthropicFollowOnGateway:
    """Stream one bounded follow-on response from the configured Anthropic model."""

    def __init__(self, api_key: str, model_id: str) -> None:
        self._api_key = api_key
        self._client = None
        self.model_id = model_id

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def stream(
        self,
        *,
        review: dict,
        evidence: dict,
        history: tuple[dict[str, str], ...],
        message: str,
    ) -> Iterator[str]:
        messages = [
            {
                "role": "user",
                "content": json.dumps(
                    {"review": review, "evidence": evidence},
                    ensure_ascii=False,
                ),
            },
            *history,
            {"role": "user", "content": message},
        ]
        with self.client.messages.stream(
            model=self.model_id,
            max_tokens=4000,
            system=load_prompt("follow_on"),
            messages=messages,
        ) as response:
            yield from response.text_stream
