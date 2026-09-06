"""AI-generated FCV current-context readout fallback.

When independent current-country research yields no external sources (the review would
otherwise be entirely document-led with no present-day context), we fall back to a bounded,
knowledge-based readout from the model of current FCV conditions in the country. It is
represented as context-only, clearly caveated ("no external current sources were available;
AI-generated readout; verify before use") and never as a cited source. This keeps the
review's "current snapshot" informed rather than empty, which the maintainer judged more
useful than no current context at all.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class FcvReadout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    synthesis: str = Field(min_length=1, max_length=2500)
    key_themes: tuple[str, ...] = Field(min_length=1, max_length=8)
    as_of_note: str = Field(default="", max_length=400)


def generate_fcv_readout(
    model_gateway,
    *,
    country: str,
    review_date: date,
    reference_start_date: date | None = None,
) -> FcvReadout | None:
    """Return a knowledge-based FCV readout, or None if the gateway did not produce one.

    The caller wraps this in best-effort handling: a readout failure must never fail a run.
    """
    payload = {
        "country": country,
        "review_date": review_date.isoformat(),
        "reference_period_start": (
            reference_start_date.isoformat() if reference_start_date is not None else None
        ),
    }
    result = model_gateway.generate(
        prompt_name="fcv_readout",
        payload=payload,
        output_type=FcvReadout,
    )
    return result if isinstance(result, FcvReadout) else None


def readout_payload(readout: FcvReadout) -> dict[str, object]:
    """Compact representation injected into the review prompt payload."""
    return {
        "provenance": (
            "AI-generated from the model's own knowledge; no external current sources were "
            "available. Context-only; verify before use."
        ),
        "synthesis": readout.synthesis,
        "key_themes": list(readout.key_themes),
        "as_of_note": readout.as_of_note,
    }


def readout_caveat_limitation(readout: FcvReadout) -> str:
    """A single, self-contained limitation entry that surfaces the readout with its caveat."""
    themes = " ".join(
        f"({index + 1}) {theme.strip()}"
        for index, theme in enumerate(readout.key_themes)
        if theme.strip()
    )
    parts = [
        "Current FCV context below is an AI-generated readout from the model's own knowledge, "
        "used because no external current sources could be established for this run; it is "
        "indicative only and must be verified before use.",
        readout.synthesis.strip(),
    ]
    if themes:
        parts.append(f"Key themes: {themes}")
    if readout.as_of_note.strip():
        parts.append(readout.as_of_note.strip())
    return " ".join(parts)
