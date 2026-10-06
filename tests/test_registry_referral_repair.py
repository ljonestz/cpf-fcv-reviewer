"""Registry-controlled referral corrections preserve original review content."""

import pytest

from cpf_fcv_reviewer.contracts import DiagnosticMode, ReviewDraft
from cpf_fcv_reviewer.review_engine import STRATEGY_REGISTRY_EVIDENCE_IDS, ReviewEngine
from cpf_fcv_reviewer.validators import validate_review


class ReferralGateway:
    def __init__(self, result, candidate_ids):
        self.calls = []
        content = result.model_dump(exclude={"metadata", "document_coverage"})
        content.update(
            institutional_referral_ids=candidate_ids,
            coverage_note=result.document_coverage.coverage_note,
            overall_read="Unrequested model rewrite.",
        )
        self.draft = ReviewDraft.model_validate(content)

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append(prompt_name)
        return self.draft


@pytest.fixture
def referral_result(make_valid_result):
    result, _ = make_valid_result
    rows = tuple(
        row.model_copy(update={
            "evidence_ids": ("ev-1", STRATEGY_REGISTRY_EVIDENCE_IDS[row.strategic_shift]),
        })
        for row in result.fcv_strategy_assessments
    )
    return result.model_copy(update={
        "fcv_strategy_assessments": rows,
        "institutional_referral_ids": ("approved-b", "unknown", "approved-a"),
    })


@pytest.mark.parametrize("mode", tuple(DiagnosticMode))
@pytest.mark.parametrize("candidate_ids", [
    ("unknown",), (), ("approved-new",), ("approved-a", "model-unknown"),
])
def test_referral_repair_uses_approved_original_ids_only(referral_result, mode, candidate_ids):
    original = referral_result.model_copy(update={
        "metadata": referral_result.metadata.model_copy(update={"diagnostic_mode": mode}),
    })
    gateway = ReferralGateway(original, candidate_ids)
    repaired = ReviewEngine(gateway).repair(
        original, [{"code": "unknown_institutional_referral"}],
        evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
        registry_entry_ids={"approved-a", "approved-b", "approved-new"},
    )
    assert repaired.institutional_referral_ids == ("approved-b", "approved-a")
    assert repaired.model_dump(exclude={"metadata", "institutional_referral_ids"}) == (
        original.model_dump(exclude={"metadata", "institutional_referral_ids"})
    )
    assert repaired.metadata == original.metadata.model_copy(update={"repair_count": 1})
    assert gateway.calls == ["repair"]


def test_empty_authoritative_registry_removes_all_referrals(referral_result):
    repaired = ReviewEngine(ReferralGateway(referral_result, ("unknown",))).repair(
        referral_result, [{"code": "unknown_institutional_referral"}],
        registry_entry_ids=set(),
        evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
    )
    assert repaired.institutional_referral_ids == ()


def test_no_authoritative_registry_retains_fail_closed_behavior(referral_result):
    repaired = ReviewEngine(ReferralGateway(referral_result, ("unknown",))).repair(
        referral_result, [{"code": "unknown_institutional_referral"}],
        registry_entry_ids=None,
        evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
    )
    issues = validate_review(
        repaired, evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
        prohibited_terms=set(), registry_entry_ids={"approved-a", "approved-b"},
    )
    assert "unknown_institutional_referral" in {issue.code for issue in issues}


def test_other_issue_does_not_authorize_referral_changes(referral_result):
    repaired = ReviewEngine(ReferralGateway(referral_result, ())).repair(
        referral_result, [{"code": "stage_length_overreach"}],
        registry_entry_ids={"approved-a", "approved-b"},
        evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
    )
    assert repaired.institutional_referral_ids == referral_result.institutional_referral_ids


def test_referral_correction_does_not_hide_policy_failure(referral_result):
    original = referral_result.model_copy(update={"overall_read": "Policy clearance confirmed."})
    repaired = ReviewEngine(ReferralGateway(original, ("unknown",))).repair(
        original, [{"code": "unknown_institutional_referral"}],
        registry_entry_ids={"approved-a", "approved-b"},
        evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
    )
    issues = validate_review(
        repaired, evidence_ids={"ev-1", *STRATEGY_REGISTRY_EVIDENCE_IDS.values()},
        prohibited_terms={"Policy clearance confirmed"},
        registry_entry_ids={"approved-a", "approved-b"},
    )
    assert "unknown_institutional_referral" not in {issue.code for issue in issues}
    assert "prohibited_policy_language" in {issue.code for issue in issues}
