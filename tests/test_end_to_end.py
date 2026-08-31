from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DiagnosticEntry,
    DiagnosticMode,
    DocumentCoverage,
    EvidenceItem,
    EvidenceLocator,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RecommendationScale,
    ReviewResult,
    RevisionSummaryItem,
    SensitivityCategory,
    UserCorrection,
)
from cpf_fcv_reviewer.evidence_builder import build_reproducible_evidence_pack
from cpf_fcv_reviewer.extraction import extract_document, require_readable_primary
from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator
from cpf_fcv_reviewer.registry import load_registry_bundle
from cpf_fcv_reviewer.routes import run_assessment

FIXTURES = Path("tests/fixtures")
REGISTRY_PATH = FIXTURES / "registry_bundle.synthetic.json"
SYNTHETIC_INPUTS = (
    "synthetic_en.txt",
    "synthetic_fr.txt",
    "synthetic_mixed.txt",
)


STRATEGY_REGISTRY_EVIDENCE_IDS = tuple(
    f"registry-PUB-FCV-STRAT-{index:03d}" for index in range(1, 5)
)


def strategy_assessments() -> tuple[FCVStrategyAssessment, ...]:
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
            assessment="The synthetic CPF partly reflects this FCV Strategy shift.",
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


class FakeSharePointAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def candidates(self, country: str) -> tuple:
        self.calls.append(country)
        return ()


class FakePublicSearchAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search(self, country: str) -> tuple:
        self.calls.append(country)
        return ()


class FakeModelAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.evidence_packs = []
        self.review_focuses = []

    def review(self, evidence_pack, *, review_focus="") -> ReviewResult:
        self.calls += 1
        self.evidence_packs.append(evidence_pack)
        self.review_focuses.append(review_focus)
        locator = evidence_pack.evidence[0].locator
        assert locator is not None
        correction_text = (
            evidence_pack.user_corrections[0].text
            if evidence_pack.user_corrections
            else None
        )
        assessment = "The synthetic strategy identifies delivery constraints."
        recommended_action = "Clarify the delivery-risk response before finalization."
        if correction_text:
            assessment = f"The synthetic strategy incorporates this correction: {correction_text}"
            recommended_action = "Retain the corrected delivery-risk description in the CPF."
        return ReviewResult(
            metadata=evidence_pack.metadata,
            overall_read="The CPF has a credible foundation.",
            alignment_readout="The CPF addresses some FCV concerns but needs clearer alignment.",
            strategy_readout=(
                "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
            ),
            revision_summary=(
                RevisionSummaryItem(
                    priority_area_id="pa-1",
                    title="Clarify the delivery-risk response",
                ),
            ),
            priority_areas=(
                PriorityArea(
                    priority_area_id="pa-1",
                    heading="Delivery risk needs clearer treatment",
                    assessment=assessment,
                    why_it_matters="This links the diagnostic to an implementable response.",
                    recommended_action=recommended_action,
                    target_locator=locator,
                    recommendation_scale=RecommendationScale.TARGETED_EDIT,
                    evidence_ids=("primary-001",),
                    sensitivity=SensitivityCategory.CAUTIOUS,
                    gap_locus=GapLocus.DELIVERY_ARRANGEMENTS,
                ),
            ),
            fcv_strategy_assessments=strategy_assessments(),
            document_coverage=DocumentCoverage(
                primary_document=locator.document_title,
                coverage_note="The review covers the uploaded CPF.",
            ),
            limitations=("No current RRA was available; limited framing was used.",),
        )


def correction_models(payload: dict) -> tuple[UserCorrection, ...]:
    return tuple(
        UserCorrection(
            correction_id=item["correction_id"],
            created_at=item["created_at"],
            affected_priority_area_id=item.get("affected_priority_area_id"),
            text=item["text"],
            rationale=item.get("rationale"),
            independently_supported=item["independently_supported"],
        )
        for item in payload.get("corrections", ())
    )


