from __future__ import annotations

from collections import Counter

from .contracts import DiagnosticEntry


def validate_diagnostic_entry_ids(entries: tuple[DiagnosticEntry, ...]) -> None:
    entry_counts = Counter(entry.entry_id for entry in entries)
    duplicate_entry_ids = [item for item, count in entry_counts.items() if count > 1]
    if duplicate_entry_ids:
        raise ValueError(
            "Duplicate diagnostic entry identifiers: "
            f"{', '.join(duplicate_entry_ids)}"
        )


def validate_diagnostic_coverage(
    material_evidence_ids: tuple[str, ...],
    entries: tuple[DiagnosticEntry, ...],
) -> None:
    material_counts = Counter(material_evidence_ids)
    duplicate_material_ids = [
        item for item, count in material_counts.items() if count > 1
    ]
    if duplicate_material_ids:
        raise ValueError(
            "Duplicate material evidence identifiers: "
            f"{', '.join(duplicate_material_ids)}"
        )

    validate_diagnostic_entry_ids(entries)

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


def priority_key(entry: DiagnosticEntry) -> tuple[int, int, str, str]:
    group_rank = {
        "principal_driver": 0,
        "delivery_risk": 1,
        "contextual_condition": 2,
        "resilience_opportunity": 3,
    }
    materiality_rank = {"high": 0, "medium": 1, "low": 2}
    return (
        group_rank[entry.group],
        materiality_rank[entry.materiality],
        entry.short_name.casefold(),
        entry.entry_id,
    )


def prioritize(entries: tuple[DiagnosticEntry, ...]) -> tuple[DiagnosticEntry, ...]:
    return tuple(sorted(entries, key=priority_key))
