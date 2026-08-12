from pathlib import Path

from cpf_fcv_reviewer.app import create_app

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")


def test_interface_has_required_review_controls_and_advisory_boundary():
    html = HTML.read_text(encoding="utf-8")
    for element_id in (
        'id="cpf"',
        'id="primary-upload"',
        'id="package-documents"',
        'id="context-documents"',
        'id="review-stage"',
        'id="detail-level"',
        'id="additional-guidance"',
        'id="review-focus"',
        'id="country-detection"',
        'id="process-dialog"',
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
    assert "public version" in html.lower()
    assert "internal ITS version" in html
    assert '<label for="country">' not in html
    assert '<input id="country" name="country" type="hidden">' in html
    assert "Express review" in html
    assert "Early drafting / PCN" in html
    assert "Questions requiring a dedicated response" not in html


def test_index_route_serves_the_interface():
    app = create_app({"TESTING": True})

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert 'id="review-form"' in response.get_data(as_text=True)


def test_guided_landing_separates_essential_and_optional_inputs():
    html = HTML.read_text(encoding="utf-8")

    assert 'id="landing-view"' in html
    assert 'aria-label="How the review works"' in html
    assert "<li>Add the draft</li>" in html
    assert "<li>Add context</li>" in html
    assert "<li>Review options</li>" in html
    assert "1. Add the draft" not in html
    assert "2. Add context" not in html
    assert "3. Review options" not in html
    assert '<label for="review-stage">Review stage' in html
    assert 'id="primary-upload"' in html
    assert '<details id="additional-guidance">' in html
    assert "What should the review pay particular attention to?" in html
    assert "held only for this session" in html


def test_guided_landing_has_three_upload_zones_detail_control_and_process_dialog():
    html = HTML.read_text(encoding="utf-8")
    css = Path("src/cpf_fcv_reviewer/static/styles.css").read_text(encoding="utf-8")

    assert '<section class="hero"' in html
    assert '<div class="upload-zones">' in html
    assert 'name="package_documents"' in html
    assert 'name="context_documents"' in html
    assert '<option value="standard" selected>Standard</option>' in html
    assert "How the Express review works" in html
    assert "Stage-sensitive synthesis" in html
    assert "grid-template-columns: repeat(3, 1fr)" in css
    assert "@media (max-width: 760px)" in css
    assert "grid-template-columns: 1fr" in css


def test_country_detection_preflight_and_submit_gating_are_wired():
    javascript = JS.read_text(encoding="utf-8")

    assert 'fetch("/api/detect-country"' in javascript
    assert 'document.querySelector("#country")' in javascript
    assert "requires_confirmation" in javascript
    assert "countryCorrection" in javascript
    assert "detectionPending" in javascript
    assert "submitButton.disabled" in javascript


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


def test_browser_evidence_is_expandable_and_uses_validated_locator_content():
    javascript = JS.read_text(encoding="utf-8")

    assert 'document.createElement("details")' in javascript
    assert 'text("summary", `Evidence: ${evidenceId}`)' in javascript
    assert "result.evidence_by_id" in javascript
    assert "locator.document_title" in javascript
    assert "locator.excerpt" in javascript
    assert "innerHTML" not in javascript


def test_browser_renders_recommendations_priority_responses_and_limitations():
    javascript = JS.read_text(encoding="utf-8")

    assert 'text("h2", "Practical options")' in javascript
    assert "result.recommendations" in javascript
    assert "recommendation.target_locator" in javascript
    assert 'text("h2", "Priority questions")' in javascript
    assert "result.priority_question_responses" in javascript
    assert 'text("h2", "Limitations")' in javascript
    assert "result.limitations" in javascript


def test_interface_transitions_between_landing_progress_and_results():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'id="review-workspace" hidden' in html
    assert 'id="return-to-intake"' in html
    assert "function showLanding" in javascript
    assert "function showProgress" in javascript
    assert "function showResults" in javascript
    assert "showProgress();" in javascript
    assert "showResults();" in javascript
    assert "showLanding();" in javascript
    assert "Start a new review" in html


def test_return_to_intake_respects_the_hidden_attribute_and_landing_has_notice():
    html = HTML.read_text(encoding="utf-8")
    css = Path("src/cpf_fcv_reviewer/static/styles.css").read_text(encoding="utf-8")

    assert 'id="landing-notice"' in html
    assert 'aria-live="polite"' in html
    assert "#return-to-intake { display: block; }" not in css
