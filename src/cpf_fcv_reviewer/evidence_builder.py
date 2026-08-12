from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .contracts import (
    DetailLevel,
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
from .reproducibility import build_run_metadata


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
    duplicate_evidence_ids = tuple(item for item, count in evidence_counts.items() if count > 1)
    if duplicate_evidence_ids:
        raise ValueError(f"Duplicate evidence identifiers: {', '.join(duplicate_evidence_ids)}")

    validate_diagnostic_entry_ids(diagnostic_entries)

    referenced_ids = material_diagnostic_ids + tuple(
        evidence_id for entry in diagnostic_entries for evidence_id in entry.source_evidence_ids
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


def build_reproducible_evidence_pack(
    *,
    run_id: str,
    created_at: datetime,
    review_stage: str,
    detail_level: DetailLevel | str = DetailLevel.STANDARD,
    diagnostic_mode: DiagnosticMode | str,
    documents: Mapping[str, bytes],
    registry_bundle: bytes,
    guidance: str,
    prompt_bytes: Mapping[str, bytes],
    model_id: str,
    source_scan_at: datetime,
    output_language: str,
    evidence: tuple[EvidenceItem, ...],
    diagnostic_entries: tuple[DiagnosticEntry, ...],
    material_diagnostic_ids: tuple[str, ...],
    corrections: tuple[UserCorrection, ...] = (),
    warnings: tuple[str, ...] = (),
    validation_outcomes: tuple[str, ...] = (),
    correction_ids: tuple[str, ...] = (),
    parent_run_id: str | None = None,
    repair_count: int = 0,
) -> EvidencePack:
    """Build immutable run metadata before assembling model-visible evidence."""
    metadata = build_run_metadata(
        run_id=run_id,
        created_at=created_at,
        review_stage=review_stage,
        detail_level=detail_level,
        diagnostic_mode=diagnostic_mode,
        documents=documents,
        registry_bundle=registry_bundle,
        guidance=guidance,
        prompt_bytes=prompt_bytes,
        model_id=model_id,
        source_scan_at=source_scan_at,
        output_language=output_language,
        validation_outcomes=validation_outcomes,
        correction_ids=correction_ids,
        parent_run_id=parent_run_id,
        repair_count=repair_count,
    )
    return build_evidence_pack(
        metadata=metadata,
        evidence=evidence,
        diagnostic_entries=diagnostic_entries,
        material_diagnostic_ids=material_diagnostic_ids,
        corrections=corrections,
        warnings=warnings,
    )
