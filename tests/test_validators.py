from datetime import UTC, datetime

import pytest

from cpf_fcv_reviewer import validators
from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidenceLocator,
    Finding,
    PriorityQuestionResponse,
    Recommendation,
    ReviewResult,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.validators import (
    validate_review,
    validate_stage_behavior,
)


def metadata():
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="finalization",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"opcs": "1.0.0-test"},
        model_id="fake",
    )


def locator():
    return EvidenceLocator(
        document_title="CPF",
        page=1,
        excerpt="Outcome framework",
    )


def test_unknown_evidence_and_alignment_claim_fail():
    result = ReviewResult(
        metadata=metadata(),
        executive_judgment="The CPF is aligned with the RRA.",
        diagnostic_title="RRA-CPF alignment",
        findings=(
            Finding(
                finding_id="f1",
                title="Unsupported",
                narrative="A named policy is triggered.",
                status="material_gap",
                evidence_ids=("missing",),
                sensitivity=SensitivityCategory.DIRECT,
            ),
        ),
        recommendations=(),
    )

    issues = validate_review(result, evidence_ids=set(), prohibited_terms={"triggered"})

    assert {issue.code for issue in issues} == {
        "limited_mode_overclaim",
        "unknown_evidence",
        "prohibited_policy_language",
    }


def test_finalization_rejects_wholesale_redesign():
    issues = validate_stage_behavior(
        "finalization",
        "Replace all CPF outcome areas and rebuild the entire theory of change.",
    )

    assert issues[0].code == "stage_overreach"


def test_repair_can_receive_exact_forbidden_phrases_without_source_content():
    assert hasattr(validators, "matched_prohibited_policy_phrases")
    matches = validators.matched_prohibited_policy_phrases(
        "The draft complies with an internal threshold.",
        {"internal threshold"},
    )

    assert matches == ("complies with", "internal threshold")


def test_registry_only_prohibited_phrase_is_rejected():
    with pytest.raises(ValueError, match="Unsupported policy"):
        validators.assert_no_unsupported_policy_claims(
            "The draft relies on an internal threshold.",
            {"internal threshold"},
        )


def test_recommendation_and_priority_question_are_traceable_and_validated():
    result = ReviewResult(
        metadata=metadata(),
        executive_judgment="The evidence is limited.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(),
        recommendations=(
            Recommendation(
                recommendation_id="rec-1",
                finding_id="missing-finding",
                priority_tier="core",
                action="Confirm eligibility for the PRA.",
                why_it_matters="The rationale is unclear.",
                target_locator=locator(),
                stage_behavior="Targeted edit.",
                sensitivity=SensitivityCategory.WITHHOLD,
            ),
        ),
        priority_question_responses=(
            PriorityQuestionResponse(
                question_id="pq-1",
                question="Has the delivery risk been confirmed?",
                direct_answer="Not in the supplied package.",
                evidence_ids=("ev-2", "ev-1", "ev-2"),
                confidence="low",
            ),
        ),
    )

    issues = validate_review(result, evidence_ids={"ev-1"}, prohibited_terms=set())

    assert {issue.code for issue in issues} == {
        "unknown_finding",
        "unknown_evidence",
        "prohibited_policy_language",
        "withheld_drafting",
    }
    assert [issue.message for issue in issues if issue.code == "unknown_evidence"] == [
        "pq-1 cites unknown evidence: ['ev-2']"
    ]


def test_unknown_evidence_messages_are_sorted_and_deterministic():
    result = ReviewResult(
        metadata=metadata(),
        executive_judgment="Evidence is limited.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(
            Finding(
                finding_id="f1",
                title="Finding",
                narrative="Evidence requires confirmation.",
                status="material_gap",
                evidence_ids=("z-id", "a-id", "z-id"),
                sensitivity=SensitivityCategory.CONFIRM,
            ),
        ),
        recommendations=(),
    )

    issues = validate_review(result, evidence_ids=set(), prohibited_terms=set())

    assert [issue.message for issue in issues] == ["f1 cites unknown evidence: ['a-id', 'z-id']"]
