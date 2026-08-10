import pytest

from cpf_fcv_reviewer.contracts import DiagnosticEntry
from cpf_fcv_reviewer.diagnostic_map import validate_diagnostic_coverage


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
