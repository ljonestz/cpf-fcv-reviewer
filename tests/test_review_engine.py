import json
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from cpf_fcv_reviewer import model_gateway
from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DetailLevel,
    DiagnosticEntry,
    DiagnosticMode,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    EvidencePack,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RRADriverAssessment,
    RecommendationScale,
    ReviewDraft,
    ReviewResult,
    RevisionSummaryItem,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.model_gateway import AnthropicModelGateway
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.review_profiles import (
    DETAIL_PROFILES,
    STAGE_PROFILES,
    DetailProfile,
    StageProfile,
)


class FakeGateway:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append((prompt_name, payload, output_type))
        return self.result


STRATEGY_REGISTRY_EVIDENCE_IDS = tuple(
    f"registry-PUB-FCV-STRAT-{index:03d}" for index in range(1, 5)
)


def metadata(
    *,
    mode: DiagnosticMode = DiagnosticMode.LIMITED_FRAMING,
    stage: str = "finalization",
    detail: DetailLevel = DetailLevel.STANDARD,
) -> RunMetadata:
    return RunMetadata(
        run_id="run-1",
        created_at=datetime(2026, 8, 12, tzinfo=UTC),
        review_stage=stage,
        diagnostic_mode=mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="fake",
        detail_level=detail,
    )


def locator(title: str) -> EvidenceLocator:
    return EvidenceLocator(
        document_title=title,
        heading="Results framework",
        element="paragraph 12",
        excerpt=f"Excerpt from {title}.",
    )


def evidence_item(
    evidence_id: str,
    title: str,
    role: DocumentRole,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type="document_fact",
        text=f"Evidence from {title}.",
        confidence="high",
        locator=locator(title),
        document_role=role,
    )


def evidence_pack(meta: RunMetadata) -> EvidencePack:
    evidence = [
        evidence_item("ev-primary-1", "Primary.docx", DocumentRole.PRIMARY),
        evidence_item("ev-package-a-1", "Package-A.docx", DocumentRole.PACKAGE),
        evidence_item("ev-context-a-1", "Context-A.docx", DocumentRole.CONTEXT),
        evidence_item("ev-package-b-1", "Package-B.docx", DocumentRole.PACKAGE),
        evidence_item("ev-context-b-1", "Context-B.docx", DocumentRole.CONTEXT),
        evidence_item("ev-package-a-2", "Package-A.docx", DocumentRole.PACKAGE),
        evidence_item("ev-context-a-2", "Context-A.docx", DocumentRole.CONTEXT),
        EvidenceItem(
            evidence_id="ev-package-no-locator",
            evidence_type="analytical_inference",
            text="An inference without a document locator.",
            confidence="medium",
            document_role=DocumentRole.PACKAGE,
        ),
    ]
    diagnostic_entries = ()
    if meta.diagnostic_mode is DiagnosticMode.RRA_ALIGNMENT:
        evidence.append(
            EvidenceItem(
                evidence_id="ev-rra-1",
                evidence_type="document_fact",
                text="The RRA identifies a delivery constraint.",
                confidence="high",
                locator=locator("RRA.docx"),
            )
        )
        diagnostic_entries = (
            DiagnosticEntry(
                entry_id="rra-driver-1",
                short_name="Delivery constraint",
                group="delivery_risk",
                materiality="high",
                source_evidence_ids=("ev-rra-1",),
                grouping_rationale="The RRA constraint affects implementation.",
            ),
        )
    evidence.extend(
        EvidenceItem(
            evidence_id=evidence_id,
            evidence_type="registry_language",
            text=f"Synthetic FCV Strategy registry support {index}.",
            confidence="high",
        )
        for index, evidence_id in enumerate(STRATEGY_REGISTRY_EVIDENCE_IDS, start=1)
    )
    return EvidencePack(
        metadata=meta,
        evidence=tuple(evidence),
        diagnostic_entries=diagnostic_entries,
    )


