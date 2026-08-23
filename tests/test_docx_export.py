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
    assert RRA_ALIGNMENT_QUESTION in text
    assert STRATEGY_ALIGNMENT_QUESTION in text
    assert result.alignment_readout in text
    assert "Priority areas for strengthening" in text
    assert "Limitations and document coverage" in text
    assert result.priority_areas[0].heading in text
    assert result.priority_areas[0].assessment in text
    assert result.priority_areas[0].why_it_matters in text
    assert result.priority_areas[0].recommended_action in text
    assert "CPF.docx | Results framework | paragraph 12" in text
    assert "Target: CPF.docx | Results framework | paragraph 12" in text
    assert "The review covers the primary CPF draft." in text
    assert "Consult the designated policy owner." not in text
    assert "Public version." in text
    assert "public or non-sensitive material" in text
    assert "fake-model" not in text
    assert "No RRA was available." in text
    assert "ev-1" not in text
    assert "Questions for confirmation" not in text
    assert "Priority questions" not in text
    assert "Findings" not in text
    assert "Recommendations" not in text
    assert "Practical options" not in text



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
    assert "Reproducibility information" not in text
    assert "Technical appendix" not in text
    assert "Consult the designated policy owner." not in text
    assert "fake-model" not in text
    assert "Evidence and document locations" in text


def test_docx_uses_question_led_overall_read_and_restrained_appendix(make_valid_result):
    result, evidence = make_valid_result
    document = Document(BytesIO(build_docx(result, evidence=evidence, hydrated_referrals=())))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    headings = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.style.name.startswith(("Title", "Heading"))
    ]

    rra_question = "How well does the CPF package align with the RRA and current FCV dynamics?"
    strategy_question = "How does the CPF package contribute to the FCV Strategy's core priorities?"
    assert rra_question in headings
    assert strategy_question in headings
    assert headings.index("Overall assessment") < headings.index(rra_question)
    assert headings.index(rra_question) < headings.index(strategy_question)
    assert headings.index(strategy_question) < headings.index("RRA driver-to-response assessment")
    overall_index = paragraphs.index("Overall assessment")
    rra_index = paragraphs.index(rra_question)
    strategy_index = paragraphs.index(strategy_question)
    assert result.overall_read in paragraphs[overall_index + 1 : rra_index]
    assert result.alignment_readout in paragraphs[rra_index + 1 : strategy_index]
    assert result.fcv_strategy_assessments[0].assessment in paragraphs[strategy_index + 1 :]

    evidence_heading = "Evidence and document locations"
    assert evidence_heading in headings
    assert "Reproducibility information" not in headings
    assert headings.index("Limitations and document coverage") < headings.index(evidence_heading)

    evidence_index = paragraphs.index(evidence_heading)
    source_index = next(
        index
        for index, paragraph in enumerate(paragraphs)
        if paragraph.startswith("Source: ")
    )
    assert source_index > evidence_index


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
        if paragraph.text == "How well does the CPF package align with the RRA and current FCV dynamics?"
    )
    strategy_question_index = next(
        index
        for index, paragraph in enumerate(paragraphs)
        if paragraph.text == "How does the CPF package contribute to the FCV Strategy's core priorities?"
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
    assert paragraphs.index("RRA driver-to-response assessment") > paragraphs.index(
        result.alignment_readout
    )
    assert paragraphs.index("2026-2030 FCV Strategy alignment") > paragraphs.index(
        "RRA driver-to-response assessment"
    )
    assert paragraphs.index("2026-2030 FCV Strategy alignment") < paragraphs.index(
        "Priority areas for strengthening"
    )
    for label, value in (
        ("Driver", "Unequal territorial access"),
        ("CPF response", "The CPF prioritizes lagging regions."),
        ("Delivery mechanism", "Area-based delivery is proposed."),
        ("Result / indicator", "A service-access indicator is included."),
        ("Remaining gap", "Adaptation triggers are not defined."),
        ("Status", "Partially aligned"),
        ("Confidence", "High"),
        ("Gap locus", "Monitoring and adaptation"),
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
    assert "Source: CPF.docx | Results framework | paragraph 12" in text
    assert "Excerpt: The program will support access." in text
    for raw_value in (
        "anticipate_better",
        "differentiated_approach",
        "one_wbg_jobs",
        "toolkit_partnerships_staffing",
        "partially_aligned",
        "monitoring_adaptation",
        "high",
        "rra-1",
        "strategy-anticipate-better",
        "ev-1",
    ):
        assert raw_value not in text


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

    assert text.count("No supporting evidence was recorded for this assessment.") == 2
    assert text.count("Not assessable") >= 2


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
    assert text.index(RRA_ALIGNMENT_QUESTION) < text.index(STRATEGY_ALIGNMENT_QUESTION)
    assert text.index(STRATEGY_ALIGNMENT_QUESTION) < text.index(
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

    data = build_docx(
        result,
        evidence={"ctx-1": context_item, "ev-1": evidence["ev-1"]},
        hydrated_referrals=(),
    )
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
    assert list_num_ids
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

    assert "Review based primarily on submitted documents" in text
    assert limitation in text


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
