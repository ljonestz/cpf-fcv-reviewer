from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import (
    DetailLevel,
    DiagnosticMode,
    DocumentCoverage,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    PriorityArea,
    RecommendationScale,
    ReviewDraft,
    ReviewResult,
    RevisionSummaryItem,
    RunMetadata,
    SensitivityCategory,
    UserCorrection,
)


def locator() -> EvidenceLocator:
    return EvidenceLocator(
        document_title="CPF.docx",
        heading="Implementation arrangements",
        element="paragraph 18",
        excerpt="Delivery arrangements will adapt to local conditions.",
    )


def priority_area_values() -> dict[str, object]:
    return {
        "priority_area_id": "pa-1",
        "heading": "Make the delivery model explicit",
        "assessment": "The CPF recognizes insecurity but leaves adaptation implicit.",
        "why_it_matters": "Teams cannot see how delivery will change in insecure areas.",
        "recommended_action": "Add two sentences defining differentiated delivery arrangements.",
        "target_locator": locator(),
        "recommendation_scale": RecommendationScale.TARGETED_EDIT,
        "evidence_ids": ("ev-1",),
        "sensitivity": SensitivityCategory.CAUTIOUS,
    }


def test_priority_area_keeps_assessment_action_target_and_evidence_together():
    area = PriorityArea(**priority_area_values())

    assert area.target_locator.document_title == "CPF.docx"


@pytest.mark.parametrize(
    "field",
    ["priority_area_id", "heading", "assessment", "why_it_matters", "recommended_action"],
)
@pytest.mark.parametrize("value", ["", "   "])
def test_priority_area_rejects_blank_required_narrative_fields(field, value):
    values = priority_area_values()
    values[field] = value

    with pytest.raises(ValidationError):
        PriorityArea(**values)


@pytest.mark.parametrize("evidence_ids", [(), ("",), ("   ",), ("ev-1", " ")])
def test_priority_area_rejects_empty_or_blank_evidence_ids(evidence_ids):
    values = priority_area_values()
    values["evidence_ids"] = evidence_ids

    with pytest.raises(ValidationError):
        PriorityArea(**values)


def test_priority_area_allows_no_comment_reference():
    assert PriorityArea(**priority_area_values()).comment_reference is None


@pytest.mark.parametrize("comment_reference", ["", "   "])
def test_priority_area_rejects_blank_comment_reference(comment_reference):
    values = priority_area_values()
    values["comment_reference"] = comment_reference

    with pytest.raises(ValidationError):
        PriorityArea(**values)


@pytest.mark.parametrize("field", ["priority_area_id", "action"])
@pytest.mark.parametrize("value", ["", "   "])
def test_revision_summary_rejects_blank_required_fields(field, value):
    values = {"priority_area_id": "pa-1", "action": "Clarify the causal link."}
    values[field] = value

    with pytest.raises(ValidationError):
        RevisionSummaryItem(**values)


