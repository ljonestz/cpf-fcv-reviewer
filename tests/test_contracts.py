from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidenceItem,
    EvidenceLocator,
    RunMetadata,
    SensitivityCategory,
)


def test_document_evidence_requires_a_real_locator():
    with pytest.raises(ValidationError):
        EvidenceLocator(document_title="CPF", excerpt="A claim")


def test_inference_can_omit_document_coordinates():
    item = EvidenceItem(
        evidence_id="ev-1",
        evidence_type="analytical_inference",
        text="The causal link is implicit.",
        locator=None,
        confidence="medium",
    )
    assert item.locator is None


def test_run_metadata_records_diagnostic_mode_and_versions():
    metadata = RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="concept_review",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="test-model",
    )
    assert metadata.diagnostic_mode == DiagnosticMode.LIMITED_FRAMING
    assert SensitivityCategory.CONFIRM.value == "confirm"
