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


def test_document_fact_requires_a_locator():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-2",
            evidence_type="document_fact",
            text="The CPF identifies a delivery risk.",
            locator=None,
            confidence="high",
        )


@pytest.mark.parametrize("source_url", [None, "   "])
def test_current_context_requires_a_nonblank_source_url(source_url):
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-3",
            evidence_type="current_context",
            text="The current context has shifted.",
            confidence="high",
            source_url=source_url,
        )


@pytest.mark.parametrize("field", ["document_title", "excerpt", "heading", "element"])
@pytest.mark.parametrize("value", ["", "   "])
def test_document_locator_rejects_blank_text_fields(field, value):
    locator = {
        "document_title": "CPF",
        "page": 1,
        "excerpt": "A claim",
    }
    locator[field] = value

    with pytest.raises(ValidationError):
        EvidenceLocator(**locator)


def test_document_locator_preserves_meaningful_excerpt_text():
    locator = EvidenceLocator(
        document_title="CPF",
        page=1,
        excerpt="  A claim with intentional whitespace.  ",
    )

    assert locator.excerpt == "  A claim with intentional whitespace.  "


def test_run_metadata_registry_versions_is_immutable_and_serializes_as_a_mapping():
    metadata = RunMetadata(
        run_id="run-2",
        created_at=datetime.now(UTC),
        review_stage="concept_review",
        diagnostic_mode=DiagnosticMode.RRA_ALIGNMENT,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="test-model",
    )

    with pytest.raises(TypeError):
        metadata.registry_versions["new_registry"] = "2.0.0"

    assert metadata.model_dump()["registry_versions"] == {"fcv_strategy": "1.0.0"}


def test_run_metadata_forbids_extra_fields():
    with pytest.raises(ValidationError):
        RunMetadata(
            run_id="run-3",
            created_at=datetime.now(UTC),
            review_stage="concept_review",
            diagnostic_mode=DiagnosticMode.RRA_ALIGNMENT,
            app_release="0.1.0",
            schema_version="1.0.0",
            rubric_version="1.0.0",
            prompt_bundle_version="1.0.0",
            registry_versions={"fcv_strategy": "1.0.0"},
            model_id="test-model",
            unexpected_field="not allowed",
        )


def test_run_metadata_rejects_repair_count_above_one():
    with pytest.raises(ValidationError):
        RunMetadata(
            run_id="run-4",
            created_at=datetime.now(UTC),
            review_stage="concept_review",
            diagnostic_mode=DiagnosticMode.RRA_ALIGNMENT,
            app_release="0.1.0",
            schema_version="1.0.0",
            rubric_version="1.0.0",
            prompt_bundle_version="1.0.0",
            registry_versions={"fcv_strategy": "1.0.0"},
            model_id="test-model",
            repair_count=2,
        )