@pytest.mark.parametrize("field", ["primary_document", "coverage_note"])
@pytest.mark.parametrize("value", ["", "   "])
def test_document_coverage_rejects_blank_required_fields(field, value):
    values = {
        "primary_document": "CPF.docx",
        "coverage_note": "The primary draft was reviewed.",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        DocumentCoverage(**values)


@pytest.mark.parametrize("field", ["package_documents", "context_documents"])
@pytest.mark.parametrize("value", ["", "   "])
def test_document_coverage_rejects_blank_document_tuple_entries(field, value):
    values = {
        "primary_document": "CPF.docx",
        "coverage_note": "The primary draft was reviewed.",
        field: ("supporting.docx", value),
    }

    with pytest.raises(ValidationError):
        DocumentCoverage(**values)


@pytest.mark.parametrize("value", ["", "   "])
def test_review_result_rejects_blank_overall_read(make_valid_result, value):
    result, _ = make_valid_result
    payload = result.model_dump()
    payload["overall_read"] = value

    with pytest.raises(ValidationError):
        ReviewResult.model_validate(payload)


@pytest.mark.parametrize("value", ["", "   "])
def test_review_result_rejects_blank_alignment_readout(make_valid_result, value):
    result, _ = make_valid_result
    payload = result.model_dump()
    payload["alignment_readout"] = value

    with pytest.raises(ValidationError, match="Alignment readout cannot be blank"):
        ReviewResult.model_validate(payload)


def test_review_draft_requires_alignment_readout(make_valid_result):
    result, _ = make_valid_result

    with pytest.raises(ValidationError, match="alignment_readout"):
        ReviewDraft(
            overall_read=result.overall_read,
            revision_summary=result.revision_summary,
            priority_areas=result.priority_areas,
            institutional_referral_ids=(),
            limitations=(),
            coverage_note="The primary draft was reviewed.",
        )


def test_review_draft_preserves_nonblank_alignment_readout(make_valid_result):
    result, _ = make_valid_result
    alignment_readout = (
        "The draft partly reflects the diagnostic and current context, but the strategic "
        "response remains incomplete."
    )

    draft = ReviewDraft(
        overall_read=result.overall_read,
        alignment_readout=alignment_readout,
        revision_summary=result.revision_summary,
        priority_areas=result.priority_areas,
        institutional_referral_ids=(),
        limitations=(),
        coverage_note="The primary draft was reviewed.",
    )

    assert draft.alignment_readout == alignment_readout


@pytest.mark.parametrize("value", ["", "   "])
def test_review_draft_rejects_blank_alignment_readout(make_valid_result, value):
    result, _ = make_valid_result

    with pytest.raises(ValidationError, match="Alignment readout cannot be blank"):
        ReviewDraft(
            overall_read=result.overall_read,
            alignment_readout=value,
            revision_summary=result.revision_summary,
            priority_areas=result.priority_areas,
            institutional_referral_ids=(),
            limitations=(),
            coverage_note="The primary draft was reviewed.",
        )


@pytest.mark.parametrize("value", ["", "   "])
def test_review_draft_rejects_blank_overall_read(make_valid_result, value):
    result, _ = make_valid_result

    with pytest.raises(ValidationError):
        ReviewDraft(
            overall_read=value,
            alignment_readout="The draft is partly aligned with the diagnostic.",
            revision_summary=result.revision_summary,
            priority_areas=result.priority_areas,
            institutional_referral_ids=(),
            limitations=(),
            coverage_note="The primary draft was reviewed.",
        )


@pytest.mark.parametrize("value", ["", "   "])
def test_review_draft_rejects_blank_coverage_note(make_valid_result, value):
    result, _ = make_valid_result

    with pytest.raises(ValidationError):
        ReviewDraft(
            overall_read=result.overall_read,
            alignment_readout="The draft is partly aligned with the diagnostic.",
            revision_summary=result.revision_summary,
            priority_areas=result.priority_areas,
            institutional_referral_ids=(),
            limitations=(),
            coverage_note=value,
        )


def test_new_contract_defaults_and_enum_fields_serialize_compactly():
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
    evidence = EvidenceItem(
        evidence_id="ev-1",
        evidence_type="analytical_inference",
        text="The causal link is implicit.",
        confidence="medium",
        document_role=DocumentRole.PRIMARY,
    )
    correction = UserCorrection(
        correction_id="c-1",
        created_at=datetime.now(UTC),
        affected_priority_area_id="pa-1",
        text="Clarify delivery arrangements.",
    )

    assert metadata.detail_level is DetailLevel.STANDARD
    assert metadata.model_dump(mode="json")["detail_level"] == "standard"
    assert evidence.model_dump(mode="json")["document_role"] == "primary"
    assert correction.affected_priority_area_id == "pa-1"


def test_review_result_contains_no_priority_question_response_collection(make_valid_result):
    result, _ = make_valid_result

    assert isinstance(result, ReviewResult)
    assert "priority_question_responses" not in result.model_dump()
    assert result.metadata.detail_level is DetailLevel.STANDARD


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