def synthetic_services():
    sharepoint = FakeSharePointAdapter()
    public_search = FakePublicSearchAdapter()
    model = FakeModelAdapter()
    stable_service_calls: list[str] = []
    registry_bytes = REGISTRY_PATH.read_bytes()
    registry_bundle = load_registry_bundle(REGISTRY_PATH, allow_synthetic=True)

    def extract(context):
        primary = context["payload"]["cpf"]
        document = extract_document(primary["bytes"], primary["name"])
        require_readable_primary(document)
        context["document"] = document
        return context

    def resolve_sources(context):
        context["rra_candidates"] = sharepoint.candidates(context["payload"]["country"])
        return context

    def research(context):
        context["public_sources"] = public_search.search(context["payload"]["country"])
        return context

    def build_evidence(context):
        payload = context["payload"]
        document = context["document"]
        segment = document.segments[0]
        locator = EvidenceLocator(
            document_title=document.name,
            heading="Strategic context",
            element=segment.element,
            excerpt=segment.text[:180],
            is_paraphrase=False,
        )
        evidence = EvidenceItem(
            evidence_id="primary-001",
            evidence_type="document_fact",
            text="The synthetic strategy describes FCV-related delivery constraints.",
            locator=locator,
            confidence="high",
        )
        diagnostic = DiagnosticEntry(
            entry_id="diagnostic-1",
            short_name="Delivery constraints",
            group="delivery_risk",
            materiality="high",
            source_evidence_ids=(evidence.evidence_id,),
            grouping_rationale="The constraint affects implementation.",
        )
        registry_evidence = tuple(
            EvidenceItem(
                evidence_id=f"registry-{entry.entry_id.removeprefix('SYN-')}",
                evidence_type="registry_language",
                text=entry.approved_text,
                confidence="high",
            )
            for entry in registry_bundle.entries
            if entry.entry_id.startswith("SYN-PUB-FCV-STRAT-")
        )
        corrections = correction_models(payload)
        context["evidence_pack"] = build_reproducible_evidence_pack(
            run_id=context["assessment_id"],
            created_at=datetime(2026, 8, 11, tzinfo=UTC),
            review_stage=payload["review_stage"],
            diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
            documents={document.name: payload["cpf"]["bytes"]},
            registry_bundle=registry_bytes,
            guidance=payload["review_focus"],
            prompt_bytes={"review": Path("prompts/review.md").read_bytes()},
            model_id="synthetic-model-adapter",
            source_scan_at=datetime(2026, 8, 11, tzinfo=UTC),
            output_language="en",
            evidence=(evidence, *registry_evidence),
            diagnostic_entries=(diagnostic,),
            material_diagnostic_ids=(evidence.evidence_id,),
            corrections=corrections,
            validation_outcomes=("contract_valid", "policy_guardrails_passed"),
            correction_ids=tuple(item.correction_id for item in corrections),
            parent_run_id=payload.get("parent_assessment_id"),
        )
        return context

    def review(context):
        context["result"] = model.review(
            context["evidence_pack"],
            review_focus=context["payload"].get("review_focus", ""),
        )
        return context

    def validate(context):
        context["validation_issues"] = []
        return context

    def passthrough(context):
        return context

    orchestrator = ReviewOrchestrator(
        steps=(
            ("extract", extract),
            ("resolve_sources", resolve_sources),
            ("research", research),
            ("build_evidence", build_evidence),
            ("map", passthrough),
            ("review", review),
            ("validate", validate),
            ("render", passthrough),
        ),
        repair=lambda context, issues: context,
    )
    return (
        {"review_orchestrator": orchestrator, "registry_bundle": registry_bundle},
        sharepoint,
        public_search,
        model,
        stable_service_calls,
    )


@pytest.mark.parametrize("fixture_name", SYNTHETIC_INPUTS)
def test_complete_synthetic_local_workflow(fixture_name):
    services, sharepoint, public_search, model, stable_service_calls = synthetic_services()
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services=services,
    )
    client = app.test_client()
    content = (FIXTURES / fixture_name).read_bytes()

    created_response = client.post(
        "/api/reviews",
        data={
            "country": "Synthetic Republic",
            "review_stage": "decision_review",
            "review_focus": "What delivery risks need attention?",
            "cpf": (BytesIO(content), fixture_name),
        },
        content_type="multipart/form-data",
    )
    assert created_response.status_code == 201
    created = created_response.get_json()
    run_assessment(app, created["assessment_id"])

    events = client.get(created["event_url"]).get_data(as_text=True)
    assert events.count("event: run_complete") == 1
    assert "event: run_failed" not in events
    result_response = client.get(created["result_url"])
    assert result_response.status_code == 200
    result = result_response.get_json()
    assert result["overall_read"] == "The CPF has a credible foundation."
    assert result["revision_summary"][0]["priority_area_id"] == "pa-1"
    assert result["priority_areas"][0]["evidence_ids"] == ["primary-001"]
    assert result["metadata"]["detail_level"] == "standard"
    assert "priority_question_responses" not in result
    assert result["metadata"]["output_language"] == "en"
    parent_assessment = result["priority_areas"][0]["assessment"]
    parent_recommended_action = result["priority_areas"][0]["recommended_action"]

    export = client.get(f"/api/reviews/{created['assessment_id']}/export.docx")
    assert export.status_code == 200
    document = Document(BytesIO(export.data))
    docx_headings = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.style.name.startswith(("Title", "Heading"))
    ]
    authoritative_docx_headings = [
        "Overall assessment",
        "How well does the CPF package align with the RRA and current FCV dynamics?",
        "How does the CPF package contribute to the FCV Strategy's core priorities?",
        "Priority areas for strengthening",
        "Limitations and document coverage",
    ]
    assert [heading for heading in docx_headings if heading in authoritative_docx_headings] == (
        authoritative_docx_headings
    )

    correction_response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json={
            "text": "Use the corrected synthetic delivery-risk description.",
            "affected_priority_area_id": "pa-1",
        },
    )
    assert correction_response.status_code == 201
    child = correction_response.get_json()
    child_state = app.extensions["session_store"].get(child["assessment_id"])
    child_run_labels = [item["label"] for item in child_state.payload["corrections"]]
    assert "User-provided correction" in child_run_labels
    assert child_state.payload["corrections"][-1]["affected_priority_area_id"] == "pa-1"
    run_assessment(app, child["assessment_id"])
    child_result = client.get(child["result_url"]).get_json()
    assert child_result["metadata"]["parent_run_id"] == created["assessment_id"]
    assert child_result["metadata"]["correction_ids"]
    assert model.review_focuses == [
        "What delivery risks need attention?",
        "What delivery risks need attention?",
    ]
    assert (
        model.evidence_packs[1].user_corrections[0].affected_priority_area_id
        == "pa-1"
    )
    assert child_result["priority_areas"][0]["assessment"] != parent_assessment
    assert child_result["priority_areas"][0]["recommended_action"] != parent_recommended_action
    assert "Use the corrected synthetic delivery-risk description." in child_result[
        "priority_areas"
    ][0]["assessment"]

    assert client.delete(f"/api/reviews/{child['assessment_id']}").status_code == 204
    assert client.get(child["result_url"]).status_code == 410
    assert sharepoint.calls == ["Synthetic Republic", "Synthetic Republic"]
    assert public_search.calls == ["Synthetic Republic", "Synthetic Republic"]
    assert model.calls == 2
    assert stable_service_calls == []