def strategy_rows() -> tuple[FCVStrategyAssessment, ...]:
    gap_loci = (
        GapLocus.CPF_NARRATIVE,
        GapLocus.RESULTS_FRAMEWORK,
        GapLocus.DELIVERY_ARRANGEMENTS,
        GapLocus.MONITORING_ADAPTATION,
    )
    return tuple(
        FCVStrategyAssessment(
            assessment_id=f"strategy-{shift.value}",
            strategic_shift=shift,
            assessment="The supplied evidence supports partial alignment with this shift.",
            status=AssessmentStatus.PARTIALLY_ALIGNED,
            confidence=AssessmentConfidence.MEDIUM,
            gap_locus=gap_locus,
            evidence_ids=(registry_evidence_id,),
        )
        for shift, gap_locus, registry_evidence_id in zip(
            FCVStrategicShift,
            gap_loci,
            STRATEGY_REGISTRY_EVIDENCE_IDS,
        )
    )


def rra_rows(meta: RunMetadata) -> tuple[RRADriverAssessment, ...]:
    if meta.diagnostic_mode is not DiagnosticMode.RRA_ALIGNMENT:
        return ()
    return (
        RRADriverAssessment(
            assessment_id="rra-driver-1",
            driver="The RRA identifies a delivery constraint.",
            cpf_response="The CPF includes a response to the identified constraint.",
            delivery_mechanism="Implementation arrangements and adaptive management.",
            result_or_indicator="Delivery indicators track whether the response is working.",
            remaining_gap="The response needs clearer ownership and adaptation triggers.",
            status=AssessmentStatus.PARTIALLY_ALIGNED,
            confidence=AssessmentConfidence.MEDIUM,
            gap_locus=GapLocus.DELIVERY_ARRANGEMENTS,
            evidence_ids=("ev-rra-1",),
        ),
    )


def draft_for(
    meta: RunMetadata,
    *,
    coverage_note: str = "Model coverage note.",
    alignment_readout: str = (
        "The draft partly reflects the diagnostic and current context, but the strategic "
        "response remains incomplete."
    ),
) -> ReviewDraft:
    return ReviewDraft(
        overall_read="The review has a credible foundation.",
        alignment_readout=alignment_readout,
        revision_summary=(
            RevisionSummaryItem(
                priority_area_id="pa-1",
                title="Clarify the delivery logic",
            ),
        ),
        priority_areas=(
            PriorityArea(
                priority_area_id="pa-1",
                heading="Strengthen the delivery logic",
                assessment="The delivery logic remains implicit.",
                why_it_matters="A clearer chain will support implementation.",
                recommended_action="Clarify the delivery logic.",
                target_locator=locator("Primary.docx"),
                recommendation_scale=(
                    RecommendationScale.FINE_TUNING
                    if meta.review_stage == "finalization"
                    else RecommendationScale.TARGETED_EDIT
                ),
                evidence_ids=("ev-primary-1",),
                sensitivity=SensitivityCategory.CAUTIOUS,
                gap_locus=GapLocus.DELIVERY_ARRANGEMENTS,
            ),
        ),
        rra_driver_assessments=rra_rows(meta),
        fcv_strategy_assessments=strategy_rows(),
        institutional_referral_ids=(),
        limitations=(),
        coverage_note=coverage_note,
    )


def result_for(
    meta: RunMetadata,
    *,
    alignment_readout: str = (
        "The draft partly reflects the diagnostic and current context, but the strategic "
        "response remains incomplete."
    ),
) -> ReviewResult:
    return ReviewResult(
        metadata=meta,
        overall_read="The review has a credible foundation.",
        alignment_readout=alignment_readout,
        revision_summary=(
            RevisionSummaryItem(
                priority_area_id="pa-1",
                title="Clarify the delivery logic",
            ),
        ),
        priority_areas=(),
        rra_driver_assessments=rra_rows(meta),
        fcv_strategy_assessments=strategy_rows(),
        limitations=(),
        document_coverage={
            "primary_document": "Primary.docx",
            "package_documents": ("Package.docx",),
            "context_documents": ("Context.docx",),
            "coverage_note": "Existing coverage note.",
        },
    )


