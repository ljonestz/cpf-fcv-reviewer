from __future__ import annotations

from collections import Counter

from .contracts import DiagnosticEntry


def validate_diagnostic_coverage(
    material_evidence_ids: tuple[str, ...],
    entries: tuple[DiagnosticEntry, ...],
) -> None:
    mapped = Counter(
        evidence_id
        for entry in entries
        for evidence_id in entry.source_evidence_ids
    )
    missing = [item for item in material_evidence_ids if mapped[item] == 0]
    duplicated = [item for item in material_evidence_ids if mapped[item] > 1]
    if missing:
        raise ValueError(f"Unmapped diagnostic evidence: {', '.join(missing)}")
    if duplicated:
        raise ValueError(
            f"Diagnostic evidence mapped more than once: {', '.join(duplicated)}"
        )


def priority_key(entry: DiagnosticEntry) -> tuple[int, int, str]:
    group_rank = {
        "principal_driver": 0,
        "resilience_opportunity": 1,
        "delivery_risk": 2,
        "contextual_condition": 3,
    }
    materiality_rank = {"high": 0, "medium": 1, "low": 2}
    return (
        group_rank[entry.group],
        materiality_rank[entry.materiality],
        entry.short_name.casefold(),
    )


def prioritize(entries: tuple[DiagnosticEntry, ...]) -> tuple[DiagnosticEntry, ...]:
    return tuple(sorted(entries, key=priority_key))
