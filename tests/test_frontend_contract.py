from pathlib import Path

from cpf_fcv_reviewer.app import create_app

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")


def test_interface_has_required_review_controls_and_advisory_boundary():
    html = HTML.read_text(encoding="utf-8")
    for element_id in (
        'id="cpf"',
        'id="supporting"',
        'id="review-stage"',
        'id="guidance"',
        'id="progress"',
        'id="results"',
        'id="correction-text"',
        'id="export-docx"',
        'id="reset-review"',
    ):
        assert element_id in html
    for prohibited_determination in (
        "clearance",
        "policy determination",
        "eligibility finding",
        "official classification",
    ):
        assert prohibited_determination in html
    assert '<label for="correction-text">' in html


def test_index_route_serves_the_interface():
    app = create_app({"TESTING": True})

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert 'id="review-form"' in response.get_data(as_text=True)


def test_browser_state_is_session_only_and_reset_clears_assessment_id():
    javascript = JS.read_text(encoding="utf-8")

    assert "sessionStorage" in javascript
    assert "localStorage" not in javascript
    assert "indexedDB" not in javascript
    assert 'sessionStorage.removeItem("cpf_fcv_assessment_id")' in javascript


def test_result_rendering_uses_text_content_with_sensitivity_and_evidence_labels():
    javascript = JS.read_text(encoding="utf-8")

    assert "textContent" in javascript
    assert "innerHTML" not in javascript
    assert "Frame cautiously" in javascript
    assert "Confirm with country team or FCV specialist" in javascript
    assert "evidence_ids" in javascript
