from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    CurrentEvidenceTier,
    DetailLevel,
    DiagnosticMode,
    DocumentCoverage,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RecommendationScale,
    RRADriverAssessment,
    ReviewDraft,
    ReviewResult,
    RevisionSummaryItem,
    RunMetadata,
    SensitivityCategory,
    UserCorrection,
)


def test_current_evidence_tier_is_shared_and_serializes_as_stable_values():
    assert CurrentEvidenceTier.FULL.value == "full"
    assert CurrentEvidenceTier.REDUCED.value == "reduced"
    assert CurrentEvidenceTier.DOCUMENT_LED.value == "document_led"


def _run_metadata_values(**overrides):
    values = {
        "run_id": "run-status",
        "created_at": datetime.now(UTC),
        "review_stage": "concept_review",
        "diagnostic_mode": DiagnosticMode.LIMITED_FRAMING,
        "app_release": "0.1.0",
        "schema_version": "1.0.0",
        "rubric_version": "1.0.0",
        "prompt_bundle_version": "1.0.0",
        "registry_versions": {"fcv_strategy": "1.0.0"},
        "model_id": "test-model",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    ("tier", "limitation"),
    (
        (CurrentEvidenceTier.FULL, " "),
        (CurrentEvidenceTier.REDUCED, None),
        (CurrentEvidenceTier.REDUCED, "   "),
        (CurrentEvidenceTier.DOCUMENT_LED, None),
        (CurrentEvidenceTier.DOCUMENT_LED, "\t"),
    ),
)
def test_run_metadata_rejects_inconsistent_current_evidence_status(tier, limitation):
    with pytest.raises(ValidationError, match="current_evidence"):
        RunMetadata(
            **_run_metadata_values(
                current_evidence_tier=tier,
                current_evidence_limitation=limitation,
            )
        )


@pytest.mark.parametrize(
    "tier",
    [CurrentEvidenceTier.REDUCED, CurrentEvidenceTier.DOCUMENT_LED],
)
def test_run_metadata_current_evidence_status_is_immutable_and_serializable(tier):
    limitation = "Independent current evidence remains incomplete."
    metadata = RunMetadata(
        **_run_metadata_values(
            current_evidence_tier=tier,
            current_evidence_limitation=limitation,
        )
    )

    assert metadata.current_evidence_tier is tier
    assert metadata.current_evidence_limitation == limitation
    assert metadata.model_dump(mode="json")["current_evidence_tier"] == tier.value
    with pytest.raises(ValidationError):
        metadata.current_evidence_tier = CurrentEvidenceTier.FULL
    invalid = metadata.model_dump()
    invalid.update(
        {
            "current_evidence_tier": CurrentEvidenceTier.FULL,
            "current_evidence_limitation": limitation,
        }
    )
    with pytest.raises(ValidationError):
        RunMetadata.model_validate(invalid)


def rra_assessment_values(**overrides) -> dict[str, object]:
    values = {
        "assessment_id": "rra-1",
        "driver": "Unequal territorial access",
        "cpf_response": "The CPF prioritizes lagging regions.",
        "delivery_mechanism": "Area-based delivery is proposed.",
        "result_or_indicator": "A service-access indicator is included.",
        "remaining_gap": "Adaptation triggers are not defined.",
        "status": AssessmentStatus.ALIGNED,
        "confidence": AssessmentConfidence.HIGH,
        "gap_locus": None,
        "evidence_ids": ("ev-1",),
    }
    values.update(overrides)
    return values


def strategy_assessment_values(**overrides) -> dict[str, object]:
    values = {
        "assessment_id": "strategy-1",
        "strategic_shift": FCVStrategicShift.ANTICIPATE_BETTER,
        "assessment": "The CPF reflects this strategic shift in the response.",
        "status": AssessmentStatus.ALIGNED,
        "confidence": AssessmentConfidence.HIGH,
        "gap_locus": None,
        "evidence_ids": ("ev-1",),
    }
    values.update(overrides)
    return values


def test_assessment_enums_expose_canonical_values():
    assert {member.value for member in AssessmentStatus} == {
        "aligned",
        "partially_aligned",
        "not_evidenced",
        "not_assessable",
    }
    assert {member.value for member in AssessmentConfidence} == {"high", "medium", "low"}
    assert {member.value for member in GapLocus} == {
        "cpf_narrative",
        "results_framework",
        "delivery_arrangements",
        "monitoring_adaptation",
        "downstream_operationalization",
    }
    assert {member.value for member in FCVStrategicShift} == {
        "anticipate_better",
        "differentiated_approach",
        "one_wbg_jobs",
        "toolkit_partnerships_staffing",
    }


