from __future__ import annotations

import json
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from .prompts import load_prompt

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ModelGateway(Protocol):
    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel: ...


class AnthropicModelGateway:
    def __init__(self, api_key: str, model_id: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id

    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel:
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=12000,
            system=load_prompt(prompt_name),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
        )
        text_parts = (
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
            and isinstance(getattr(block, "text", None), str)
        )
        text = "\n".join(part for part in text_parts if part.strip()).strip()
        if not text:
            raise ValueError("Anthropic response contained no text content.")
        return output_type.model_validate_json(text)
