from datetime import date

from cpf_fcv_reviewer.diagnostic_sources import (
    identify_uploaded_diagnostic,
)
from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment


def document(name: str, *segments: str) -> ExtractedDocument:
    return ExtractedDocument(
        name,
        tuple(
            ExtractedSegment(text, None, None, f"paragraph {index}")
            for index, text in enumerate(segments)
        ),
        (),
    )


def test_identifies_dated_benin_rra():
    result = identify_uploaded_diagnostic(
        (document("Benin Risk and Resilience Assessment.docx", "Publication: March 2024"),),
        country="Benin",
    )

    assert result is not None
    assert result.name == "Benin Risk and Resilience Assessment.docx"
    assert result.kind == "rra"
    assert result.publication_date == date(2024, 3, 1)


def test_rejects_generic_growth_and_jobs_diagnostic():
    assert identify_uploaded_diagnostic(
        (
            document(
                "Benin Growth and Jobs Diagnostic.pdf",
                "Benin growth and jobs diagnostic 2024",
            ),
        ),
        country="Benin",
    ) is None


def test_identifies_explicit_accepted_equivalent():
    result = identify_uploaded_diagnostic(
        (
            document(
                "Benin FCV Risk Assessment.pdf",
                "Accepted equivalent diagnostic, January 2023",
            ),
        ),
        country="Benin",
    )

    assert result is not None
    assert result.kind == "accepted_equivalent"
    assert result.publication_date == date(2023, 1, 1)


def test_retains_undated_rra_with_no_publication_date():
    result = identify_uploaded_diagnostic(
        (document("Benin Risk & Resilience Assessment.pdf", "Country context for Benin."),),
        country="Benin",
    )

    assert result is not None
    assert result.publication_date is None


def test_rejects_diagnostic_when_country_does_not_match():
    assert identify_uploaded_diagnostic(
        (document("Togo Risk and Resilience Assessment.pdf", "Togo, June 2022"),),
        country="Benin",
    ) is None


def test_retains_diagnostic_but_omits_ambiguous_publication_date():
    result = identify_uploaded_diagnostic(
        (document("Benin Risk and Resilience Assessment.pdf", "March 2022; revised July 2023"),),
        country="Benin",
    )

    assert result is not None
    assert result.publication_date is None


def test_returns_none_for_multiple_matching_diagnostics():
    documents = (
        document("Benin Risk and Resilience Assessment 2022.pdf", "Benin"),
        document("Benin Accepted Equivalent Diagnostic.pdf", "Benin"),
    )

    assert identify_uploaded_diagnostic(documents, country="Benin") is None
