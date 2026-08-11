from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .contracts import EvidenceItem, ReviewResult

SENSITIVITY_LABELS = {
    "direct": "Suitable to state directly",
    "cautious": "Frame cautiously",
    "confirm": "Confirm with country team or FCV specialist",
    "withhold": "Do not suggest for inclusion without guidance",
}

BLUE = RGBColor(0x2E, 0x74, 0xB5)
DARK_BLUE = RGBColor(0x1F, 0x4D, 0x78)
MUTED = RGBColor(0x66, 0x70, 0x85)


def _set_style_font(style, *, name: str, size: float, color: RGBColor) -> None:
    style.font.name = name
    style.font.size = Pt(size)
    style.font.color.rgb = color
    style.element.rPr.rFonts.set(qn("w:ascii"), name)
    style.element.rPr.rFonts.set(qn("w:hAnsi"), name)


def _configure_document(document: Document) -> None:
    section = document.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    _set_style_font(normal, name="Calibri", size=11, color=RGBColor(0, 0, 0))
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1

    title = document.styles["Title"]
    _set_style_font(title, name="Calibri", size=23, color=RGBColor(0, 0, 0))
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(8)

    heading_tokens = (
        ("Heading 1", 16, BLUE, 16, 8),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, DARK_BLUE, 8, 4),
    )
    for name, size, color, before, after in heading_tokens:
        style = document.styles[name]
        _set_style_font(style, name="Calibri", size=size, color=color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    bullet = document.styles["List Bullet"]
    _set_style_font(bullet, name="Calibri", size=11, color=RGBColor(0, 0, 0))
    bullet.paragraph_format.left_indent = Inches(0.5)
    bullet.paragraph_format.first_line_indent = Inches(-0.25)
    bullet.paragraph_format.space_after = Pt(8)
    bullet.paragraph_format.line_spacing = 1.167

    header = section.header.paragraphs[0]
    header.text = "CPF FCV REVIEW | ADVISORY FIRST PASS"
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header.paragraph_format.space_after = Pt(0)
    for run in header.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(8.5)
        run.font.color.rgb = MUTED

    footer = section.footer.paragraphs[0]
    footer.text = "Volatile-session export"
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.paragraph_format.space_before = Pt(0)
    for run in footer.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(8.5)
        run.font.color.rgb = MUTED


def locator_text(item: EvidenceItem) -> str:
    locator = item.locator
    if locator is None:
        return "Analytical inference; no document locator"
    parts = [locator.document_title]
    if locator.page is not None:
        parts.append(f"page {locator.page}")
    if locator.heading:
        parts.append(locator.heading)
    if locator.element:
        parts.append(locator.element)
    return " | ".join(parts)


def build_docx(
    result: ReviewResult,
    *,
    evidence: dict[str, EvidenceItem],
    hydrated_referrals: tuple[dict, ...],
) -> bytes:
    document = Document()
    _configure_document(document)

    document.add_heading("CPF FCV Review", level=0)
    advisory = document.add_paragraph()
    advisory_run = advisory.add_run(
        "AI-assisted advisory first pass. This is not clearance, policy advice, "
        "a compliance finding, an eligibility determination, or an official "
        "classification."
    )
    advisory_run.bold = True
    advisory_run.font.color.rgb = DARK_BLUE

    document.add_heading("Executive judgment", level=1)
    document.add_paragraph(result.executive_judgment)
    document.add_heading(result.diagnostic_title, level=1)

    for finding in result.findings:
        document.add_heading(finding.title, level=2)
        document.add_paragraph(finding.narrative)
        document.add_paragraph(f"Sensitivity: {SENSITIVITY_LABELS[finding.sensitivity.value]}")
        for evidence_id in finding.evidence_ids:
            item = evidence.get(evidence_id)
            if item is None:
                continue
            excerpt = item.locator.excerpt if item.locator else item.text
            document.add_paragraph(f"Source: {locator_text(item)}\nExcerpt: {excerpt}")

    if result.recommendations:
        document.add_heading("Practical options", level=1)
        for recommendation in result.recommendations:
            document.add_heading(recommendation.action, level=2)
            document.add_paragraph(recommendation.why_it_matters)
            document.add_paragraph(
                f"Target: {recommendation.target_locator.document_title} | "
                f"{recommendation.target_locator.heading or ''} | "
                f"{recommendation.target_locator.element or ''}"
            )
            document.add_paragraph(
                f"Sensitivity: {SENSITIVITY_LABELS[recommendation.sensitivity.value]}"
            )

    if result.priority_question_responses:
        document.add_heading("Priority questions", level=1)
        for response in result.priority_question_responses:
            document.add_heading(response.question, level=2)
            document.add_paragraph(response.direct_answer)
            if response.limitation:
                document.add_paragraph(f"Limitation: {response.limitation}")
            document.add_paragraph(
                f"Evidence: {', '.join(response.evidence_ids) or 'No retained evidence'}"
            )

    if hydrated_referrals:
        document.add_heading("Matters for confirmation", level=1)
        for referral in hydrated_referrals:
            document.add_paragraph(referral["approved_text"])
            document.add_paragraph(f"Registry: {referral['entry_id']} | {referral['version']}")

    document.add_heading("Limitations", level=1)
    if result.limitations:
        for limitation in result.limitations:
            document.add_paragraph(limitation, style="List Bullet")
    else:
        document.add_paragraph("No additional limitations recorded.")

    document.add_heading("Reproducibility metadata", level=1)
    metadata = result.metadata
    for label, value in (
        ("Run", metadata.run_id),
        ("Created", metadata.created_at.isoformat()),
        ("Review stage", metadata.review_stage),
        ("Application", metadata.app_release),
        ("Schema", metadata.schema_version),
        ("Rubric", metadata.rubric_version),
        ("Prompts", metadata.prompt_bundle_version),
        ("Model", metadata.model_id),
        ("Diagnostic mode", metadata.diagnostic_mode.value),
        ("Repair count", str(metadata.repair_count)),
    ):
        document.add_paragraph(f"{label}: {value}")

    for registry_name, version in sorted(metadata.registry_versions.items()):
        document.add_paragraph(f"Registry {registry_name}: {version}")

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()
