"""Regression coverage for limited-mode caveats and bounded narrative repair."""

import pytest

from cpf_fcv_reviewer.contracts import AssessmentStatus, DiagnosticMode, ReviewDraft
from cpf_fcv_reviewer.review_engine import ReviewEngine
from cpf_fcv_reviewer.validators import validate_review

ABSTENTIONS = (
    "This review has not assessed RRA alignment.",
    "This review has not evaluated alignment with the RRA.",
    "No RRA alignment assessment is possible without the diagnostic.",
    "RRA alignment was not assessed.",
    "RRA alignment was not assessed because it is clear that no RRA was supplied.",
    "RRA alignment was not assessed because it is good practice to avoid inference.",
    "RRA alignment cannot be assessed without a supplied RRA.",
    "This review does not assess alignment with the RRA.",
    "RRA alignment has not been assessed.",
    "Alignment with the RRA is not assessable because no RRA was supplied.",
    "No assessment of RRA alignment is possible without the diagnostic.",
    "This review cannot assess alignment with the RRA.",
    "RRA alignment is outside the scope of this review.",
)


def overclaim_issues(result):
    return tuple(
        issue
        for issue in validate_review(result, evidence_ids={"ev-1"}, prohibited_terms=set())
        if issue.code == "limited_mode_overclaim"
    )


@pytest.mark.parametrize("abstention", ABSTENTIONS)
@pytest.mark.parametrize("field", ("overall_read", "limitations"))
def test_limited_mode_accepts_clear_abstentions(make_valid_result, abstention, field):
    result, _ = make_valid_result
    value = (abstention,) if field == "limitations" else abstention
    assert not overclaim_issues(result.model_copy(update={field: value}))


@pytest.mark.parametrize(
    "text",
    (
        "The CPF shows strong RRA alignment.",
        "The CPF shows partial alignment with the RRA.",
        "RRA alignment was not assessed. The CPF shows strong RRA alignment.",
        "The CPF shows strong RRA alignment. RRA alignment has not been assessed.",
        (
            "RRA alignment is outside the scope of this review, "
            "but alignment with the RRA is strong."
        ),
        "We cannot assess alignment with the RRA; the CPF nevertheless shows RRA alignment.",
        "RRA alignment was not assessed, although it is strong.",
        "RRA alignment was not assessed. It is strong.",
        "RRA alignment was not assessed! This alignment appears partial.",
        ("RRA alignment has not been assessed; nevertheless, it is strong."),
        "RRA alignment is outside the scope of this review, but it appears partial.",
    ),
)
def test_abstention_does_not_hide_a_separate_alignment_claim(make_valid_result, text):
    result, _ = make_valid_result
    assert overclaim_issues(result.model_copy(update={"overall_read": text}))


class RepairGateway:
    """Supply controlled content instead of calling a model provider."""

    def __init__(self, result):
        content = result.model_dump(exclude={"metadata", "document_coverage"})
        content["coverage_note"] = result.document_coverage.coverage_note
        self.draft = ReviewDraft.model_validate(content)
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append(prompt_name)
        return self.draft


