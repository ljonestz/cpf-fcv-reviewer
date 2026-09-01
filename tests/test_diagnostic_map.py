import pytest

from cpf_fcv_reviewer.contracts import DiagnosticEntry, DiagnosticMap
from cpf_fcv_reviewer.diagnostic_map import (
    prioritize,
    validate_diagnostic_coverage,
)


def test_every_material_source_item_is_mapped_once():
    entries = (
        DiagnosticEntry(
            entry_id="d1",
            short_name="Exclusion",
            group="principal_driver",
            materiality="high",
            source_evidence_ids=("ev-1",),
            grouping_rationale="Shapes objectives.",
        ),
        DiagnosticEntry(
            entry_id="d2",
            short_name="Access constraints",
            group="delivery_risk",
            materiality="medium",
            source_evidence_ids=("ev-2",),
            grouping_rationale="Shapes implementation.",
        ),
    )
    validate_diagnostic_coverage(("ev-1", "ev-2"), entries)


def test_dropped_material_item_fails():
    entry = DiagnosticEntry(
        entry_id="d1",
        short_name="Exclusion",
        group="principal_driver",
        materiality="high",
        source_evidence_ids=("ev-1",),
        grouping_rationale="Shapes objectives.",
    )
    with pytest.raises(ValueError, match="Unmapped diagnostic evidence: ev-2"):
        validate_diagnostic_coverage(("ev-1", "ev-2"), (entry,))


def _entry(
    entry_id: str,
    evidence_id: str,
    *,
    group: str = "principal_driver",
    materiality: str = "high",
    short_name: str = "Shared name",
) -> DiagnosticEntry:
    return DiagnosticEntry(
        entry_id=entry_id,
        short_name=short_name,
        group=group,
        materiality=materiality,
        source_evidence_ids=(evidence_id,),
        grouping_rationale="Shapes the review.",
    )


def test_duplicate_mapping_fails():
    entries = (_entry("d1", "ev-1"), _entry("d2", "ev-1"))

    with pytest.raises(
        ValueError,
        match="Diagnostic evidence mapped more than once: ev-1",
    ):
        validate_diagnostic_coverage(("ev-1",), entries)


def test_duplicate_material_identifiers_fail():
    with pytest.raises(ValueError, match="Duplicate material evidence identifiers: ev-1"):
        validate_diagnostic_coverage(
            ("ev-1", "ev-1"),
            (_entry("d1", "ev-1"),),
        )


def test_duplicate_diagnostic_entry_identifiers_fail():
    entries = (_entry("d1", "ev-1"), _entry("d1", "ev-2"))

    with pytest.raises(ValueError, match="Duplicate diagnostic entry identifiers: d1"):
        validate_diagnostic_coverage(("ev-1", "ev-2"), entries)


def test_prioritize_uses_design_group_order_then_materiality():
    entries = (
        _entry("resilience", "ev-4", group="resilience_opportunity"),
        _entry("context", "ev-3", group="contextual_condition"),
        _entry("delivery", "ev-2", group="delivery_risk"),
        _entry(
            "principal-low",
            "ev-5",
            materiality="low",
            short_name="Later principal",
        ),
        _entry(
            "principal-high",
            "ev-1",
            materiality="high",
            short_name="Early principal",
        ),
    )

    assert tuple(entry.entry_id for entry in prioritize(entries)) == (
        "principal-high",
        "principal-low",
        "delivery",
        "context",
        "resilience",
    )


def test_prioritize_uses_entry_id_as_a_stable_final_tiebreaker():
    entries = (
        _entry("d-z", "ev-2", short_name="Shared name"),
        _entry("d-a", "ev-1", short_name="shared NAME"),
    )

    assert tuple(entry.entry_id for entry in prioritize(entries)) == (
        "d-a",
        "d-z",
    )


def test_diagnostic_map_requires_between_one_and_twenty_entries():
    entry = _entry("d1", "ev-1")

    assert DiagnosticMap(entries=(entry,)).entries == (entry,)
    with pytest.raises(ValueError):
        DiagnosticMap(entries=())
    with pytest.raises(ValueError):
        DiagnosticMap(
            entries=tuple(
                _entry(f"d{index}", f"ev-{index}") for index in range(21)
            )
        )


def test_unknown_diagnostic_assignment_fails_closed():
    with pytest.raises(ValueError, match="Unknown diagnostic evidence: ev-unknown"):
        validate_diagnostic_coverage(
            ("ev-1",),
            (_entry("d1", "ev-1"), _entry("d2", "ev-unknown")),
        )
