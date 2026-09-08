from datetime import UTC
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest
from docx import Document

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.contracts import (
    AssessmentStatus,
    CurrentEvidenceTier,
    DiagnosticMode,
)
from cpf_fcv_reviewer.export_docx import (
    RRA_ALIGNMENT_QUESTION,
    STRATEGY_ALIGNMENT_QUESTION,
    build_docx,
)
from cpf_fcv_reviewer.registry import load_registry_bundle


LANGUAGE_MODEL_CAVEAT_TERMS = (
    "language model",
    "dates",
    "findings",
    "country or fcv expert",
)


def assert_language_model_caveat(text: str) -> None:
    lowered = text.casefold()
    for term in LANGUAGE_MODEL_CAVEAT_TERMS:
        assert term in lowered


def test_docx_reader_note_contains_synthesis_and_omits_technical_material(
    make_valid_result,
):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())

    with ZipFile(BytesIO(data)) as archive:
        assert "word/document.xml" in archive.namelist()
        ET.fromstring(archive.read("word/document.xml"))

    paragraphs = [paragraph.text for paragraph in Document(BytesIO(data)).paragraphs]
    text = "\n".join(paragraphs)

    assert result.alignment_readout in text
    assert result.strategy_readout in text
    assert text.count(result.strategy_readout) == 1
    for area in result.priority_areas:
        assert area.heading in text
        assert area.assessment in text
        assert area.why_it_matters in text
        assert area.recommended_action in text

    assert "RRA driver-to-response assessment" in text
    assert "2026-2030 FCV Strategy alignment" in text
    assert text.count("Status and confidence") == (
        len(result.rra_driver_assessments) + len(result.fcv_strategy_assessments)
    )
    assert_language_model_caveat(text)

    for omitted in (
        "Evidence and reproducibility",
        "Evidence and document locations",
        "Limitations and document coverage",
        "Coverage note",
        "Evidence reference",
        "Used for",
        "Reproducibility information",
        "Current evidence tier",
        "Gap locus",
        "Delivery mechanism",
        "Result / indicator",
        "Source: CPF.docx | Results framework | paragraph 12",
        "Excerpt: The program will support access.",
    ):
        assert omitted not in text


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
    assert RRA_ALIGNMENT_QUESTION in text
    assert STRATEGY_ALIGNMENT_QUESTION in text
    assert result.alignment_readout in text
    assert result.strategy_readout in text
    assert "Priority areas for strengthening" in text
    assert "Basis and important limitations" not in text
    assert result.priority_areas[0].heading in text
    assert result.priority_areas[0].assessment in text
    assert result.priority_areas[0].why_it_matters in text
    assert result.priority_areas[0].recommended_action in text
    assert "Target: CPF.docx | Results framework | paragraph 12" in text
    assert "Consult the designated policy owner." not in text
    assert_language_model_caveat(text)
    assert "fake-model" not in text
    assert "No RRA was available." not in text
    assert "Evidence and document locations" not in text


def test_docx_matches_detailed_html_scope_without_summary_or_technical_metadata(
    make_valid_result,
):
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

    assert "Priority measures to strengthen the CPF/CEN" not in text
    assert result.revision_summary[0].title not in text
    assert result.strategy_readout in text
    assert "Reproducibility information" not in text
    assert "Evidence and reproducibility" not in text
    assert "Evidence and document locations" not in text
    assert "Technical appendix" not in text
    assert "Consult the designated policy owner." not in text
    assert "fake-model" not in text


def test_docx_uses_question_led_overall_read_and_restrained_appendix(make_valid_result):
    result, evidence = make_valid_result
    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    headings = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.style.name.startswith(("Title", "Heading"))
    ]

    rra_question = RRA_ALIGNMENT_QUESTION
    strategy_question = STRATEGY_ALIGNMENT_QUESTION
    rra_heading = "RRA driver-to-response assessment"
    strategy_heading = "2026-2030 FCV Strategy alignment"
    assert rra_question in headings
    assert strategy_question in headings
    assert headings.index("Overall assessment") < headings.index(rra_question)
    assert headings.index(rra_question) < headings.index(rra_heading)
    assert headings.index(rra_heading) < headings.index(strategy_question)
    assert headings.index(strategy_question) < headings.index(strategy_heading)
    assert headings.index(strategy_heading) < headings.index("Priority areas for strengthening")
    overall_index = paragraphs.index("Overall assessment")
    rra_index = paragraphs.index(rra_question)
    rra_heading_index = paragraphs.index(rra_heading)
    strategy_index = paragraphs.index(strategy_question)
    strategy_heading_index = paragraphs.index(strategy_heading)
    assert result.overall_read in paragraphs[overall_index + 1 : rra_index]
    assert result.alignment_readout in paragraphs[rra_index + 1 : rra_heading_index]
    assert result.strategy_readout in paragraphs[strategy_index + 1 : strategy_heading_index]
    assert any(
        result.fcv_strategy_assessments[0].assessment in paragraph
        for paragraph in paragraphs[strategy_heading_index + 1 :]
    )
    assert "Evidence and document locations" not in headings
    assert "Reproducibility information" not in headings


