"""Publication dates must be grounded without confusing dates of reported events."""

from datetime import date

import pytest

from cpf_fcv_reviewer import contracts
from cpf_fcv_reviewer.validators import validate_review


def with_provenance(result, publication_date=date(2023, 6, 1)):
    provenance = contracts.DiagnosticProvenance(
        document_title="Guinea RRA.pdf",
        publication_date=publication_date,
        date_basis="cover" if publication_date else "unestablished",
        locator=(contracts.EvidenceLocator(
            document_title="Guinea RRA.pdf", page=1, excerpt="June 2023",
        ) if publication_date else None),
    )
    return result.model_copy(update={
        "metadata": result.metadata.model_copy(update={"diagnostic_provenance": provenance}),
    })


def date_issues(result):
    return [issue for issue in validate_review(
        result, evidence_ids={"ev-1"}, prohibited_terms=set(),
    ) if issue.code == "diagnostic_date_conflict"]


@pytest.mark.parametrize("text", [
    "The September 2022 RRA identifies exclusion.",
    "The RRA (September 2022) identifies exclusion.",
    "The RRA was published in September 2022.",
    "The diagnostic dated 2022-09 identifies exclusion.",
    "The 2022 Risk and Resilience Assessment identifies exclusion.",
    "The RRA's September 2022 findings inform the CPF.",
    "The RRA was issued in June 2022.",
    "The RRA is dated 15 June 2023.",
])
def test_rejects_conflicting_or_invented_precision_dates(make_valid_result, text):
    result = with_provenance(make_valid_result[0]).model_copy(update={"overall_read": text})
    assert date_issues(result)


@pytest.mark.parametrize("text", [
    "The June 2023 RRA identifies exclusion.",
    "The RRA (June 2023) identifies exclusion.",
    "The 2023 RRA identifies exclusion.",
    "The RRA was published in June 2023.",
    "The RRA describes a mission in September 2022.",
    "The RRA covers violence reported in September 2022.",
    "September 2022 reporting informs the CPF; the RRA identifies exclusion.",
])
def test_accepts_supported_dates_and_distinct_event_dates(make_valid_result, text):
    result = with_provenance(make_valid_result[0]).model_copy(update={"overall_read": text})
    assert not date_issues(result)


def test_unknown_provenance_rejects_authored_date(make_valid_result):
    result = with_provenance(make_valid_result[0], None).model_copy(update={
        "alignment_readout": "The September 2022 RRA identifies exclusion.",
    })
    assert date_issues(result)


def test_unknown_provenance_accepts_abstention(make_valid_result):
    result = with_provenance(make_valid_result[0], None).model_copy(update={
        "alignment_readout": "The diagnostic publication date could not be established.",
    })
    assert not date_issues(result)


def test_legacy_metadata_remains_readable(make_valid_result):
    assert not date_issues(make_valid_result[0])


def test_provenance_requires_locator_for_established_date():
    with pytest.raises(ValueError):
        contracts.DiagnosticProvenance(
            document_title="RRA.pdf", publication_date=date(2023, 6, 1), date_basis="cover",
        )


def test_review_receives_application_owned_provenance(make_valid_result):
    from cpf_fcv_reviewer.review_engine import ReviewEngine

    result, evidence = make_valid_result
    result = with_provenance(result)
    pack = contracts.EvidencePack(
        metadata=result.metadata,
        evidence=tuple(item.model_copy(update={"document_role": contracts.DocumentRole.PRIMARY})
                       for item in evidence.values()), diagnostic_entries=(),
    )
    calls = []

    class Gateway:
        def generate(self, *, prompt_name, payload, output_type):
            calls.append(payload)
            draft = result.model_dump(exclude={"metadata", "document_coverage"})
            draft["coverage_note"] = result.document_coverage.coverage_note
            return output_type.model_validate(draft)

    reviewed = ReviewEngine(Gateway()).review(pack)
    assert calls[0]["diagnostic_provenance"]["publication_date"] == "2023-06-01"
    assert calls[0]["diagnostic_provenance"]["date_basis"] == "cover"
    assert reviewed.metadata.diagnostic_provenance == result.metadata.diagnostic_provenance


def test_review_prompt_requires_provenance_and_preserves_month_precision():
    from cpf_fcv_reviewer.model_gateway import load_prompt

    prompt = load_prompt("review")
    assert "diagnostic_provenance" in prompt
    assert "month precision" in prompt


def test_date_guard_does_not_join_unrelated_fields(make_valid_result):
    result = with_provenance(make_valid_result[0]).model_copy(update={
        "overall_read": "The CPF partly reflects the RRA",
        "alignment_readout": "September 2022 events altered delivery conditions.",
    })
    assert not date_issues(result)
