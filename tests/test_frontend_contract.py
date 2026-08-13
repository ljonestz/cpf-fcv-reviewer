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


def test_guided_landing_has_three_upload_zones_and_process_dialog():
    html = HTML.read_text(encoding="utf-8")
    css = Path("src/cpf_fcv_reviewer/static/styles.css").read_text(encoding="utf-8")

    assert '<section class="hero"' in html
    assert '<div class="upload-zones">' in html
    assert 'name="package_documents"' in html
    assert 'name="context_documents"' in html
    assert 'id="detail-level"' not in html
    dialog_start = html.split('<dialog id="process-dialog"', 1)[1].split(">", 1)[0]
    assert " hidden" in dialog_start
    assert "How the Express review works" in html
    assert "Stage-sensitive synthesis" in html
    assert "grid-template-columns: repeat(3, 1fr)" in css
    assert "@media (max-width: 760px)" in css
    assert "grid-template-columns: 1fr" in css


def test_correction_prompt_uses_note_first_review_language():
    html = HTML.read_text(encoding="utf-8")

    assert "Add context or correct the review" in html
    assert "Add context or correct a finding" not in html


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


def test_result_rendering_uses_connected_note_sections_and_safe_text_content():
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        'text("h2", "Overall read")',
        'text("h2", "What to revise")',
        'text("h2", "Priority areas for strengthening")',
        'text("h2", "Limitations and document coverage")',
        "result.revision_summary",
        "result.priority_areas",
        "area.assessment",
        "area.why_it_matters",
        "area.recommended_action",
        "area.target_locator",
        "area.comment_reference",
        "result.document_coverage",
        "coverage.primary_document",
        "coverage.package_documents",
        "coverage.context_documents",
        "coverage.coverage_note",
    ):
        assert fragment in javascript
    assert "textContent" in javascript
    assert "innerHTML" not in javascript


def test_browser_evidence_is_expandable_and_uses_validated_locator_content():
    javascript = JS.read_text(encoding="utf-8")

    assert 'document.createElement("details")' in javascript
    assert 'text("summary", "Evidence and document locations")' in javascript
    assert "result.evidence_by_id" in javascript
    assert "locator.document_title" in javascript
    assert "locator.excerpt" in javascript
    assert "evidenceId" in javascript
    assert "Evidence and document locations" in javascript
    assert "text(\"summary\", `Evidence:" not in javascript
    assert "innerHTML" not in javascript


def test_long_evidence_source_labels_wrap_safely():
    css = Path("src/cpf_fcv_reviewer/static/styles.css").read_text(encoding="utf-8")

    assert ".evidence-locator" in css
    assert "overflow-wrap: anywhere" in css


def test_browser_omits_legacy_result_collections_and_question_section():
    javascript = JS.read_text(encoding="utf-8")

    for obsolete in (
        "result.findings",
        "result.recommendations",
        "result.priority_question_responses",
        'text("h2", "Priority questions")',
    ):
        assert obsolete not in javascript


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


def test_task9_intake_uses_approved_labels_and_preserves_backend_field_names():
    html = HTML.read_text(encoding="utf-8")

    for label in (
        "Draft CPF / CEN",
        "Accompanying CPF package documents",
        "RRA and supporting analytics",
    ):
        assert label in html
    for field_name in (
        'name="cpf"',
        'name="package_documents"',
        'name="context_documents"',
        'name="review_stage"',
        'name="review_focus"',
        'name="country"',
    ):
        assert field_name in html
    assert 'id="detail-level"' not in html
    assert 'name="detail_level"' not in html
    assert "Generate CPF review note" in html
    assert "Run Express review" not in html


def test_task9_progress_has_semantic_stages_and_live_message():
    html = HTML.read_text(encoding="utf-8")

    assert '<ol id="progress-steps"' in html
    assert 'aria-label="Review progress"' in html
    for step, label in (
        ("documents", "Reading the CPF package"),
        ("research", "Checking current FCV dynamics"),
        ("note", "Preparing the review note"),
    ):
        assert f'data-progress-step="{step}"' in html
        assert label in html
    assert 'id="progress-message" role="status" aria-live="polite"' in html


def test_task9_progress_mapping_uses_safe_labels_and_omits_backend_content():
    javascript = JS.read_text(encoding="utf-8")

    emitted_research_events = (
        "research_attempt",
        "research_retry",
        "research_sufficient",
    )
    for event_name in emitted_research_events:
        assert f'"{event_name}"' in javascript
    assert (
        'for (const eventName of ["research_attempt", "research_retry", '
        '"research_sufficient"])' in javascript
    )
    assert "source.addEventListener(eventName" in javascript
    for obsolete_event_name in ("research_attempt_started", "research_retrying"):
        assert obsolete_event_name not in javascript
    for stage in (
        "extract",
        "resolve_sources",
        "research",
        "build_evidence",
        "map",
        "review",
        "validate",
        "render",
    ):
        assert stage in javascript
    for unsafe_payload in ("data.claim", "data.source", "data.prompt", "${data.step}"):
        assert unsafe_payload not in javascript
    assert "progress-message" in javascript
    assert "data-progress-step" in javascript


def test_task9_css_uses_repository_owned_screener_aligned_visual_language():
    css = Path("src/cpf_fcv_reviewer/static/styles.css").read_text(encoding="utf-8")

    assert ".site-header" in css
    assert "linear-gradient" in css
    assert "--cyan" in css
    assert ".upload-badge" in css
    assert ".progress-steps" in css
    assert "@media (max-width: 760px)" in css