def test_docx_splits_long_readout_and_bolds_each_active_lead_sentence(make_valid_result):
    result, evidence = make_valid_result
    long_read = (
        "The first sentence states the main finding. "
        "The second sentence explains the evidence. "
        "The third sentence identifies the consequence. "
        "The fourth sentence describes the implication. "
        "The fifth sentence gives the practical conclusion."
    )
    result = result.model_copy(update={"overall_read": long_read})

    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = document.paragraphs
    overall_index = next(
        index
        for index, paragraph in enumerate(paragraphs)
        if paragraph.text == "Overall assessment"
    )
    rra_question_index = next(
        index
        for index, paragraph in enumerate(paragraphs)
        if paragraph.text == RRA_ALIGNMENT_QUESTION
    )
    readout_paragraphs = paragraphs[overall_index + 1 : rra_question_index]

    assert [paragraph.text for paragraph in readout_paragraphs] == [
        "The first sentence states the main finding. The second sentence explains the evidence. "
        "The third sentence identifies the consequence. The fourth sentence describes the implication.",
        "The fifth sentence gives the practical conclusion.",
    ]
    assert readout_paragraphs[0].runs[0].text == "The first sentence states the main finding."
    assert readout_paragraphs[0].runs[0].bold is True
    assert readout_paragraphs[0].runs[1].bold is not True
    assert readout_paragraphs[1].runs[0].bold is True


def test_docx_exports_structured_assessments_with_human_labels_and_evidence(
    make_valid_result,
):
    result, evidence = make_valid_result
    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    text = "\n".join(paragraphs)
    assert "RRA driver-to-response assessment" in text
    assert "2026-2030 FCV Strategy alignment" in text
    assert paragraphs.index("RRA driver-to-response assessment") < paragraphs.index(
        "2026-2030 FCV Strategy alignment"
    )
    for label, value in (
        ("Driver", "Unequal territorial access"),
        ("CPF response", "The CPF prioritizes lagging regions."),
        ("Remaining gap", "Adaptation triggers are not defined."),
        ("Status and confidence", "Partially aligned - High confidence"),
    ):
        assert label in text
        assert value in text
    for shift in (
        "Anticipate better",
        "Differentiated approach",
        "One WBG approach to jobs",
        "Toolkit, partnerships, and staffing",
    ):
        assert shift in text
    assert "Strategic shift" in text
    assert "Assessment" in text
    assert "The CPF reflects this strategic shift in the response." in text
    assert "Delivery mechanism" not in text
    assert "Result / indicator" not in text
    assert "Gap locus" not in text
    assert "Source: CPF.docx | Results framework | paragraph 12" not in text
    assert "Excerpt: The program will support access." not in text

def test_docx_uses_distinct_empty_rra_messages(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"rra_driver_assessments": ()})
    limited_document = Document(
        BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=()))
    )
    limited_text = "\n".join(paragraph.text for paragraph in limited_document.paragraphs)
    assert "No current RRA was supplied; RRA alignment was not assessed." in limited_text
    unexpected_result = result.model_copy(
        update={
            "metadata": result.metadata.model_copy(
                update={"diagnostic_mode": DiagnosticMode.RRA_ALIGNMENT}
            )
        }
    )
    unexpected_document = Document(
        BytesIO(build_docx(unexpected_result, evidence=evidence, hydrated_referrals=()))
    )
    unexpected_text = "\n".join(
        paragraph.text for paragraph in unexpected_document.paragraphs
    )
    assert "No RRA alignment assessments were returned for this review." in unexpected_text
    assert "No current RRA was supplied; RRA alignment was not assessed." not in unexpected_text


def test_docx_includes_strategy_empty_state_sentence(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"fcv_strategy_assessments": ()})

    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    strategy_heading = "2026-2030 FCV Strategy alignment"
    empty_state = "No FCV Strategy alignment assessments were returned for this review."
    heading_index = paragraphs.index(strategy_heading)

    assert paragraphs[heading_index] == strategy_heading
    assert paragraphs[heading_index + 1] == empty_state


