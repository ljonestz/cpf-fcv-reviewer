from io import BytesIO

from docx import Document

from cpf_fcv_reviewer.export_docx import build_docx


def test_browser_fields_are_present_in_docx(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.overall_read in text
    for item in result.revision_summary:
        assert item.action in text
        assert item.priority_area_id not in text
    for area in result.priority_areas:
        for field in (
            area.heading,
            area.assessment,
            area.why_it_matters,
            area.recommended_action,
        ):
            assert field in text
        assert area.target_locator.document_title in text
        assert area.target_locator.heading in text
        assert area.target_locator.element in text
    assert result.limitations[0] in text
    assert result.document_coverage.coverage_note in text


def test_docx_and_web_note_share_empty_state_language(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={"revision_summary": (), "priority_areas": ()})
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)

    assert "No revision summary was returned for this review." in text
    assert "No priority areas were returned for this review." in text
