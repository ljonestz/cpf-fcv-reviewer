from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

SOURCE_KINDS = frozenset(
    {
        "upload",
        "sharepoint_original",
        "approved_summary",
        "derived_copy",
        "public_web",
    }
)


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

    def __post_init__(self) -> None:
        for field_name in ("source_id", "title", "version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be nonblank text.")
        if not isinstance(self.source_kind, str) or self.source_kind not in SOURCE_KINDS:
            raise ValueError("source_kind must be an approved source kind.")
        if type(self.is_current) is not bool:
            raise ValueError("is_current must be a bool.")


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
