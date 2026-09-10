from datetime import date
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from cpf_fcv_reviewer.diagnostic_sources import (
    identify_uploaded_diagnostic,
)
from cpf_fcv_reviewer.extraction import (
    ExtractedDocument,
    ExtractedSegment,
    extract_pdf_bytes,
)


def document(name: str, *segments: str) -> ExtractedDocument:
    return ExtractedDocument(
        name,
        tuple(
            ExtractedSegment(text, None, None, f"paragraph {index}")
            for index, text in enumerate(segments)
        ),
        (),
    )


def make_pdf(texts: list[str]) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for text in texts:
        page = writer.add_blank_page(width=300, height=300)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font}
                )
            }
        )
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_identifies_dated_benin_rra():
    result = identify_uploaded_diagnostic(
        (document("Benin Risk and Resilience Assessment.docx", "Publication: March 2024"),),
        country="Benin",
    )

    assert result is not None
    assert result.name == "Benin Risk and Resilience Assessment.docx"
    assert result.kind == "rra"
    assert result.publication_date == date(2024, 3, 1)


def test_identifies_rra_metadata_on_fourth_sampled_page():
    extracted = extract_pdf_bytes(
        make_pdf(
            [
                "Page 1",
                "Page 2",
                "Page 3",
                "Benin Risk and Resilience Assessment. Publication: March 2024.",
                *[f"Page {index}" for index in range(5, 41)],
            ]
        ),
        "long-rra.pdf",
        max_pages=12,
        sample_across_document=True,
    )

    assert [segment.page for segment in extracted.segments[:4]] == [1, 2, 3, 4]
    result = identify_uploaded_diagnostic((extracted,), country="Benin")

    assert result is not None
    assert result.name == "long-rra.pdf"
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
                "Benin contextual diagnostic.pdf",
                "Accepted equivalent diagnostic, January 2023",
            ),
        ),
        country="Benin",
    )

    assert result is not None
    assert result.kind == "accepted_equivalent"
    assert result.publication_date == date(2023, 1, 1)


def test_identifies_fcv_risk_assessment_cover_title_as_accepted_equivalent():
    result = identify_uploaded_diagnostic(
        (
            document(
                "Benin contextual diagnostic.pdf",
                "Benin FCV Risk Assessment",
            ),
        ),
        country="Benin",
    )

    assert result is not None
    assert result.kind == "accepted_equivalent"


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


def test_country_token_does_not_match_a_longer_country_name():
    assert identify_uploaded_diagnostic(
        (
            document(
                "Somaliland Risk and Resilience Assessment.pdf",
                "Somaliland country context",
            ),
        ),
        country="Mali",
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


def test_identified_diagnostic_preserves_supplied_source_position():
    documents = (
        document("same.pdf", "Benin package evidence without a diagnostic marker."),
        document("same.pdf", "Benin Risk and Resilience Assessment."),
    )

    result = identify_uploaded_diagnostic(documents, country="Benin")

    assert result is not None
    assert result.source_index == 1


def test_provenance_uses_cover_date_not_later_mission_date():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = ExtractedDocument("Guinea RRA.pdf", (
        ExtractedSegment("Guinea Risk and Resilience Assessment\nJune 2023", 1, None, "page 1"),
        ExtractedSegment("The mission took place in September 2022.", 2, None, "page 2"),
    ), ())
    provenance = diagnostic_provenance(source)
    assert provenance.publication_date == date(2023, 6, 1)
    assert provenance.date_basis == "cover"
    assert provenance.locator.page == 1
    assert "June 2023" in provenance.locator.excerpt


def test_image_only_cover_does_not_promote_body_date_to_cover():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = ExtractedDocument("Guinea RRA June 2023.pdf", (
        ExtractedSegment("Risk and Resilience Assessment. Mission: September 2022.",
                         2, None, "page 2"),
    ), ("page 1 extracted no text",))
    provenance = diagnostic_provenance(source)
    assert provenance.publication_date is None
    assert provenance.date_basis == "unestablished"
    assert provenance.locator is None


def test_docx_title_and_publication_month_can_be_separate_paragraphs():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = document("RRA.docx", "Guinea Risk and Resilience Assessment", "June 2023",
                      "Mission: September 2022")
    provenance = diagnostic_provenance(source)
    assert provenance.publication_date == date(2023, 6, 1)
    assert provenance.locator.element == "paragraph 1"


def test_filename_and_mission_dates_are_not_publication_dates():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = document("Benin RRA March 2024.docx", "Mission: September 2022")
    assert diagnostic_provenance(source).publication_date is None


def test_explicit_publication_date_on_fourth_physical_page_has_provenance():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = ExtractedDocument("RRA.pdf", (
        ExtractedSegment("Publication: March 2024", 4, None, "page 4"),
    ), ())
    provenance = diagnostic_provenance(source)
    assert provenance.publication_date == date(2024, 3, 1)
    assert provenance.date_basis == "publication_statement"
    assert provenance.locator.page == 4


def test_conflicting_cover_and_publication_statement_remain_unknown():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = document("RRA.docx", "Risk and Resilience Assessment, June 2023",
                      "Publication: September 2022")
    assert diagnostic_provenance(source).publication_date is None


def test_standalone_mission_month_is_not_a_cover_date():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = document("RRA.docx", "Benin Risk and Resilience Assessment",
                      "Mission", "September 2022")
    assert diagnostic_provenance(source).publication_date is None


def test_invalid_calendar_year_remains_unestablished():
    from cpf_fcv_reviewer.diagnostic_sources import diagnostic_provenance

    source = document("RRA.docx", "Publication: June 0000")
    assert diagnostic_provenance(source).publication_date is None
