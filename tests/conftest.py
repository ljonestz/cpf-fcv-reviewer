from datetime import UTC, datetime

import pytest

from cpf_fcv_reviewer.contracts import (
    AssessmentConfidence,
    AssessmentStatus,
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
    RRADriverAssessment,
    RunMetadata,
    SensitivityCategory,
)


@pytest.fixture
def make_valid_result():
    metadata = RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="finalization",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"opcs": "1.0.0-test"},
        model_id="fake-model",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
        document_fingerprints={"CPF.docx": "a" * 64},
        registry_bundle_hash="b" * 64,
        guidance_hash="c" * 64,
        prompt_hashes={"review": "d" * 64},
        validation_outcomes=(
            "contract_valid",
            "policy_guardrails_passed",
        ),
    )
    locator = EvidenceLocator(
        document_title="CPF.docx",
        heading="Results framework",
        element="paragraph 12",
        excerpt="The program will support access.",
    )
    result = ReviewResult(
        metadata=metadata,
        overall_read="The CPF has a useful foundation but needs a clearer delivery narrative.",
        alignment_readout=(
            "The draft partly reflects the diagnostic and current context, but the strategic "
            "response remains incomplete."
        ),
        strategy_readout=(
            "The CPF advances prevention and jobs. Operational differentiation remains incomplete."
        ),
        revision_summary=(
            RevisionSummaryItem(
                priority_area_id="pa-1",
                title="Strengthen the territorial delivery chain",
            ),
        ),
        priority_areas=(
            PriorityArea(
                priority_area_id="pa-1",
                heading="Strengthen the causal link",
                assessment="The link remains implicit.",
                why_it_matters="The results chain is not explicit.",
                recommended_action="Clarify the causal link.",
                target_locator=locator,
                recommendation_scale=RecommendationScale.FINE_TUNING,
                evidence_ids=("ev-1",),
                sensitivity=SensitivityCategory.CAUTIOUS,
                gap_locus=GapLocus.CPF_NARRATIVE,
            ),
        ),
        rra_driver_assessments=(
            RRADriverAssessment(
                assessment_id="rra-1",
                driver="Unequal territorial access",
                cpf_response="The CPF prioritizes lagging regions.",
                delivery_mechanism="Area-based delivery is proposed.",
                result_or_indicator="A service-access indicator is included.",
                remaining_gap="Adaptation triggers are not defined.",
                status=AssessmentStatus.PARTIALLY_ALIGNED,
                confidence=AssessmentConfidence.HIGH,
                gap_locus=GapLocus.MONITORING_ADAPTATION,
                evidence_ids=("ev-1",),
            ),
        ),
        fcv_strategy_assessments=(
            FCVStrategyAssessment(
                assessment_id="strategy-anticipate-better",
                strategic_shift=FCVStrategicShift.ANTICIPATE_BETTER,
                assessment="The CPF reflects this strategic shift in the response.",
                status=AssessmentStatus.ALIGNED,
                confidence=AssessmentConfidence.HIGH,
                evidence_ids=("ev-1",),
            ),
            FCVStrategyAssessment(
                assessment_id="strategy-differentiated-approach",
                strategic_shift=FCVStrategicShift.DIFFERENTIATED_APPROACH,
                assessment="The CPF reflects this strategic shift in the response.",
                status=AssessmentStatus.ALIGNED,
                confidence=AssessmentConfidence.HIGH,
                evidence_ids=("ev-1",),
            ),
            FCVStrategyAssessment(
                assessment_id="strategy-one-wbg-jobs",
                strategic_shift=FCVStrategicShift.ONE_WBG_JOBS,
                assessment="The CPF reflects this strategic shift in the response.",
                status=AssessmentStatus.ALIGNED,
                confidence=AssessmentConfidence.HIGH,
                evidence_ids=("ev-1",),
            ),
            FCVStrategyAssessment(
                assessment_id="strategy-toolkit-partnerships-staffing",
                strategic_shift=FCVStrategicShift.TOOLKIT_PARTNERSHIPS_STAFFING,
                assessment="The CPF reflects this strategic shift in the response.",
                status=AssessmentStatus.ALIGNED,
                confidence=AssessmentConfidence.HIGH,
                evidence_ids=("ev-1",),
            ),
        ),
        institutional_referral_ids=("SYN-REF-001",),
        limitations=("No RRA was available.",),
        document_coverage=DocumentCoverage(
            primary_document="CPF.docx",
            coverage_note="The review covers the primary CPF draft.",
        ),
    )
    evidence = {
        "ev-1": EvidenceItem(
            evidence_id="ev-1",
            evidence_type="document_fact",
            text="The link is implicit.",
            confidence="high",
            locator=locator,
        )
    }
    return result, evidence


@pytest.fixture
def completed_coordinator_review():
    from io import BytesIO
    from pathlib import Path

    from cpf_fcv_reviewer.app import create_smoke_app
    from cpf_fcv_reviewer.routes import run_assessment

    app = create_smoke_app(start_background_runs=False)
    client = app.test_client()
    primary = (Path(__file__).parent / "fixtures" / "synthetic_en.txt").read_bytes()
    created = client.post("/api/reviews", data={
        "cpf": (BytesIO(primary), "Benin CPF.txt"),
        "country": "Benin", "review_stage": "roc_oc",
        "review_questions": "Are the program choices clear?",
    })
    assert created.status_code == 201
    assessment_id = created.json["assessment_id"]
    run_assessment(app, assessment_id)
    assert app.extensions["session_store"].get(assessment_id).payload["status"] == "complete"
    return app, client, assessment_id
