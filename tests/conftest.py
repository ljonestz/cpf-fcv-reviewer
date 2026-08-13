from datetime import UTC, datetime

import pytest

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    DocumentCoverage,
    EvidenceItem,
    EvidenceLocator,
    PriorityArea,
    RecommendationScale,
    ReviewResult,
    RevisionSummaryItem,
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
        revision_summary=(
            RevisionSummaryItem(
                priority_area_id="pa-1",
                action="Clarify the causal link.",
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
