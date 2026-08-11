from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import (
    DiagnosticEntry,
    DiagnosticMode,
    EvidenceItem,
    EvidenceLocator,
    Finding,
    Recommendation,
    ReviewResult,
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

    def review(self, evidence_pack) -> ReviewResult:
        self.calls += 1
        locator = evidence_pack.evidence[0].locator
        assert locator is not None
        return ReviewResult(
            metadata=evidence_pack.metadata,
            executive_judgment="The strategy has a usable FCV foundation that needs strengthening.",
            diagnostic_title="Core Review 1",
            findings=(
                Finding(
                    finding_id="finding-1",
                    title="Delivery risk needs clearer treatment",
                    narrative="The synthetic strategy identifies delivery constraints.",
                    status="needs_strengthening",
                    evidence_ids=("evidence-1",),
                    sensitivity=SensitivityCategory.CAUTIOUS,
                ),
            ),
            recommendations=(
                Recommendation(
                    recommendation_id="recommendation-1",
                    finding_id="finding-1",
                    priority_tier="core",
                    action="Clarify the delivery-risk response before finalization.",
                    why_it_matters="This links the diagnostic to an implementable response.",
                    target_locator=locator,
                    stage_behavior="Revise the identified strategic-context passage.",
                    sensitivity=SensitivityCategory.CAUTIOUS,
                ),
            ),
            limitations=("No current RRA was available; limited framing was used.",),
        )


def correction_models(payload: dict) -> tuple[UserCorrection, ...]:
    return tuple(
        UserCorrection(
            correction_id=item["correction_id"],
            created_at=item["created_at"],
            affected_finding_id=item.get("affected_finding_id"),
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
            evidence_id="evidence-1",
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
        corrections = correction_models(payload)
        context["evidence_pack"] = build_reproducible_evidence_pack(
            run_id=context["assessment_id"],
            created_at=datetime(2026, 8, 11, tzinfo=UTC),
            review_stage=payload["review_stage"],
            diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
            documents={document.name: payload["cpf"]["bytes"]},
            registry_bundle=registry_bytes,
            guidance=payload["guidance"],
            prompt_bytes={"review": Path("prompts/review.md").read_bytes()},
            model_id="synthetic-model-adapter",
            source_scan_at=datetime(2026, 8, 11, tzinfo=UTC),
            output_language="en",
            evidence=(evidence,),
            diagnostic_entries=(diagnostic,),
            material_diagnostic_ids=(evidence.evidence_id,),
            corrections=corrections,
            validation_outcomes=("contract_valid", "policy_guardrails_passed"),
            correction_ids=tuple(item.correction_id for item in corrections),
            parent_run_id=payload.get("parent_assessment_id"),
        )
        return context

    def review(context):
        context["result"] = model.review(context["evidence_pack"])
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
    bundle = load_registry_bundle(REGISTRY_PATH, allow_synthetic=True)
    return (
        {"review_orchestrator": orchestrator, "registry_bundle": bundle},
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
            "guidance": "What delivery risks need attention?",
            "priority_questions": "What delivery risks need attention?",
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
    assert result["metadata"]["diagnostic_mode"] == "limited_framing"
    assert result["metadata"]["output_language"] == "en"
    assert result["findings"][0]["evidence_ids"]
    assert result["recommendations"][0]["target_locator"]["heading"]

    export = client.get(f"/api/reviews/{created['assessment_id']}/export.docx")
    assert export.status_code == 200
    document = Document(BytesIO(export.data))
    docx_headings = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.style.name.startswith(("Title", "Heading"))
    ]
    browser_section_headings = [result["diagnostic_title"], result["findings"][0]["title"]]
    assert [heading for heading in docx_headings if heading in browser_section_headings] == (
        browser_section_headings
    )

    correction_response = client.post(
        f"/api/reviews/{created['assessment_id']}/corrections",
        json={"text": "Use the corrected synthetic delivery-risk description."},
    )
    assert correction_response.status_code == 201
    child = correction_response.get_json()
    child_state = app.extensions["session_store"].get(child["assessment_id"])
    child_run_labels = [item["label"] for item in child_state.payload["corrections"]]
    assert "User-provided correction" in child_run_labels
    run_assessment(app, child["assessment_id"])
    child_result = client.get(child["result_url"]).get_json()
    assert child_result["metadata"]["parent_run_id"] == created["assessment_id"]
    assert child_result["metadata"]["correction_ids"]

    assert client.delete(f"/api/reviews/{child['assessment_id']}").status_code == 204
    assert client.get(child["result_url"]).status_code == 410
    assert sharepoint.calls == ["Synthetic Republic", "Synthetic Republic"]
    assert public_search.calls == ["Synthetic Republic", "Synthetic Republic"]
    assert model.calls == 2
    assert stable_service_calls == []
