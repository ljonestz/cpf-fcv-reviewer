from __future__ import annotations

from hashlib import sha256
from pathlib import Path

PROMPT_ROOT = Path(__file__).parents[2] / "prompts"
PROMPT_NAMES = frozenset(
    {"diagnostic_map", "review", "repair", "follow_on", "fcv_readout"}
)


def load_prompt(name: str) -> str:
    if name not in PROMPT_NAMES:
        raise ValueError(f"Unknown prompt: {name!r}")
    return (PROMPT_ROOT / f"{name}.md").read_text(encoding="utf-8")


def prompt_hash(name: str) -> str:
    return sha256(load_prompt(name).encode("utf-8")).hexdigest()
