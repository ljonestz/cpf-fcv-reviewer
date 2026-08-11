from io import BytesIO

from docx import Document

from cpf_fcv_reviewer.export_docx import build_docx


def test_browser_fields_are_present_in_docx(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.executive_judgment in text
    for finding in result.findings:
        assert finding.title in text
        assert finding.narrative in text
    for recommendation in result.recommendations:
        assert recommendation.action in text
        assert recommendation.why_it_matters in text