def test_docx_handles_not_assessable_rows_without_evidence(make_valid_result):
    result, evidence = make_valid_result
    rra = result.rra_driver_assessments[0].model_copy(
        update={
            "status": AssessmentStatus.NOT_ASSESSABLE,
            "gap_locus": None,
            "evidence_ids": (),
        }
    )
    strategy = result.fcv_strategy_assessments[0].model_copy(
        update={
            "status": AssessmentStatus.NOT_ASSESSABLE,
            "gap_locus": None,
            "evidence_ids": (),
        }
    )
    result = result.model_copy(
        update={
            "rra_driver_assessments": (rra,),
            "fcv_strategy_assessments": (
                strategy,
                *result.fcv_strategy_assessments[1:],
            ),
        }
    )

    document = Document(
        BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=()))
    )
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert text.count("Not assessable - High confidence") == 2
    assert "No supporting evidence was recorded for this assessment." not in text

def test_docx_rejects_missing_assessment_evidence_with_row_details(make_valid_result):
    result, evidence = make_valid_result
    rra = result.rra_driver_assessments[0].model_copy(
        update={"evidence_ids": ("missing-rra",)}
    )
    strategy = result.fcv_strategy_assessments[0].model_copy(
        update={"evidence_ids": ("missing-strategy",)}
    )
    result = result.model_copy(
        update={
            "rra_driver_assessments": (rra,),
            "fcv_strategy_assessments": (
                strategy,
                *result.fcv_strategy_assessments[1:],
            ),
        }
    )
    with pytest.raises(
        ValueError,
        match=(
            "Missing evidence for assessment citations: "
            "RRA rra-1: missing-rra; Strategy strategy-anticipate-better: "
            "missing-strategy"
        ),
    ):
        build_docx(result, evidence=evidence, hydrated_referrals=())