def test_profiles_are_exact():
    assert STAGE_PROFILES == {
        "early_drafting": StageProfile(
            "Challenge strategic framing where needed, but keep any immediate edit suitable "
            "for a short concept document. Carry larger changes as preparation priorities.",
            (RecommendationScale.PREPARATION_PRIORITY, RecommendationScale.TARGETED_EDIT),
            80,
        ),
        "concept_review": StageProfile(
            "Recommend material but bounded changes to strategic choices and architecture.",
            (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
            180,
        ),
        "decision_review": StageProfile(
            "Recommend specific revisions to objectives, results, risks, and delivery choices.",
            (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
            140,
        ),
        "roc_oc": StageProfile(
            "Focus on discrete management decisions and implementability refinements.",
            (RecommendationScale.TARGETED_EDIT,),
            100,
        ),
        "finalization": StageProfile(
            "Limit advice to precise clarification, correction, consistency, and indicator edits.",
            (RecommendationScale.FINE_TUNING,),
            60,
        ),
        "response_to_comments": StageProfile(
            "Link each action to the issue being resolved and propose concise response language.",
            (RecommendationScale.COMMENT_RESPONSE,),
            100,
        ),
    }
    assert "short concept document" in STAGE_PROFILES["early_drafting"].instruction
    assert STAGE_PROFILES["early_drafting"].allowed_scales == (
        RecommendationScale.PREPARATION_PRIORITY,
        RecommendationScale.TARGETED_EDIT,
    )
    assert STAGE_PROFILES["early_drafting"].max_immediate_insertion_words == 80
    assert STAGE_PROFILES["concept_review"].allowed_scales == (
        RecommendationScale.SUBSTANTIVE_REVISION,
        RecommendationScale.TARGETED_EDIT,
    )
    assert STAGE_PROFILES["concept_review"].max_immediate_insertion_words == 180
    assert STAGE_PROFILES["decision_review"].allowed_scales == (
        RecommendationScale.SUBSTANTIVE_REVISION,
        RecommendationScale.TARGETED_EDIT,
    )
    assert STAGE_PROFILES["decision_review"].max_immediate_insertion_words == 140
    assert STAGE_PROFILES["roc_oc"].allowed_scales == (RecommendationScale.TARGETED_EDIT,)
    assert STAGE_PROFILES["roc_oc"].max_immediate_insertion_words == 100
    assert STAGE_PROFILES["finalization"].allowed_scales == (
        RecommendationScale.FINE_TUNING,
    )
    assert STAGE_PROFILES["finalization"].max_immediate_insertion_words == 60
    assert STAGE_PROFILES["response_to_comments"].allowed_scales == (
        RecommendationScale.COMMENT_RESPONSE,
    )
    assert STAGE_PROFILES["response_to_comments"].max_immediate_insertion_words == 100
    assert DETAIL_PROFILES == {
        DetailLevel.BRIEF: DetailProfile(1, (2, 3)),
        DetailLevel.STANDARD: DetailProfile(2, (3, 5)),
        DetailLevel.IN_DEPTH: DetailProfile(3, (3, 5)),
    }
    assert DETAIL_PROFILES[DetailLevel.BRIEF].target_pages == 1
    assert DETAIL_PROFILES[DetailLevel.BRIEF].priority_area_range == (2, 3)
    assert DETAIL_PROFILES[DetailLevel.STANDARD].target_pages == 2
    assert DETAIL_PROFILES[DetailLevel.STANDARD].priority_area_range == (3, 5)
    assert DETAIL_PROFILES[DetailLevel.IN_DEPTH].target_pages == 3
    assert DETAIL_PROFILES[DetailLevel.IN_DEPTH].priority_area_range == (3, 5)
    with pytest.raises(FrozenInstanceError):
        STAGE_PROFILES["finalization"].max_immediate_insertion_words = 1
    with pytest.raises(FrozenInstanceError):
        DETAIL_PROFILES[DetailLevel.BRIEF].target_pages = 9


def test_profile_registries_reject_assignment_and_deletion():
    assert isinstance(STAGE_PROFILES, Mapping)
    assert isinstance(DETAIL_PROFILES, Mapping)
    with pytest.raises(TypeError):
        STAGE_PROFILES["new_stage"] = STAGE_PROFILES["finalization"]
    with pytest.raises(TypeError):
        del STAGE_PROFILES["finalization"]
    with pytest.raises(TypeError):
        DETAIL_PROFILES[DetailLevel.BRIEF] = DETAIL_PROFILES[DetailLevel.STANDARD]
    with pytest.raises(TypeError):
        del DETAIL_PROFILES[DetailLevel.BRIEF]


@pytest.mark.parametrize("stage", sorted(STAGE_PROFILES))
@pytest.mark.parametrize("detail", tuple(DetailLevel))
def test_every_stage_and_detail_injects_serialized_profiles(stage, detail):
    meta = metadata(stage=stage, detail=detail)
    gateway = FakeGateway(draft_for(meta))

    ReviewEngine(gateway).review(
        evidence_pack(meta),
        review_focus="Focus on delivery realism.",
    )

    payload = gateway.calls[0][1]
    assert set(payload) == {
        "evidence_pack",
        "stage_profile",
        "detail_profile",
        "review_focus",
    }
    assert payload["stage_profile"] == {
        "instruction": STAGE_PROFILES[stage].instruction,
        "allowed_scales": [
            scale.value for scale in STAGE_PROFILES[stage].allowed_scales
        ],
        "max_immediate_insertion_words": STAGE_PROFILES[
            stage
        ].max_immediate_insertion_words,
    }
    assert payload["detail_profile"] == {
        "target_pages": DETAIL_PROFILES[detail].target_pages,
        "priority_area_range": list(DETAIL_PROFILES[detail].priority_area_range),
    }
    assert payload["review_focus"] == "Focus on delivery realism."
    assert payload["evidence_pack"] == evidence_pack(meta).model_dump(mode="json")
    json.dumps(payload)


def test_review_derives_deduplicated_role_coverage_and_excludes_model_note():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta, coverage_note="Model-authored note."))

    result = ReviewEngine(gateway).review(evidence_pack(meta))

    assert result.document_coverage.primary_document == "Primary.docx"
    assert result.document_coverage.package_documents == (
        "Package-A.docx",
        "Package-B.docx",
    )
    assert result.document_coverage.context_documents == (
        "Context-A.docx",
        "Context-B.docx",
    )
    assert "Primary.docx" not in result.document_coverage.package_documents
    assert "Primary.docx" not in result.document_coverage.context_documents
    assert result.document_coverage.coverage_note == "Model-authored note."
    assert "coverage_note" not in result.model_dump(exclude={"document_coverage"})
    assert gateway.calls[0][2] is ReviewDraft