def test_structured_assessments_construct_one_driver_and_all_strategy_rows():
    rra = RRADriverAssessment(**rra_assessment_values())
    strategy_rows = tuple(
        FCVStrategyAssessment(
            **strategy_assessment_values(
                assessment_id=f"strategy-{index}",
                strategic_shift=strategic_shift,
            )
        )
        for index, strategic_shift in enumerate(FCVStrategicShift, start=1)
    )

    assert rra.driver == "Unequal territorial access"
    assert {row.strategic_shift for row in strategy_rows} == set(FCVStrategicShift)


@pytest.mark.parametrize(
    ("model", "factory", "field"),
    (
        (RRADriverAssessment, rra_assessment_values, "assessment_id"),
        (RRADriverAssessment, rra_assessment_values, "driver"),
        (RRADriverAssessment, rra_assessment_values, "cpf_response"),
        (RRADriverAssessment, rra_assessment_values, "delivery_mechanism"),
        (RRADriverAssessment, rra_assessment_values, "result_or_indicator"),
        (RRADriverAssessment, rra_assessment_values, "remaining_gap"),
        (FCVStrategyAssessment, strategy_assessment_values, "assessment_id"),
        (FCVStrategyAssessment, strategy_assessment_values, "assessment"),
    ),
)
@pytest.mark.parametrize("value", ["", "   "])
def test_assessments_reject_blank_narrative_fields(model, factory, field, value):
    values = factory()
    values[field] = value

    with pytest.raises(ValidationError):
        model(**values)


@pytest.mark.parametrize(
    ("model", "factory"),
    (
        (RRADriverAssessment, rra_assessment_values),
        (FCVStrategyAssessment, strategy_assessment_values),
    ),
)
@pytest.mark.parametrize(
    "status",
    [AssessmentStatus.PARTIALLY_ALIGNED, AssessmentStatus.NOT_EVIDENCED],
)
def test_partial_or_not_evidenced_assessments_require_gap_locus(model, factory, status):
    values = factory(status=status)

    with pytest.raises(ValidationError, match="gap_locus"):
        model(**values)


@pytest.mark.parametrize(
    ("model", "factory"),
    (
        (RRADriverAssessment, rra_assessment_values),
        (FCVStrategyAssessment, strategy_assessment_values),
    ),
)
@pytest.mark.parametrize(
    "status",
    [
        AssessmentStatus.ALIGNED,
        AssessmentStatus.PARTIALLY_ALIGNED,
        AssessmentStatus.NOT_EVIDENCED,
    ],
)
def test_non_assessable_statuses_require_evidence(model, factory, status):
    values = factory(status=status, evidence_ids=())
    if status in {
        AssessmentStatus.PARTIALLY_ALIGNED,
        AssessmentStatus.NOT_EVIDENCED,
    }:
        values["gap_locus"] = GapLocus.CPF_NARRATIVE

    with pytest.raises(ValidationError, match="evidence"):
        model(**values)


@pytest.mark.parametrize(
    ("model", "factory"),
    (
        (RRADriverAssessment, rra_assessment_values),
        (FCVStrategyAssessment, strategy_assessment_values),
    ),
)
def test_not_assessable_allows_an_empty_evidence_list(model, factory):
    assessment = model(
        **factory(
            status=AssessmentStatus.NOT_ASSESSABLE,
            evidence_ids=(),
        )
    )

    assert assessment.evidence_ids == ()


def test_review_result_accepts_incomplete_assessment_collections(make_valid_result):
    result, _ = make_valid_result
    payload = result.model_dump()
    payload["rra_driver_assessments"] = ()
    payload["fcv_strategy_assessments"] = payload["fcv_strategy_assessments"][:1]

    parsed = ReviewResult.model_validate(payload)

    assert parsed.rra_driver_assessments == ()
    assert len(parsed.fcv_strategy_assessments) == 1


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
        "gap_locus": GapLocus.CPF_NARRATIVE,
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


@pytest.mark.parametrize("field", ["priority_area_id", "title"])
@pytest.mark.parametrize("value", ["", "   "])
def test_revision_summary_rejects_blank_required_fields(field, value):
    values = {"priority_area_id": "pa-1", "title": "Clarify the causal link."}
    values[field] = value

    with pytest.raises(ValidationError):
        RevisionSummaryItem(**values)




def test_revision_summary_accepts_a_100_character_title():
    title = "x" * 100

    item = RevisionSummaryItem(priority_area_id="pa-1", title=title)

    assert item.title == title


