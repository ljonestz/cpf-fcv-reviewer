from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


class DocumentUnreadable(ValueError):
    """Raised when the required primary document contains too little text."""


@dataclass(frozen=True)
class ExtractedSegment:
    text: str
    page: int | None
    heading: str | None
    element: str


@dataclass(frozen=True)
class ExtractedDocument:
    name: str
    segments: tuple[ExtractedSegment, ...]
    warnings: tuple[str, ...]


def segments_from_pdf_pages(name: str, pages: list[str]) -> ExtractedDocument:
    segments: list[ExtractedSegment] = []
    warnings: list[str] = []
    for index, text in enumerate(pages, start=1):
        clean = (text or "").strip()
        if clean:
            segments.append(ExtractedSegment(clean, index, None, f"page {index}"))
        else:
            warnings.append(f"page {index} extracted no text")
    return ExtractedDocument(name, tuple(segments), tuple(warnings))


def extract_pdf_bytes(data: bytes, name: str) -> ExtractedDocument:
    reader = PdfReader(BytesIO(data))
    return segments_from_pdf_pages(name, [(page.extract_text() or "") for page in reader.pages])


def extract_docx_bytes(data: bytes, name: str) -> ExtractedDocument:
    document = Document(BytesIO(data))
    segments: list[ExtractedSegment] = []
    warnings: list[str] = []
    heading: str | None = None
    paragraph_number = 0
    table_number = 0

    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            paragraph_number += 1
            text = paragraph.text.strip()
            if not text:
                continue
            if paragraph.style and paragraph.style.name.startswith("Heading"):
                heading = text
            segments.append(
                ExtractedSegment(
                    text=text,
                    page=None,
                    heading=heading,
                    element=f"paragraph {paragraph_number}",
                )
            )
        elif child.tag.endswith("}tbl"):
            table_number += 1
            table = Table(child, document)
            for row_number, row in enumerate(table.rows, start=1):
                values = [cell.text.strip() for cell in row.cells]
                text = " | ".join(value for value in values if value)
                if text:
                    segments.append(
                        ExtractedSegment(
                            text=text,
                            page=None,
                            heading=heading,
                            element=f"table {table_number} row {row_number}",
                        )
                    )

    if document.inline_shapes:
        warnings.append(
            f"{len(document.inline_shapes)} figure(s) detected; "
            "upload a readable text/table version if they contain material evidence"
        )

    return ExtractedDocument(name, tuple(segments), tuple(warnings))


def require_readable_primary(document: ExtractedDocument) -> None:
    character_count = sum(len(segment.text) for segment in document.segments)
    if character_count < 100:
        raise DocumentUnreadable("Primary CPF/CEN is unreadable or contains too little text.")


def extract_text_bytes(data: bytes, name: str) -> ExtractedDocument:
    text = data.decode("utf-8-sig").strip()
    segment = ExtractedSegment(text, None, None, "full text")
    return ExtractedDocument(name, (segment,) if text else (), ())


def extract_document(data: bytes, name: str) -> ExtractedDocument:
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_bytes(data, name)
    if suffix == ".docx":
        return extract_docx_bytes(data, name)
    if suffix in {".txt", ".md"}:
        return extract_text_bytes(data, name)
    raise ValueError(f"Unsupported file type: {suffix}")
