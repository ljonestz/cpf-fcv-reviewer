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
# Constrained decoding rejects schemas whose compiled grammar is too large (the review
# draft on Opus 5.5). Those types fall back to a schema-in-prompt request whose reply is
# validated locally, so an invalid reply still raises ValidationError for the retry.
GRAMMAR_TOO_LARGE_MARKER = "compiled grammar is too large"
SCHEMA_INSTRUCTION = (
    "\n\nReturn only one JSON object that validates against the JSON Schema below. "
    "Do not add code fences or any other text.\n"
)


def _is_grammar_too_large(error: Exception) -> bool:
    return (
        getattr(error, "status_code", None) == 400
        and GRAMMAR_TOO_LARGE_MARKER in str(error).casefold()
    )


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


class AnthropicModelGateway:
    def __init__(self, api_key: str, model_id: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id
        self._prompt_schema_types: set[type] = set()

    def _stream(self, *, system: str, payload: dict, **options):
        with self.client.messages.stream(
            model=self.model_id,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
            output_config={"effort": REVIEW_EFFORT},
            **options,
        ) as stream:
            response = stream.get_final_message()
        if getattr(response, "stop_reason", None) == "refusal":
            raise ValueError("Anthropic response was declined.")
        return response

    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel:
        prompt = load_prompt(prompt_name)
        if output_type not in self._prompt_schema_types:
            try:
                response = self._stream(
                    system=prompt, payload=payload, output_format=output_type
                )
            except Exception as error:
                if not _is_grammar_too_large(error):
                    raise
                self._prompt_schema_types.add(output_type)
            else:
                parsed = getattr(response, "parsed_output", None)
                if not isinstance(parsed, output_type):
                    raise ValueError("Anthropic response contained no parsed output.")
                return parsed
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        response = self._stream(system=prompt + SCHEMA_INSTRUCTION + schema, payload=payload)
        text = "".join(
            getattr(block, "text", "")
            for block in getattr(response, "content", ())
            if getattr(block, "type", None) == "text"
        )
        return output_type.model_validate_json(_strip_code_fence(text))
