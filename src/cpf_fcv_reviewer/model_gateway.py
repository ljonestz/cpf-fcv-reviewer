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


class ModelGateway(Protocol):
    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel: ...


# Output budget covers adaptive thinking plus the structured result. Requests this
# large must stream, or the SDK refuses them to avoid HTTP timeouts.
MAX_OUTPUT_TOKENS = 64_000
REVIEW_EFFORT = "high"


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
        with self.client.messages.stream(
            model=self.model_id,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=load_prompt(prompt_name),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
            output_format=output_type,
            output_config={"effort": REVIEW_EFFORT},
        ) as stream:
            response = stream.get_final_message()
        if getattr(response, "stop_reason", None) == "refusal":
            raise ValueError("Anthropic response was declined.")
        parsed = getattr(response, "parsed_output", None)
        if not isinstance(parsed, output_type):
            raise ValueError("Anthropic response contained no parsed output.")
        return parsed