def test_review_carries_model_authored_alignment_readout_into_result():
    meta = metadata()
    alignment_readout = (
        "The draft partly reflects the diagnostic and current context, but the strategic "
        "response remains incomplete."
    )
    gateway = FakeGateway(draft_for(meta, alignment_readout=alignment_readout))

    result = ReviewEngine(gateway).review(evidence_pack(meta))

    assert result.alignment_readout == alignment_readout


def test_missing_located_primary_role_is_rejected_before_gateway_call():
    meta = metadata()
    pack = EvidencePack(
        metadata=meta,
        evidence=(evidence_item("ev-package", "Package.docx", DocumentRole.PACKAGE),),
        diagnostic_entries=(),
    )
    gateway = FakeGateway(draft_for(meta))

    with pytest.raises(ValueError, match="located primary document evidence"):
        ReviewEngine(gateway).review(pack)

    assert gateway.calls == []


def test_unsupported_review_stage_is_rejected_before_gateway_call():
    meta = metadata(stage="unsupported")
    gateway = FakeGateway(draft_for(meta))

    with pytest.raises(ValueError, match="Unsupported review stage: unsupported"):
        ReviewEngine(gateway).review(evidence_pack(meta))

    assert gateway.calls == []


def test_repair_preserves_application_coverage_and_updates_only_note():
    meta = metadata()
    initial = result_for(meta)
    repaired_draft = draft_for(meta, coverage_note="Updated coverage note.")
    gateway = FakeGateway(repaired_draft)

    repaired = ReviewEngine(gateway).repair(
        initial,
        [{"code": "withheld_drafting", "message": "Repair the narrative."}],
    )

    payload = gateway.calls[0][1]
    assert "metadata" not in payload["draft"]
    assert "Primary.docx" not in json.dumps(payload["draft"])
    assert "Package.docx" not in json.dumps(payload["draft"])
    assert "Context.docx" not in json.dumps(payload["draft"])
    assert payload["draft"]["coverage_note"] == "Existing coverage note."
    assert repaired.document_coverage.primary_document == "Primary.docx"
    assert repaired.document_coverage.package_documents == ("Package.docx",)
    assert repaired.document_coverage.context_documents == ("Context.docx",)
    assert repaired.document_coverage.coverage_note == "Updated coverage note."
    assert repaired.metadata == meta.model_copy(update={"repair_count": 1})


