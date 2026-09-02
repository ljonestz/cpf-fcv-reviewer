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


def validate_diagnostic_references(
    authoritative_evidence_ids: tuple[str, ...],
    entries: tuple[DiagnosticEntry, ...],
) -> None:
    validate_diagnostic_entry_ids(entries)
    authoritative = set(authoritative_evidence_ids)
    for entry in entries:
        if not entry.source_evidence_ids:
            raise ValueError(
                f"Diagnostic entry {entry.entry_id} requires source evidence."
            )
        counts = Counter(entry.source_evidence_ids)
        repeated = [item for item, count in counts.items() if count > 1]
        if repeated:
            raise ValueError(
                f"Diagnostic entry {entry.entry_id} repeats source evidence: "
                + ", ".join(repeated)
            )
        unknown = [
            item
            for item in entry.source_evidence_ids
            if item not in authoritative
        ]
        if unknown:
            raise ValueError("Unknown diagnostic evidence: " + ", ".join(unknown))


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
