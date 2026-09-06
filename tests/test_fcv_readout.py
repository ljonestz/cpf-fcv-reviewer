from datetime import date

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.fcv_readout import (
    FcvReadout,
    generate_fcv_readout,
    readout_caveat_limitation,
    readout_payload,
)


class _FakeGateway:
    def __init__(self, result):
        self._result = result
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append((prompt_name, payload, output_type))
        return self._result


def _readout():
    return FcvReadout(
        synthesis="Guinea remains in a fragile post-coup transition with security tensions.",
        key_themes=("CNRD-led transition and legitimacy questions", "Localised security incidents"),
        as_of_note="Based on model knowledge; not externally sourced.",
    )


def test_readout_requires_synthesis_and_at_least_one_theme():
    with pytest.raises(ValidationError):
        FcvReadout(synthesis="", key_themes=("x",))
    with pytest.raises(ValidationError):
        FcvReadout(synthesis="ok", key_themes=())


def test_generate_fcv_readout_returns_result_and_passes_prompt_and_dates():
    gateway = _FakeGateway(_readout())
    out = generate_fcv_readout(
        gateway,
        country="Guinea",
        review_date=date(2026, 9, 1),
        reference_start_date=date(2023, 6, 1),
    )
    assert isinstance(out, FcvReadout)
    prompt_name, payload, output_type = gateway.calls[0]
    assert prompt_name == "fcv_readout"
    assert output_type is FcvReadout
    assert payload["country"] == "Guinea"
    assert payload["review_date"] == "2026-09-01"
    assert payload["reference_period_start"] == "2023-06-01"


def test_generate_fcv_readout_null_reference_when_no_diagnostic_date():
    gateway = _FakeGateway(_readout())
    generate_fcv_readout(gateway, country="Guinea", review_date=date(2026, 9, 1))
    assert gateway.calls[0][1]["reference_period_start"] is None


def test_generate_fcv_readout_returns_none_for_wrong_type():
    gateway = _FakeGateway(object())
    assert generate_fcv_readout(gateway, country="Guinea", review_date=date(2026, 9, 1)) is None


def test_readout_payload_is_context_only_and_labelled():
    payload = readout_payload(_readout())
    assert set(payload) == {"provenance", "synthesis", "key_themes", "as_of_note"}
    assert "no external current sources" in payload["provenance"].casefold()
    assert isinstance(payload["key_themes"], list) and len(payload["key_themes"]) == 2


def test_readout_caveat_limitation_carries_caveat_synthesis_and_themes():
    text = readout_caveat_limitation(_readout())
    assert "ai-generated readout" in text.casefold()
    assert "no external current sources" in text.casefold()
    assert "post-coup transition" in text
    assert "(1)" in text and "(2)" in text


def test_review_prompt_documents_readout_fallback():
    from cpf_fcv_reviewer.prompts import load_prompt

    prompt = load_prompt("review").casefold()
    assert "current_context_readout" in prompt
    assert "ai-generated" in prompt
    assert "no external current sources" in prompt


def test_preserve_research_limitation_appends_readout_caveat():
    from types import SimpleNamespace

    from cpf_fcv_reviewer.runtime import _preserve_research_limitation

    class _Result:
        def __init__(self, limitations):
            self.limitations = limitations

        def model_copy(self, *, update):
            self.limitations = tuple(update["limitations"])
            return self

    context = {
        "result": _Result(("Existing limitation.",)),
        "research_result": SimpleNamespace(limitation=None),
        "fcv_readout": _readout(),
    }
    out = _preserve_research_limitation(context)
    joined = " ".join(out.limitations).casefold()
    assert "ai-generated readout" in joined
    assert "post-coup transition" in " ".join(out.limitations)


def test_load_prompt_supports_fcv_readout():
    from cpf_fcv_reviewer.prompts import PROMPT_NAMES, load_prompt

    assert "fcv_readout" in PROMPT_NAMES
    text = load_prompt("fcv_readout").casefold()
    assert "fcv" in text and "current" in text and "readout" in text
