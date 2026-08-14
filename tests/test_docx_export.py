from datetime import UTC
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import CurrentEvidenceTier
from cpf_fcv_reviewer.export_docx import build_docx
from cpf_fcv_reviewer.registry import load_registry_bundle


def test_docx_contains_same_result_and_source_locator(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(
        result,
        evidence=evidence,
        hydrated_referrals=(
            {
                "entry_id": "SYN-REF-001",
                "approved_text": "Consult the designated policy owner.",
                "version": "1.0.0-test",
            },
        ),
    )
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.overall_read in text
    assert "Overall assessment" in text
    assert result.overall_read in text
    assert "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy" in text
    assert result.alignment_readout in text
    assert "Priority measures to strengthen the CPF/CEN" in text
    assert "Priority areas for strengthening" in text
    assert "Limitations and document coverage" in text
    assert result.revision_summary[0].action in text
    assert result.priority_areas[0].heading in text
    assert result.priority_areas[0].assessment in text
    assert result.priority_areas[0].why_it_matters in text
    assert result.priority_areas[0].recommended_action in text
    assert "CPF.docx | Results framework | paragraph 12" in text
    assert "Target: CPF.docx | Results framework | paragraph 12" in text
    assert "The review covers the primary CPF draft." in text
    assert "Consult the designated policy owner." in text
    assert "Public version." in text
    assert "public or non-sensitive material" in text
    assert "fake-model" in text
    assert "No RRA was available." in text
    assert "ev-1" not in text
    assert "Questions for confirmation" not in text
    assert "Priority questions" not in text
    assert "Findings" not in text
    assert "Recommendations" not in text
    assert "Practical options" not in text


def test_docx_uses_note_first_sections_and_omits_question_section(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert text.index("Overall assessment") < text.index("How the draft responds")
    assert text.index("How the draft responds") < text.index(
        "Priority measures to strengthen the CPF/CEN"
    )
    assert text.index("Priority measures to strengthen the CPF/CEN") < text.index(
        "Priority areas for strengthening"
    )
    assert text.index("Priority areas for strengthening") < text.index(
        "Limitations and document coverage"
    )
    assert "Questions for confirmation" not in text
    assert "Priority questions" not in text
    assert "ev-1" not in text


def test_withheld_content_is_not_rendered_as_draft_language(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Suggested ready-to-paste text" not in text


def test_docx_renders_context_evidence_with_human_source_label(make_valid_result):
    result, evidence = make_valid_result
    context_item = evidence["ev-1"].model_copy(
        update={
            "evidence_id": "ctx-1",
            "evidence_type": "current_context",
            "locator": evidence["ev-1"].locator,
            "source_url": "https://example.test/context",
            "text": "Context source excerpt.",
        }
    )
    area = result.priority_areas[0].model_copy(update={"evidence_ids": ("ctx-1",)})
    result = result.model_copy(update={"priority_areas": (area,)})

    data = build_docx(result, evidence={"ctx-1": context_item}, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert (
        "Source: Current context | CPF.docx | Results framework | paragraph 12 | "
        "https://example.test/context"
    ) in text
    assert "Excerpt: Context source excerpt." in text
    assert "ctx-1" not in text


def test_docx_rejects_priority_area_with_missing_evidence(make_valid_result):
    result, _ = make_valid_result

    with pytest.raises(ValueError, match="Missing evidence for priority area"):
        build_docx(result, evidence={}, hydrated_referrals=())


def test_docx_preserves_coverage_buckets_and_optional_comment(make_valid_result):
    result, evidence = make_valid_result
    coverage = result.document_coverage.model_copy(
        update={
            "package_documents": ("Results Framework.xlsx",),
            "context_documents": ("Country Context Note.pdf",),
        }
    )
    area = result.priority_areas[0].model_copy(update={"comment_reference": "QER comment 4"})
    result = result.model_copy(update={"document_coverage": coverage, "priority_areas": (area,)})

    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert "Primary document: CPF.docx" in text
    assert "Package documents: Results Framework.xlsx" in text
    assert "Context documents: Country Context Note.pdf" in text
    assert "Coverage note: The review covers the primary CPF draft." in text
    assert "Comment addressed: QER comment 4" in text


def test_docx_encodes_standard_business_brief_tokens(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    w = ns["w"]

    with ZipFile(BytesIO(data)) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        styles_xml = ET.fromstring(archive.read("word/styles.xml"))
        numbering_xml = ET.fromstring(archive.read("word/numbering.xml"))

    section = document_xml.find(".//w:sectPr", ns)
    page_size = section.find("w:pgSz", ns)
    page_margins = section.find("w:pgMar", ns)
    assert page_size.attrib[f"{{{w}}}w"] == "12240"
    assert page_size.attrib[f"{{{w}}}h"] == "15840"
    assert page_margins.attrib[f"{{{w}}}top"] == "1440"
    assert page_margins.attrib[f"{{{w}}}right"] == "1440"
    assert page_margins.attrib[f"{{{w}}}bottom"] == "1440"
    assert page_margins.attrib[f"{{{w}}}left"] == "1440"
    assert page_margins.attrib[f"{{{w}}}header"] == "708"
    assert page_margins.attrib[f"{{{w}}}footer"] == "708"

    def style(style_id):
        return styles_xml.find(f".//w:style[@w:styleId='{style_id}']", ns)

    normal_spacing = style("Normal").find("w:pPr/w:spacing", ns)
    assert normal_spacing.attrib[f"{{{w}}}after"] == "120"
    assert normal_spacing.attrib[f"{{{w}}}line"] == "264"
    normal_run_properties = style("Normal").find("w:rPr", ns)
    normal_fonts = normal_run_properties.find("w:rFonts", ns)
    assert normal_fonts.attrib[f"{{{w}}}ascii"] == "Calibri"
    assert normal_fonts.attrib[f"{{{w}}}hAnsi"] == "Calibri"
    assert normal_run_properties.find("w:sz", ns).attrib[f"{{{w}}}val"] == "22"
    expected_headings = {
        "Heading1": ("320", "160", "2E74B5", "32"),
        "Heading2": ("240", "120", "2E74B5", "26"),
        "Heading3": ("160", "80", "1F4D78", "24"),
    }
    for style_id, (before, after, color, size) in expected_headings.items():
        heading = style(style_id)
        spacing = heading.find("w:pPr/w:spacing", ns)
        assert spacing.attrib[f"{{{w}}}before"] == before
        assert spacing.attrib[f"{{{w}}}after"] == after
        assert heading.find("w:rPr/w:color", ns).attrib[f"{{{w}}}val"] == color
        assert heading.find("w:rPr/w:sz", ns).attrib[f"{{{w}}}val"] == size

    custom_lists = []
    for abstract in numbering_xml.findall("w:abstractNum", ns):
        level = abstract.find("w:lvl", ns)
        if level is None:
            continue
        fmt = level.find("w:numFmt", ns)
        indent = level.find("w:pPr/w:ind", ns)
        if fmt is not None and indent is not None:
            custom_lists.append(
                (
                    fmt.attrib[f"{{{w}}}val"],
                    indent.attrib[f"{{{w}}}left"],
                    indent.attrib[f"{{{w}}}hanging"],
                )
            )
    assert ("decimal", "720", "360") in custom_lists
    assert ("bullet", "720", "360") in custom_lists

    list_num_ids = []
    for paragraph in document_xml.findall(".//w:body/w:p", ns):
        num_id = paragraph.find("w:pPr/w:numPr/w:numId", ns)
        if num_id is not None:
            list_num_ids.append(num_id.attrib[f"{{{w}}}val"])
    custom_num_ids = {
        num.attrib[f"{{{w}}}numId"]
        for num in numbering_xml.findall("w:num", ns)
        if num.find("w:abstractNumId", ns) is not None
        and num.find("w:abstractNumId", ns).attrib[f"{{{w}}}val"]
        in {
            abstract.attrib[f"{{{w}}}abstractNumId"]
            for abstract in numbering_xml.findall("w:abstractNum", ns)
            if abstract.find("w:nsid", ns) is not None
            and abstract.find("w:nsid", ns).attrib[f"{{{w}}}val"]
            in {"C0F00001", "C0F00002"}
        }
    }
    assert set(list_num_ids) == custom_num_ids
    assert len(custom_num_ids) == 2


def test_docx_core_properties_are_neutral_and_match_result_timestamp(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    properties = document.core_properties

    expected_timestamp = result.metadata.created_at.astimezone(UTC).replace(
        microsecond=0
    )
    assert properties.author == "CPF FCV Reviewer"
    assert properties.last_modified_by == "CPF FCV Reviewer"
    assert properties.created == expected_timestamp
    assert properties.modified == expected_timestamp


def test_docx_footer_contains_muted_page_field(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    with ZipFile(BytesIO(data)) as archive:
        footer_xml = ET.fromstring(archive.read("word/footer1.xml"))

    assert "Volatile-session export" in "".join(footer_xml.itertext())
    assert footer_xml.find(".//w:fldChar[@w:fldCharType='begin']", ns) is not None
    instruction = footer_xml.find(".//w:instrText", ns)
    assert instruction is not None
    assert instruction.text == " PAGE "
    assert footer_xml.find(".//w:fldChar[@w:fldCharType='end']", ns) is not None


def test_docx_empty_narrative_collections_have_explicit_empty_states(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"revision_summary": (), "priority_areas": ()})

    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert "No revision summary was returned for this review." in text
    assert "No priority areas were returned for this review." in text


@pytest.mark.parametrize(
    ("tier", "status", "limitation"),
    (
        (CurrentEvidenceTier.FULL, "Current evidence established", None),
        (
            CurrentEvidenceTier.REDUCED,
            "Current evidence partially established",
            "Only one public source was established recently.",
        ),
        (
            CurrentEvidenceTier.DOCUMENT_LED,
            "Review based primarily on submitted documents",
            "Independent current-country research was unavailable.",
        ),
    ),
)
def test_docx_places_exact_evidence_status_before_limitations(
    make_valid_result,
    tier,
    status,
    limitation,
):
    result, evidence = make_valid_result
    metadata = result.metadata.model_copy(
        update={
            "current_evidence_tier": tier,
            "current_evidence_limitation": limitation,
        }
    )
    limitations = result.limitations if limitation is None else (*result.limitations, limitation)
    result = result.model_copy(update={"metadata": metadata, "limitations": limitations})

    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    limitations_heading = paragraphs.index("Limitations and document coverage")

    assert paragraphs[limitations_heading - 1] == status
    assert paragraphs.count(status) == 1
    if limitation is not None:
        assert paragraphs.count(limitation) == 1


def test_docx_reproducibility_metadata_includes_evidence_status(make_valid_result):
    result, evidence = make_valid_result
    limitation = "Independent current-country research was unavailable."
    result = result.model_copy(
        update={
            "metadata": result.metadata.model_copy(
                update={
                    "current_evidence_tier": CurrentEvidenceTier.DOCUMENT_LED,
                    "current_evidence_limitation": limitation,
                }
            ),
            "limitations": (*result.limitations, limitation),
        }
    )

    text = "\n".join(
        paragraph.text
        for paragraph in Document(
            BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=()))
        ).paragraphs
    )

    assert "Current evidence tier: document_led" in text
    assert f"Current evidence limitation: {limitation}" in text


def test_export_route_requires_a_completed_traceable_result(make_valid_result):
    result, evidence = make_valid_result
    registry = load_registry_bundle(
        Path("tests/fixtures/registry_bundle.synthetic.json"),
        allow_synthetic=True,
    )
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"registry_bundle": registry},
    )
    assessment_id = app.extensions["session_store"].create({"status": "created"})
    client = app.test_client()

    pending = client.get(f"/api/reviews/{assessment_id}/export.docx")
    assert pending.status_code == 202

    app.extensions["session_store"].update(
        assessment_id,
        status="complete",
        result=result.model_dump(mode="json"),
        evidence_by_id={key: item.model_dump(mode="json") for key, item in evidence.items()},
    )
    response = client.get(f"/api/reviews/{assessment_id}/export.docx")

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "filename=CPF-FCV-Review.docx" in response.headers["Content-Disposition"]


def test_background_run_persists_traceable_evidence(make_valid_result):
    result, evidence = make_valid_result

    class FakeOrchestrator:
        def run(self, context, emit):
            return {
                **context,
                "result": result,
                "evidence_pack": SimpleNamespace(evidence=tuple(evidence.values())),
            }

    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"review_orchestrator": FakeOrchestrator()},
    )
    assessment_id = app.extensions["session_store"].create({"status": "created", "corrections": []})

    from cpf_fcv_reviewer.routes import run_assessment

    run_assessment(app, assessment_id)

    state = app.extensions["session_store"].get(assessment_id)
    assert state.payload["status"] == "complete"
    assert state.payload["evidence_by_id"]["ev-1"]["evidence_id"] == "ev-1"
