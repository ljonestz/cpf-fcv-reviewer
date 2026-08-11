from __future__ import annotations

from collections import Counter
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
from .diagnostic_map import (
    prioritize,
    validate_diagnostic_coverage,
    validate_diagnostic_entry_ids,
)


@dataclass(frozen=True)
class DocumentRole:
    role: Literal["cpf", "rra", "diagnostic", "results", "comments", "other"]
    name: str
    readable: bool
    accepted_equivalent: bool
    is_current: bool = False


def select_diagnostic_mode(
    documents: tuple[DocumentRole, ...],
) -> DiagnosticMode:
    for document in documents:
        if not document.readable:
            continue
        if document.role == "rra" and document.is_current:
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
    evidence_ids = tuple(item.evidence_id for item in evidence)
    evidence_counts = Counter(evidence_ids)
    duplicate_evidence_ids = tuple(
        item for item, count in evidence_counts.items() if count > 1
    )
    if duplicate_evidence_ids:
        raise ValueError(
            "Duplicate evidence identifiers: "
            f"{', '.join(duplicate_evidence_ids)}"
        )

    validate_diagnostic_entry_ids(diagnostic_entries)

    referenced_ids = material_diagnostic_ids + tuple(
        evidence_id
        for entry in diagnostic_entries
        for evidence_id in entry.source_evidence_ids
    )
    known_evidence_ids = set(evidence_ids)
    unknown_ids = tuple(dict.fromkeys(referenced_ids))
    unknown_ids = tuple(item for item in unknown_ids if item not in known_evidence_ids)
    if unknown_ids:
        raise ValueError(f"Unknown diagnostic evidence references: {', '.join(unknown_ids)}")

    if metadata.diagnostic_mode == DiagnosticMode.RRA_ALIGNMENT:
        validate_diagnostic_coverage(material_diagnostic_ids, diagnostic_entries)
    return EvidencePack(
        metadata=metadata,
        evidence=evidence,
        diagnostic_entries=prioritize(diagnostic_entries),
        user_corrections=corrections,
        warnings=warnings,
    )
