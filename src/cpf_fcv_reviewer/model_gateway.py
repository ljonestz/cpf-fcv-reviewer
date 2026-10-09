from __future__ import annotations

import json
import logging
from time import sleep
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .prompts import load_prompt

OutputModel = TypeVar("OutputModel", bound=BaseModel)
logger = logging.getLogger(__name__)


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


# Long streamed requests can be interrupted after HTTP 200 (an error event mid-stream,
# such as overloaded_error), which the SDK does not retry. Retry those and other
# transient failures a bounded number of times with backoff.
TRANSIENT_RETRY_DELAYS_SECONDS = (15.0, 45.0)
_TRANSIENT_STATUS_CODES = frozenset({200, 408, 429, 500, 502, 503, 504, 529})
_TRANSIENT_ERROR_NAMES = frozenset(
    {"APIConnectionError", "APITimeoutError", "RemoteProtocolError", "ReadError"}
)


def _is_transient(error: Exception) -> bool:
    return (
        getattr(error, "status_code", None) in _TRANSIENT_STATUS_CODES
        or type(error).__name__ in _TRANSIENT_ERROR_NAMES
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
        for attempt in range(len(TRANSIENT_RETRY_DELAYS_SECONDS) + 1):
            try:
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
                break
            except Exception as error:
                if attempt == len(TRANSIENT_RETRY_DELAYS_SECONDS) or not _is_transient(error):
                    raise
                body = getattr(error, "body", None)
                api_error = body.get("error") if isinstance(body, dict) else None
                logger.warning(
                    "model_stream_retry attempt=%d error_type=%s status_code=%s api_error=%s",
                    attempt + 1,
                    type(error).__name__,
                    getattr(error, "status_code", None),
                    api_error.get("type") if isinstance(api_error, dict) else None,
                )
                sleep(TRANSIENT_RETRY_DELAYS_SECONDS[attempt])
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