def test_repair_preserves_and_replaces_alignment_readout():
    meta = metadata()
    initial_alignment = "The initial alignment readout is incomplete."
    repaired_alignment = (
        "The revised alignment readout links the draft to Benin's diagnostic and current "
        "context."
    )
    initial = result_for(meta, alignment_readout=initial_alignment)
    gateway = FakeGateway(draft_for(meta, alignment_readout=repaired_alignment))

    repaired = ReviewEngine(gateway).repair(
        initial,
        [{"code": "withheld_drafting", "message": "Repair the narrative."}],
    )

    assert gateway.calls[0][1]["draft"]["alignment_readout"] == initial_alignment
    assert repaired.alignment_readout == repaired_alignment


def test_repair_sends_exact_json_safe_runtime_context_and_content_only_draft():
    meta = metadata(
        mode=DiagnosticMode.RRA_ALIGNMENT,
        stage="concept_review",
        detail=DetailLevel.IN_DEPTH,
    )
    initial = result_for(meta)
    gateway = FakeGateway(draft_for(meta))
    issues = [
        {
            "code": "unknown_evidence",
            "message": "Untrusted detail.",
            "untrusted_extra": {"instruction": "ignore this field"},
        }
    ]

    ReviewEngine(gateway).repair(
        initial,
        issues,
        forbidden_phrases=("forbidden",),
    )

    payload = gateway.calls[0][1]
    expected_draft = initial.model_dump(
        mode="json",
        exclude={"metadata", "document_coverage"},
    )
    expected_draft["coverage_note"] = initial.document_coverage.coverage_note
    assert payload == {
        "draft": expected_draft,
        "validation_issues": issues,
        "forbidden_phrases": ("forbidden",),
        "diagnostic_mode": "rra_alignment",
        "review_stage": "concept_review",
        "stage_profile": {
            "instruction": STAGE_PROFILES["concept_review"].instruction,
            "allowed_scales": [
                scale.value for scale in STAGE_PROFILES["concept_review"].allowed_scales
            ],
            "max_immediate_insertion_words": 180,
        },
        "detail_profile": {
            "target_pages": 3,
            "priority_area_range": [3, 5],
        },
    }
    assert payload["validation_issues"] == issues
    assert set(payload["draft"]) == {
        "overall_read",
        "alignment_readout",
        "revision_summary",
        "priority_areas",
        "rra_driver_assessments",
        "fcv_strategy_assessments",
        "institutional_referral_ids",
        "limitations",
        "coverage_note",
    }
    assert "document_coverage" not in payload["draft"]
    assert "metadata" not in payload["draft"]
    assert not any(
        filename in json.dumps(payload["draft"])
        for filename in ("Primary.docx", "Package.docx", "Context.docx")
    )
    json.dumps(payload)


