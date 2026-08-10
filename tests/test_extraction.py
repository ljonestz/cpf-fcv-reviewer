from io import BytesIO

import pytest
from docx import Document

from cpf_fcv_reviewer.extraction import (
    extract_docx_bytes,
    require_readable_primary,
    segments_from_pdf_pages,
)


def make_docx() -> bytes:
    document = Document()
    document.add_heading("Strategic context", level=1)
    document.add_paragraph("The CPF identifies localized exclusion.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Outcome"
    table.cell(0, 1).text = "Indicator"
    table.cell(1, 0).text = "Access"
    table.cell(1, 1).text = "People reached"
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_docx_segments_retain_heading_and_table_locator():
    extracted = extract_docx_bytes(make_docx(), "CPF.docx")

    paragraph = next(item for item in extracted.segments if "localized" in item.text)
    table = next(item for item in extracted.segments if "People reached" in item.text)

    assert paragraph.heading == "Strategic context"
    assert paragraph.element == "paragraph 2"
    assert table.heading == "Strategic context"
    assert table.element == "table 1 row 2"


def test_pdf_segments_use_real_page_numbers_only():
    extracted = segments_from_pdf_pages(
        "CPF.pdf",
        ["First page text", "", "Third page text"],
    )

    assert [segment.page for segment in extracted.segments] == [1, 3]
    assert "page 2 extracted no text" in extracted.warnings


def test_empty_primary_is_rejected():
    with pytest.raises(ValueError, match="Primary CPF/CEN is unreadable"):
        require_readable_primary(type("Doc", (), {"segments": (), "warnings": ()})())
