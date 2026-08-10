from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import (
    DiagnosticEntry,
    DiagnosticMode,
    EvidenceItem,
    EvidencePack,
    RunMetadata,
    UserCorrection,
)
from .diagnostic_map import prioritize, validate_diagnostic_coverage


@dataclass(frozen=True)
class DocumentRole:
    role: Literal["cpf", "rra", "diagnostic", "results", "comments", "other"]
    name: str
    readable: bool
    accepted_equivalent: bool


def select_diagnostic_mode(
    documents: tuple[DocumentRole, ...],
) -> DiagnosticMode:
    for document in documents:
        if not document.readable:
            continue
        if document.role == "rra":
            return DiagnosticMode.RRA_ALIGNMENT
        if document.role == "diagnostic" and document.accepted_equivalent:
            return DiagnosticMode.RRA_ALIGNMENT
    return DiagnosticMode.LIMITED_FRAMING


def build_evidence_pack(
    *,
    metadata: RunMetadata,
    evidence: tuple[EvidenceItem, ...],
    diagnostic_entries: tuple[DiagnosticEntry, ...],
    material_diagnostic_ids: tuple[str, ...],
    corrections: tuple[UserCorrection, ...] = (),
    warnings: tuple[str, ...] = (),
) -> EvidencePack:
    if metadata.diagnostic_mode == DiagnosticMode.RRA_ALIGNMENT:
        validate_diagnostic_coverage(material_diagnostic_ids, diagnostic_entries)
    return EvidencePack(
        metadata=metadata,
        evidence=evidence,
        diagnostic_entries=prioritize(diagnostic_entries),
        user_corrections=corrections,
        warnings=warnings,
    )
