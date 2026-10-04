"""Optional mAI Desktop DEV transport; never use Desktop identity for hosting."""

from __future__ import annotations

import json
import ssl
from dataclasses import replace
from threading import Lock

import httpx

from .contracts import CurrentEvidenceTier
from .model_gateway import ModelOutputUnavailable
from .prompts import load_prompt
from .research_controller import ResearchController

MODEL_ID = "us.anthropic.claude-sonnet-4-6"
ENDPOINT = f"https://azapimdev.worldbank.org/maifactory/bedrock/model/{MODEL_ID}/converse"
RESEARCH_LIMITATION = (
    "Local development review uses institutional-source research only; "
    "broad web search was not performed. "
)


class MaiUnavailable(RuntimeError):
    """Sanitized transport/authentication failure without provider response text."""


class MaiDesktopGateway:
    def __init__(self, team_name: str, *, token_provider=None, client=None):
        if (not isinstance(team_name, str) or not team_name.strip()
                or not team_name.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in team_name)):
            raise ValueError("A valid mAI team name is required.")
        self.team_name = team_name.strip()
        self.model_id = MODEL_ID
        self._token_provider = token_provider
        self._desktop = None
        self._auth_lock = Lock()
        self._client = client or httpx.Client(
            # Windows trust includes the enterprise roots; verification stays enabled.
            verify=ssl.create_default_context(),
            timeout=httpx.Timeout(300, connect=10), follow_redirects=False,
        )

    def _token(self):
        # MSAL/WAM access is serialized; get_token refreshes through MSAL rather
        # than the installed SDK's token_provider, which caches indefinitely.
        with self._auth_lock:
            try:
                if self._token_provider is not None:
                    return self._token_provider()
                if self._desktop is None:
                    from itsai.platform.authentication import DesktopToken

                    self._desktop = DesktopToken()
                return self._desktop.get_token(env="DEV")
            except Exception:
                raise MaiUnavailable("mAI Desktop sign-in is unavailable.") from None

    def authenticate(self):
        """Sign in on the main thread before background assessment work."""
        self._token()

    def _complete(self, *, system, messages, max_tokens, schema=None):
        payload = {
            "system": [{"text": system}],
            "messages": [
                {"role": message["role"], "content": [{"text": message["content"]}]}
                for message in messages
            ],
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        if schema is not None:
            payload["outputConfig"] = {"textFormat": {
                "type": "json_schema", "structure": {"jsonSchema": {
                    "name": "cpf_review", "schema": json.dumps(schema),
                }},
            }}
        try:
            response = self._client.post(ENDPOINT, json=payload, headers={
                "Authorization": "Bearer " + self._token(),
                "x-source-type": "interactive", "x-team-name": self.team_name,
            })
        except httpx.HTTPError:
            raise MaiUnavailable("mAI request failed; no automatic retry was made.") from None
        if response.status_code != 200:
            raise MaiUnavailable(f"mAI returned HTTP {response.status_code}.")
        try:
            body = response.json()
            stop_reason = body.get("stopReason")
            if stop_reason != "end_turn":
                raise ModelOutputUnavailable(stop_reason)
            text = "".join(block["text"] for block in body["output"]["message"]["content"]
                           if "text" in block)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise MaiUnavailable("mAI returned an invalid response envelope.") from None
        if not text.strip():
            raise MaiUnavailable("mAI returned no usable text.")
        return text

    def generate(self, *, prompt_name, payload, output_type):
        from anthropic import transform_schema

        text = self._complete(
            system=load_prompt(prompt_name),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            max_tokens=20000 if prompt_name in {"review", "repair"} else 12000,
            schema=transform_schema(output_type.model_json_schema()),
        )
        return output_type.model_validate_json(text)

    def stream(self, *, review, evidence, history, message):
        # ponytail: one complete chunk for local testing; add native streaming
        # only after the gateway's streaming protocol has been verified.
        yield self._complete(
            system=load_prompt("follow_on"), max_tokens=4000,
            messages=[
                {"role": "user", "content": json.dumps(
                    {"review": review, "evidence": evidence}, ensure_ascii=False)},
                *history, {"role": "user", "content": message},
            ],
        )


class NoBroadWebSearch:
    """Select existing institutional recovery without calling a paid search API."""

    def search(self, prompt):
        return ()


class InstitutionalResearchController(ResearchController):
    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        return replace(
            result,
            tier=(CurrentEvidenceTier.REDUCED
                  if result.tier is CurrentEvidenceTier.FULL else result.tier),
            limitation=RESEARCH_LIMITATION + (result.limitation or ""),
        )
