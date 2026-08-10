from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class SourceCandidate:
    source_id: str
    title: str
    version: str
    source_kind: Literal[
        "upload",
        "sharepoint_original",
        "approved_summary",
        "derived_copy",
        "public_web",
    ]
    is_current: bool


class RraSourceAdapter(Protocol):
    def candidates(self, country: str) -> tuple[SourceCandidate, ...]: ...


def choose_authoritative_source(
    candidates: tuple[SourceCandidate, ...],
) -> SourceCandidate | None:
    current_originals = [
        item
        for item in candidates
        if item.is_current and item.source_kind == "sharepoint_original"
    ]
    if len(current_originals) == 1:
        return current_originals[0]
    if len(current_originals) > 1:
        return None

    current_uploads = [
        item for item in candidates if item.is_current and item.source_kind == "upload"
    ]
    return current_uploads[0] if len(current_uploads) == 1 else None