@pytest.mark.parametrize(
    "field",
    (
        "strategy_assessment",
        "driver",
        "cpf_response",
        "delivery_mechanism",
        "result_or_indicator",
        "remaining_gap",
    ),
)
def test_limited_mode_repair_keeps_corrected_row_text(make_valid_result, field):
    base, _ = make_valid_result
    if field == "strategy_assessment":
        row = base.fcv_strategy_assessments[0].model_copy(
            update={
                "assessment": "The CPF shows strong RRA alignment.",
                "status": AssessmentStatus.NOT_ASSESSABLE,
                "gap_locus": None,
                "evidence_ids": (),
            }
        )
        original = base.model_copy(
            update={
                "rra_driver_assessments": (),
                "fcv_strategy_assessments": (row, *base.fcv_strategy_assessments[1:]),
            }
        )
        corrected = original.model_copy(
            update={
                "fcv_strategy_assessments": (
                    row.model_copy(update={"assessment": "RRA alignment was not assessed."}),
                    *original.fcv_strategy_assessments[1:],
                ),
            }
        )
    else:
        row = base.rra_driver_assessments[0].model_copy(
            update={
                field: "The CPF shows strong RRA alignment.",
            }
        )
        original = base.model_copy(update={"rra_driver_assessments": (row,)})
        corrected = original.model_copy(
            update={
                "rra_driver_assessments": (
                    row.model_copy(update={field: "RRA alignment was not assessed."}),
                )
            }
        )
    gateway = RepairGateway(corrected)
    repaired = ReviewEngine(gateway).repair(
        original, [{"code": "limited_mode_overclaim"}], evidence_ids={"ev-1"}
    )

    assert overclaim_issues(original)
    assert not overclaim_issues(corrected)
    assert not overclaim_issues(repaired)
    assert gateway.calls == ["repair"]
    assert repaired.metadata.repair_count == 1
    # Only the required wording correction may change in the preserved row.
    collection = (
        "fcv_strategy_assessments" if field == "strategy_assessment" else "rra_driver_assessments"
    )
    narrative_field = "assessment" if field == "strategy_assessment" else field
    original_row = getattr(original, collection)[0]
    repaired_row = getattr(repaired, collection)[0]
    assert repaired_row.model_dump(exclude={narrative_field}) == original_row.model_dump(
        exclude={narrative_field}
    )


@pytest.mark.parametrize(
    "candidate_kind", ("still_overclaims", "changed_identity", "duplicate_identity")
)
def test_limited_mode_repair_does_not_accept_unsafe_row_replacement(
    make_valid_result, candidate_kind
):
    base, _ = make_valid_result
    row = base.rra_driver_assessments[0].model_copy(
        update={
            "remaining_gap": "The CPF shows strong RRA alignment.",
        }
    )
    original = base.model_copy(update={"rra_driver_assessments": (row,)})
    candidate = row.model_copy(update={"remaining_gap": "RRA alignment was not assessed."})
    if candidate_kind == "still_overclaims":
        candidate = row
    elif candidate_kind == "changed_identity":
        candidate = candidate.model_copy(update={"assessment_id": "different-row"})
    candidates = (candidate, candidate) if candidate_kind == "duplicate_identity" else (candidate,)
    gateway = RepairGateway(original.model_copy(update={"rra_driver_assessments": candidates}))
    repaired = ReviewEngine(gateway).repair(
        original, [{"code": "limited_mode_overclaim"}], evidence_ids={"ev-1"}
    )
    assert overclaim_issues(repaired)
    assert gateway.calls == ["repair"]


def test_limited_mode_text_repair_is_not_applied_in_alignment_mode(make_valid_result):
    original, _ = make_valid_result
    original = original.model_copy(
        update={
            "metadata": original.metadata.model_copy(
                update={"diagnostic_mode": DiagnosticMode.RRA_ALIGNMENT}
            )
        }
    )
    candidate = original.model_copy(
        update={
            "rra_driver_assessments": (
                original.rra_driver_assessments[0].model_copy(
                    update={"driver": "Unrelated replacement."}
                ),
            )
        }
    )
    repaired = ReviewEngine(RepairGateway(candidate)).repair(
        original, [{"code": "limited_mode_overclaim"}], evidence_ids={"ev-1"}
    )
    assert repaired.rra_driver_assessments == original.rra_driver_assessments


def test_limited_mode_wording_repair_does_not_add_rra_rows(make_valid_result):
    original, _ = make_valid_result
    row = original.rra_driver_assessments[0].model_copy(
        update={"remaining_gap": "The CPF shows strong RRA alignment."}
    )
    original = original.model_copy(update={"rra_driver_assessments": (row,)})
    corrected = row.model_copy(update={"remaining_gap": "RRA alignment was not assessed."})
    extra = corrected.model_copy(update={"assessment_id": "injected-row"})
    candidate = original.model_copy(update={"rra_driver_assessments": (corrected, extra)})
    repaired = ReviewEngine(RepairGateway(candidate)).repair(
        original, [{"code": "limited_mode_overclaim"}], evidence_ids={"ev-1"}
    )
    assert not overclaim_issues(repaired)
    assert repaired.rra_driver_assessments == (corrected,)