def test_revision_summary_rejects_a_101_character_title():
    with pytest.raises(ValidationError, match="at most 100 characters"):
        RevisionSummaryItem(priority_area_id="pa-1", title="x" * 101)


def test_revision_summary_rejects_legacy_action_as_extra_forbidden():
    with pytest.raises(ValidationError) as exc_info:
        RevisionSummaryItem(
            priority_area_id="pa-1",
            action="Clarify the causal link.",
        )

    assert any(
        error["type"] == "extra_forbidden" and error["loc"] == ("action",)
        for error in exc_info.value.errors()
    )
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

    with pytest.raises(ValidationError, match="Review readout cannot be blank"):
        ReviewResult.model_validate(payload)


@pytest.mark.parametrize("value", ["", "   "])
def test_review_result_rejects_blank_strategy_readout(make_valid_result, value):
    result, _ = make_valid_result
    payload = result.model_dump()
    payload["strategy_readout"] = value

    with pytest.raises(ValidationError, match="Review readout cannot be blank"):
        ReviewResult.model_validate(payload)


def test_review_draft_requires_alignment_readout(make_valid_result):
    result, _ = make_valid_result

    with pytest.raises(ValidationError, match="alignment_readout"):
        ReviewDraft(
            overall_read=result.overall_read,
            strategy_readout=(
                "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
            ),
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
        strategy_readout=(
            "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
        ),
        revision_summary=result.revision_summary,
        priority_areas=result.priority_areas,
        fcv_strategy_assessments=result.fcv_strategy_assessments,
        institutional_referral_ids=(),
        limitations=(),
        coverage_note="The primary draft was reviewed.",
    )

    assert draft.alignment_readout == alignment_readout




def test_review_draft_allows_empty_rra_and_partial_strategy_collections(make_valid_result):
    result, _ = make_valid_result

    draft = ReviewDraft(
        overall_read=result.overall_read,
        alignment_readout="The draft is partly aligned with the diagnostic.",
        strategy_readout=(
            "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
        ),
        revision_summary=result.revision_summary,
        priority_areas=result.priority_areas,
        rra_driver_assessments=(),
        fcv_strategy_assessments=result.fcv_strategy_assessments[:1],
        institutional_referral_ids=(),
        limitations=(),
        coverage_note="The primary draft was reviewed.",
    )

    assert draft.rra_driver_assessments == ()
    assert len(draft.fcv_strategy_assessments) == 1
@pytest.mark.parametrize("value", ["", "   "])
def test_review_draft_rejects_blank_alignment_readout(make_valid_result, value):
    result, _ = make_valid_result

    with pytest.raises(ValidationError, match="Review readout cannot be blank"):
        ReviewDraft(
            overall_read=result.overall_read,
            alignment_readout=value,
            strategy_readout=(
                "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
            ),
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
            strategy_readout=(
                "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
            ),
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
            strategy_readout=(
                "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
            ),
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


def test_review_draft_schema_exposes_local_validation_requirements():
    schema = ReviewDraft.model_json_schema()
    definitions = schema["$defs"]

    for field in (
        "overall_read",
        "alignment_readout",
        "strategy_readout",
        "coverage_note",
    ):
        assert "non-whitespace" in schema["properties"][field]["description"]

    for definition, fields in (
        ("RRADriverAssessment", ("driver", "cpf_response", "remaining_gap")),
        ("FCVStrategyAssessment", ("assessment_id", "assessment")),
        ("PriorityArea", ("heading", "assessment", "recommended_action")),
        ("RevisionSummaryItem", ("priority_area_id", "title")),
    ):
        properties = definitions[definition]["properties"]
        for field in fields:
            assert "non-whitespace" in properties[field]["description"]

    for definition in ("RRADriverAssessment", "FCVStrategyAssessment"):
        properties = definitions[definition]["properties"]
        assert "partially_aligned or not_evidenced" in properties["gap_locus"][
            "description"
        ]
        assert "unless status is not_assessable" in properties["evidence_ids"][
            "description"
        ]

    locator_schema = definitions["EvidenceLocator"]
    locator_properties = locator_schema["properties"]
    assert "page, heading, or element" in locator_schema["description"]
    for field in ("document_title", "excerpt"):
        assert "non-whitespace" in locator_properties[field]["description"]
    for field in ("heading", "element"):
        assert "non-whitespace" in locator_properties[field]["description"]

    priority_evidence_items = definitions["PriorityArea"]["properties"][
        "evidence_ids"
    ]["items"]
    assert "non-whitespace" in priority_evidence_items["description"]