def test_docx_uses_question_led_note_sections(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert text.index("Overall assessment") < text.index(RRA_ALIGNMENT_QUESTION)
    assert text.index(RRA_ALIGNMENT_QUESTION) < text.index(
        "RRA driver-to-response assessment"
    )
    assert text.index("RRA driver-to-response assessment") < text.index(
        STRATEGY_ALIGNMENT_QUESTION
    )
    assert text.index(STRATEGY_ALIGNMENT_QUESTION) < text.index(
        "2026-2030 FCV Strategy alignment"
    )
    assert text.index("2026-2030 FCV Strategy alignment") < text.index(
        "Priority areas for strengthening"
    )
    assert "Basis and important limitations" not in text
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

    data = build_docx(
        result,
        evidence={"ctx-1": context_item, "ev-1": evidence["ev-1"]},
        hydrated_referrals=(),
    )
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert (
        "Source: Current context | CPF.docx | Results framework | paragraph 12 | "
        "https://example.test/context"
    ) not in text
    assert "Excerpt: Context source excerpt." not in text
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

    assert "Primary document: CPF.docx" not in text
    assert "Package documents: Results Framework.xlsx" not in text
    assert "Context documents: Country Context Note.pdf" not in text
    assert "Coverage note: The review covers the primary CPF draft." not in text
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
        header_xml = ET.fromstring(archive.read("word/header1.xml"))
        assert header_xml.find(".//w:shd", ns).attrib[f"{{{w}}}fill"] == "153956"
        assert header_xml.find(".//w:bottom", ns).attrib[f"{{{w}}}color"] == "13A6A4"
        assert header_xml.find(".//w:rPr/w:color", ns).attrib[f"{{{w}}}val"] == "FFFFFF"
        assert header_xml.find(".//w:txbxContent", ns) is None
        header_indent = header_xml.find(".//w:pPr/w:ind", ns)
        assert header_indent.attrib[f"{{{w}}}left"] == "-1440"
        assert header_indent.attrib[f"{{{w}}}right"] == "-1440"
        assert header_indent.attrib[f"{{{w}}}firstLine"] == "1440"


    assert document_xml.find(".//w:txbxContent", ns) is None
    alignment = styles_xml.find(".//w:style[@w:styleId='Normal']/w:pPr/w:jc", ns)
    assert alignment.attrib[f"{{{w}}}val"] == "left"
    section = document_xml.find(".//w:sectPr", ns)
    page_size = section.find("w:pgSz", ns)
    page_margins = section.find("w:pgMar", ns)
    assert page_size.attrib[f"{{{w}}}w"] == "12240"
    assert page_size.attrib[f"{{{w}}}h"] == "15840"
    assert page_margins.attrib[f"{{{w}}}top"] == "1440"
    assert page_margins.attrib[f"{{{w}}}right"] == "1440"
    assert page_margins.attrib[f"{{{w}}}bottom"] == "1440"
    assert page_margins.attrib[f"{{{w}}}left"] == "1440"
    assert page_margins.attrib[f"{{{w}}}header"] == "360"
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
        "Heading1": ("320", "160", "153956", "32"),
        "Heading2": ("240", "120", "153956", "26"),
        "Heading3": ("160", "80", "153956", "24"),
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
    assert set(list_num_ids).issubset(custom_num_ids)
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

    assert "CPF FCV review" in "".join(footer_xml.itertext())
    assert "Volatile-session export" not in "".join(footer_xml.itertext())
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

    assert "No revision summary was returned for this review." not in text
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
@pytest.mark.parametrize("summary", (False, True))
def test_docx_omits_evidence_status_and_reader_limitations(
    make_valid_result,
    tier,
    status,
    limitation,
    summary,
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

    result_limitations = result.limitations
    result_current_limitation = result.metadata.current_evidence_limitation
    paragraphs = [
        paragraph.text
        for paragraph in Document(
            BytesIO(
                build_docx(
                    result,
                    evidence=evidence,
                    hydrated_referrals=(),
                    summary=summary,
                )
            )
        ).paragraphs
    ]
    text = "\n".join(paragraphs)
    assert_language_model_caveat(text)
    assert result.overall_read in text
    assert result.alignment_readout in text
    assert result.strategy_readout in text
    assert "Basis and important limitations" not in paragraphs
    assert status not in text
    assert "Current evidence tier" not in text
    if limitation is not None:
        assert limitation not in text
        assert limitation in result_limitations
        assert result_current_limitation == limitation

def test_docx_visible_evidence_status_matches_html(make_valid_result):
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

    assert "Review based primarily on submitted documents" not in text
    assert "Current evidence tier" not in text
    assert limitation not in text

def test_export_route_requires_a_completed_traceable_result(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(
        update={
            "institutional_referral_ids": ("registry-PUB-GUARD-003",),
        }
    )
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
    with ZipFile(BytesIO(response.data)) as archive:
        assert "word/document.xml" in archive.namelist()

    summary = client.get(f"/api/reviews/{assessment_id}/export.docx?view=summary")
    assert summary.status_code == 200
    assert "CPF-FCV-Five-Minute-Readout.docx" in summary.headers["Content-Disposition"]
    assert Document(BytesIO(summary.data)).paragraphs[0].text == "Five-minute readout"
    assert client.get(f"/api/reviews/{assessment_id}/export.docx?view=unknown").status_code == 400
    app.extensions["session_store"].update(assessment_id, evidence_by_id=None)
    assert client.get(f"/api/reviews/{assessment_id}/export.docx?view=summary").status_code == 409


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


def test_docx_labels_current_context_verification():
    from cpf_fcv_reviewer.export_docx import current_context_chip_label

    assert current_context_chip_label("verified") == "Verified"
    assert current_context_chip_label("partially_verified") == "Partially verified — verify before use"
    assert current_context_chip_label("unverified") == "Unverified — verify before use"


def test_five_minute_export_preserves_actions_and_limits_detail(make_valid_result):
    result, evidence = make_valid_result
    area = result.priority_areas[0].model_copy(update={
        "assessment": "First assessment. Second assessment. Extra detail.",
        "why_it_matters": "Fragility relevance. Extra relevance.",
        "recommended_action": "First action. Second action. Third action.",
    })
    result = result.model_copy(update={"priority_areas": (area,)})
    document = Document(BytesIO(build_docx(
        result, evidence=evidence, hydrated_referrals=(), summary=True,
    )))
    paragraphs = document.paragraphs
    text = "\n".join(p.text for p in paragraphs)
    assert "Five-minute readout" in text
    assert "First assessment. Second assessment. Fragility relevance." in text
    assert "Extra detail." not in text
    assert "Extra relevance." not in text
    assert "First action. Second action. Third action." in text
    assert "Basis and important limitations" not in text
    overview = next(p for p in paragraphs if p.text.startswith("First assessment."))
    assert not any(run.bold for run in overview.runs)
    action = next(p for p in paragraphs if "First action." in p.text)
    assert all(not run.bold for run in action.runs if "First action." in run.text)
