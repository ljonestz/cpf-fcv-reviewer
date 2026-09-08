"""Restyle saved review exports locally without another model assessment."""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cpf_fcv_reviewer.export_docx import (  # noqa: E402
    ADVISORY_NOTE,
    _apply_report_layout,
    _configure_document,
)


def restyle(source: Path, destination: Path, *, summary: bool, country: str) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    document = Document(source)
    created_at = document.core_properties.created or datetime.now(UTC)
    remove = False
    for paragraph in list(document.paragraphs):
        if paragraph.text == "Basis and important limitations":
            remove = True
        if remove:
            paragraph._element.getparent().remove(paragraph._element)
        elif "AI-assisted advisory first pass" in paragraph.text:
            paragraph.text = ADVISORY_NOTE
        elif paragraph.style.name == "Title":
            label = "five-minute readout" if summary else "CPF FCV review"
            paragraph.text = f"{country} {label}"
    _configure_document(document, created_at=created_at)
    _apply_report_layout(document, summary=summary, created_at=created_at)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--country", required=True)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    restyle(args.source, args.destination, summary=args.summary, country=args.country)
