from datetime import UTC, datetime

import pytest

from cpf_fcv_reviewer.contracts import (
    DiagnosticEntry,
    DiagnosticMode,
    EvidenceItem,
    RunMetadata,
)
from cpf_fcv_reviewer.evidence_builder import (
    DocumentRole,
    build_evidence_pack,
    select_diagnostic_mode,
)


def _metadata(mode: DiagnosticMode) -> RunMetadata:
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="concept",
        diagnostic_mode=mode,
        app_release="test",
        schema_version="1",
        rubric_version="1",
        prompt_bundle_version="1",
        registry_versions={},
        model_id="test-model",
    )


def _evidence(evidence_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type="analytical_inference",
        text=f"Evidence {evidence_id}",
        confidence="high",
    )


def _entry(
    entry_id: str,
    evidence_id: str,
    *,
    group: str = "principal_driver",
    short_name: str = "Exclusion",
) -> DiagnosticEntry:
    return DiagnosticEntry(
        entry_id=entry_id,
        short_name=short_name,
        group=group,
        materiality="high",
        source_evidence_ids=(evidence_id,),
        grouping_rationale="Shapes the review.",
    )


def test_current_rra_enables_alignment_mode():
    documents = (
        DocumentRole("cpf", "CPF.docx", True, False, is_current=True),
        DocumentRole("rra", "RRA.docx", True, False, is_current=True),
    )
    assert select_diagnostic_mode(documents) == DiagnosticMode.RRA_ALIGNMENT


def test_missing_or_unapproved_diagnostic_forces_limited_mode():
    only_cpf = (DocumentRole("cpf", "CPF.docx", True, False, is_current=True),)
    unapproved = (
        DocumentRole("cpf", "CPF.docx", True, False, is_current=True),
        DocumentRole("diagnostic", "Context.docx", True, False),
    )
    assert select_diagnostic_mode(only_cpf) == DiagnosticMode.LIMITED_FRAMING
    assert select_diagnostic_mode(unapproved) == DiagnosticMode.LIMITED_FRAMING


@pytest.mark.parametrize(
    "document_args",
    (
        ("rra", "Old RRA.docx", True, False, False),
        ("rra", "Unreadable RRA.docx", False, False, True),
        ("diagnostic", "Unreadable.docx", False, True, False),
    ),
)
def test_unsuitable_diagnostic_sources_force_limited_mode(document_args):
    document = DocumentRole(*document_args)
    assert select_diagnostic_mode((document,)) == DiagnosticMode.LIMITED_FRAMING


def test_readable_accepted_equivalent_enables_alignment_mode():
    document = DocumentRole("diagnostic", "Accepted.docx", True, True)

    assert select_diagnostic_mode((document,)) == DiagnosticMode.RRA_ALIGNMENT


def test_build_evidence_pack_sorts_entries_and_preserves_payload():
    evidence = (_evidence("ev-context"), _evidence("ev-driver"))
    entries = (
        _entry(
            "d-context",
            "ev-context",
            group="contextual_condition",
            short_name="Context",
        ),
        _entry("d-driver", "ev-driver", short_name="Driver"),
    )

    pack = build_evidence_pack(
        metadata=_metadata(DiagnosticMode.RRA_ALIGNMENT),
        evidence=evidence,
        diagnostic_entries=entries,
        material_diagnostic_ids=("ev-context", "ev-driver"),
        warnings=("Public scan unavailable.",),
    )

    assert pack.evidence == evidence
    assert tuple(entry.entry_id for entry in pack.diagnostic_entries) == (
        "d-driver",
        "d-context",
    )
    assert pack.warnings == ("Public scan unavailable.",)


def test_build_evidence_pack_rejects_unmapped_material_evidence():
    with pytest.raises(ValueError, match="Unmapped diagnostic evidence: ev-1"):
        build_evidence_pack(
            metadata=_metadata(DiagnosticMode.RRA_ALIGNMENT),
            evidence=(_evidence("ev-1"),),
            diagnostic_entries=(),
            material_diagnostic_ids=("ev-1",),
        )


def test_build_evidence_pack_rejects_unknown_diagnostic_references():
    with pytest.raises(
        ValueError,
        match="Unknown diagnostic evidence references: ghost",
    ):
        build_evidence_pack(
            metadata=_metadata(DiagnosticMode.RRA_ALIGNMENT),
            evidence=(_evidence("ev-1"),),
            diagnostic_entries=(_entry("d1", "ghost"),),
            material_diagnostic_ids=("ghost",),
        )


def test_build_evidence_pack_rejects_duplicate_evidence_ids():
    with pytest.raises(ValueError, match="Duplicate evidence identifiers: ev-1"):
        build_evidence_pack(
            metadata=_metadata(DiagnosticMode.LIMITED_FRAMING),
            evidence=(_evidence("ev-1"), _evidence("ev-1")),
            diagnostic_entries=(),
            material_diagnostic_ids=(),
        )


def test_duplicate_evidence_error_preserves_first_seen_identifier_order():
    with pytest.raises(
        ValueError,
        match="Duplicate evidence identifiers: ev-2, ev-1",
    ):
        build_evidence_pack(
            metadata=_metadata(DiagnosticMode.LIMITED_FRAMING),
            evidence=(
                _evidence("ev-2"),
                _evidence("ev-1"),
                _evidence("ev-2"),
                _evidence("ev-1"),
            ),
            diagnostic_entries=(),
            material_diagnostic_ids=(),
        )


def test_limited_mode_rejects_duplicate_diagnostic_entry_ids():
    with pytest.raises(ValueError, match="Duplicate diagnostic entry identifiers: d1"):
        build_evidence_pack(
            metadata=_metadata(DiagnosticMode.LIMITED_FRAMING),
            evidence=(_evidence("ev-1"), _evidence("ev-2")),
            diagnostic_entries=(
                _entry("d1", "ev-1"),
                _entry("d1", "ev-2"),
            ),
            material_diagnostic_ids=(),
        )