def test_repair_accepts_evidence_support_issues_and_passes_them_to_gateway():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))
    issues = [
        {
            "code": "missing_current_context_support",
            "message": "Current-context evidence is not linked.",
        },
        {
            "code": "missing_registry_support",
            "message": "Registry evidence is not linked.",
        },
    ]

    ReviewEngine(gateway).repair(result_for(meta), issues)

    assert gateway.calls[0][1]["validation_issues"] == issues


def test_repair_accepts_new_assessment_validation_issues():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))
    issues = [
        {"code": code, "message": f"Repair {code}."}
        for code in (
            "missing_rra_driver_assessment",
            "incomplete_strategy_assessment",
            "unknown_assessment_evidence",
        )
    ]

    repaired = ReviewEngine(gateway).repair(result_for(meta), issues)

    assert gateway.calls[0][1]["validation_issues"] == issues
    assert repaired.fcv_strategy_assessments == strategy_rows()
    assert repaired.rra_driver_assessments == ()
    assert repaired.metadata.repair_count == 1


def test_repair_rejects_unsupported_metadata_stage_before_gateway_call():
    meta = metadata(stage="unsupported")
    gateway = FakeGateway(draft_for(meta))

    with pytest.raises(ValueError, match="Unsupported review stage: unsupported"):
        ReviewEngine(gateway).repair(
            result_for(meta),
            [{"code": "unknown_evidence", "message": "Untrusted detail."}],
        )

    assert gateway.calls == []


@pytest.mark.parametrize(
    ("issues", "expected_message"),
    [
        ([{"message": "Missing code."}], "missing code"),
        ([{"code": 123, "message": "Non-string code."}], "string code"),
        ([{"code": "not_repairable", "message": "Unknown code."}], "unknown code"),
        (["not a dict"], "dictionary"),
    ],
)
def test_repair_rejects_invalid_issue_entries_before_gateway_call(issues, expected_message):
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))

    with pytest.raises(ValueError, match=expected_message):
        ReviewEngine(gateway).repair(result_for(meta), issues)

    assert gateway.calls == []


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def test_anthropic_gateway_sends_json_and_validates_model_response(monkeypatch):
    meta = metadata()
    expected = draft_for(meta)
    response = SimpleNamespace(parsed_output=expected)
    client = FakeAnthropicClient(response)
    monkeypatch.setattr(model_gateway.anthropic, "Anthropic", lambda api_key: client)
    gateway = AnthropicModelGateway("test-key", "test-model")

    actual = gateway.generate(
        prompt_name="review",
        payload={"accented": "Résilience"},
        output_type=ReviewDraft,
    )

    assert actual == expected
    call = client.messages.calls[0]
    assert call["model"] == "test-model"
    assert call["max_tokens"] == 12000
    assert call["system"].startswith("Version: 3.0.0")
    assert call["output_format"] is ReviewDraft
    assert json.loads(call["messages"][0]["content"]) == {"accented": "Résilience"}


def test_anthropic_gateway_rejects_missing_parsed_output(monkeypatch):
    client = FakeAnthropicClient(SimpleNamespace(parsed_output=None))
    monkeypatch.setattr(model_gateway.anthropic, "Anthropic", lambda api_key: client)
    gateway = AnthropicModelGateway("test-key", "test-model")

    with pytest.raises(ValueError, match="no parsed output"):
        gateway.generate(
            prompt_name="review",
            payload={"input": "bounded"},
            output_type=ReviewDraft,
        )
