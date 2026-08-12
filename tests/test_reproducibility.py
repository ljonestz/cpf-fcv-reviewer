from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import DetailLevel, DiagnosticMode
from cpf_fcv_reviewer.evidence_builder import build_reproducible_evidence_pack
from cpf_fcv_reviewer.reproducibility import build_run_metadata, sha256_bytes


def test_metadata_rejects_unsupported_detail_level_at_pydantic_validation():
    with pytest.raises(ValidationError, match="detail_level"):
        build_run_metadata(
            run_id="run-invalid-detail",
            created_at=datetime(2026, 8, 10, tzinfo=UTC),
            review_stage="early_drafting",
            detail_level="unsupported",
            diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
            documents={},
            registry_bundle=b"registry",
            guidance="guidance",
            prompt_bytes={},
            model_id="test-model",
            source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
            output_language="en",
        )


def test_metadata_records_every_reproducibility_input():
    metadata = build_run_metadata(
        run_id="run-1",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        review_stage="early_draft",
        detail_level=DetailLevel.BRIEF,
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        documents={"CPF draft": b"synthetic input"},
        registry_bundle=b'{"bundle_version":"2026.08"}',
        guidance="Check the conflict narrative.",
        prompt_bytes={"review": b"review-v1"},
        model_id="test-model",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
        validation_outcomes=("contract_valid", "policy_guardrails_passed"),
        correction_ids=("c-1",),
        parent_run_id="run-0",
    )

    assert metadata.document_fingerprints == {"CPF draft": sha256_bytes(b"synthetic input")}
    assert metadata.registry_bundle_hash == sha256_bytes(b'{"bundle_version":"2026.08"}')
    assert metadata.guidance_hash == sha256_bytes(b"Check the conflict narrative.")
    assert metadata.prompt_hashes == {"review": sha256_bytes(b"review-v1")}
    assert metadata.source_scan_at == datetime(2026, 8, 10, tzinfo=UTC)
    assert metadata.output_language == "en"
    assert metadata.validation_outcomes[-1] == "policy_guardrails_passed"
    assert metadata.correction_ids == ("c-1",)
    assert metadata.parent_run_id == "run-0"
    assert metadata.detail_level is DetailLevel.BRIEF


def test_metadata_hash_mappings_are_sorted_deterministically_and_immutable():
    metadata = build_run_metadata(
        run_id="run-1",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        review_stage="early_draft",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        documents={"z annex": b"z", "a cpf": b"a"},
        registry_bundle=b"registry",
        guidance="guidance",
        prompt_bytes={"z prompt": b"z", "a prompt": b"a"},
        model_id="test-model",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
    )

    assert list(metadata.document_fingerprints) == ["a cpf", "z annex"]
    assert list(metadata.prompt_hashes) == ["a prompt", "z prompt"]
    with pytest.raises(TypeError):
        metadata.document_fingerprints["other"] = "hash"
    with pytest.raises(TypeError):
        metadata.prompt_hashes["other"] = "hash"


def test_metadata_never_retains_raw_content():
    document_content = "sensitive document content"
    guidance = "sensitive guidance content"
    correction_id = "c-1"
    metadata = build_run_metadata(
        run_id="run-1",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        review_stage="early_draft",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        documents={"CPF draft": document_content.encode()},
        registry_bundle=b"registry",
        guidance=guidance,
        prompt_bytes={"review": b"sensitive prompt content"},
        model_id="test-model",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
        correction_ids=(correction_id,),
    )

    serialized = str(metadata.model_dump())
    assert document_content not in serialized
    assert guidance not in serialized
    assert "sensitive prompt content" not in serialized
    assert correction_id in serialized


def test_evidence_pack_builder_constructs_metadata_before_model_use():
    pack = build_reproducible_evidence_pack(
        run_id="run-2",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        review_stage="concept_review",
        detail_level=DetailLevel.IN_DEPTH,
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        documents={"CPF draft": b"synthetic document"},
        registry_bundle=b"synthetic registry",
        guidance="Check delivery assumptions.",
        prompt_bytes={"review": b"review prompt"},
        model_id="test-model",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
        evidence=(),
        diagnostic_entries=(),
        material_diagnostic_ids=(),
    )

    assert pack.metadata.document_fingerprints == {"CPF draft": sha256_bytes(b"synthetic document")}
    assert pack.metadata.registry_bundle_hash == sha256_bytes(b"synthetic registry")
    assert pack.metadata.prompt_hashes == {"review": sha256_bytes(b"review prompt")}
    assert pack.metadata.detail_level is DetailLevel.IN_DEPTH
