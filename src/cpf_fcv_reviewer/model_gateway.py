from __future__ import annotations

import json
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .prompts import load_prompt

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class _LazyAnthropicModule:
    @staticmethod
    def Anthropic(*args, **kwargs):
        from anthropic import Anthropic

        return Anthropic(*args, **kwargs)


anthropic = _LazyAnthropicModule()


class ModelOutputUnavailable(RuntimeError):
    """Withhold incomplete generations without exposing their content."""

    def __init__(self, stop_reason: object) -> None:
        self.failure_code = {
            "max_tokens": "model_output_truncated",
            "refusal": "model_refusal",
        }.get(stop_reason, "model_output_unavailable")
        super().__init__("Model generation did not complete safely.")


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
        from anthropic import transform_schema

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
            output_config={"format": {
                "type": "json_schema",
                "schema": transform_schema(output_type.model_json_schema()),
            }},
        )
        # Check provider termination before parsing; truncated structured JSON
        # must not consume an identical schema-correction call or be released.
        if response.stop_reason != "end_turn":
            raise ModelOutputUnavailable(response.stop_reason)
        content = "".join(block.text for block in response.content if block.type == "text")
        if not content.strip():
            raise ValueError("Anthropic response contained no JSON output.")
        return output_type.model_validate_json(content)
