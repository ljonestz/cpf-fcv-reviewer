from pathlib import Path

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")
CSS = Path("src/cpf_fcv_reviewer/static/styles.css")


def test_summary_tab_and_panel_are_selected_first():
    html = HTML.read_text(encoding="utf-8")

    assert (
        'id="result-tab-summary" role="tab" aria-selected="true" '
        'aria-controls="summary-panel" tabindex="0"' in html
    )
    assert (
        'id="result-tab-detailed" role="tab" aria-selected="false" '
        'aria-controls="detailed-panel" tabindex="-1"' in html
    )
    assert 'id="summary-panel" role="tabpanel"' in html
    detailed_panel = html.split('id="detailed-panel"', 1)[1].split(">", 1)[0]
    assert 'role="tabpanel"' in detailed_panel
    assert " hidden" in detailed_panel


def test_result_tabs_have_roving_keyboard_state_and_linked_panels():
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        "function setResultView(view)",
        'tab.setAttribute("aria-selected", String(isSelected))',
        "tab.tabIndex = isSelected ? 0 : -1",
        "panel.hidden = !isSelected",
        'case "ArrowLeft"',
        'case "ArrowRight"',
        'case "Home"',
        'case "End"',
    ):
        assert fragment in javascript


def test_changing_result_tabs_is_client_side_only():
    javascript = JS.read_text(encoding="utf-8")
    assert "function setResultView(view)" in javascript
    assert "function handleResultTabKeydown(event)" in javascript
    tab_state = javascript.split("function setResultView(view)", 1)[1].split(
        "\n}\n", 1
    )[0]
    keyboard_handler = javascript.split(
        "function handleResultTabKeydown(event)", 1
    )[1].split("\n}\n", 1)[0]

    assert "fetch(" not in tab_state
    assert "fetch(" not in keyboard_handler
    assert "EventSource" not in tab_state
    assert "EventSource" not in keyboard_handler


def test_corrections_remain_outside_both_tabpanels():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="summary-panel"' in html
    assert 'id="detailed-panel"' in html
    summary_end = html.index("</section>", html.index('id="summary-panel"'))
    detailed_end = html.index("</section>", html.index('id="detailed-panel"'))
    corrections = html.index('id="corrections"')

    assert corrections > summary_end
    assert corrections > detailed_end


def test_completed_result_heading_is_focusable_and_receives_focus():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'id="result-title" tabindex="-1"' in html
    render_result = javascript.split("function renderResult(result)", 1)[1].split(
        "\n}\n", 1
    )[0]
    assert "showResults();" in render_result
    assert "resultTitle.focus({preventScroll: true});" in render_result
    assert render_result.index("showResults();") < render_result.index("resultTitle.focus")


def test_research_recovery_is_focusable_and_retry_is_failure_specific():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'id="research-recovery-heading" tabindex="-1"' in html
    assert 'id="research-recovery" hidden aria-labelledby="research-recovery-heading"' in html
    assert 'id="research-recovery-message" role="status" aria-live="polite"' in html
    assert 'id="retry-research" type="button"' in html
    research_failure = javascript.split("function showResearchFailure", 1)[1].split(
        "\n}\n", 1
    )[0]
    generic_failure = javascript.split("function showRecoverableFailure", 1)[1].split(
        "\n}\n", 1
    )[0]
    assert "researchRecoveryHeading.focus({preventScroll: true})" in research_failure
    assert "retryResearchButton.hidden = false" in research_failure
    assert "retryResearchButton.hidden = true" in generic_failure
    assert "returnToIntake.hidden = false" in research_failure


def test_mobile_result_tabs_stay_horizontal_for_left_right_navigation():
    css = CSS.read_text(encoding="utf-8")
    mobile = css.split("@media (max-width: 760px)", 1)[1]

    assert "#actions, .result-tabs" not in mobile
    assert ".result-tabs { flex-wrap: wrap; }" in mobile


def test_guided_journey_has_live_regions_and_reduced_motion_support():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    assert 'id="progress" hidden aria-labelledby="progress-title"' in html
    assert 'id="progress-message" role="status" aria-live="polite"' in html
    assert 'id="while-we-work" aria-live="off"' in html
    assert 'id="evidence-status" role="status"' in html
    assert "aria-current" in javascript
    assert ".progress-stage" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".progress-stage, .progress-stage::before, .guidance-card" in css


def test_guided_journey_focus_styles_are_visible():
    css = CSS.read_text(encoding="utf-8")

    assert ":focus-visible" in css
    assert "details summary:focus-visible" in css


def test_assessment_renderers_use_semantic_sections_and_definition_lists():
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        "function renderRraAssessments(result)",
        "function renderStrategyAssessments(result)",
        'text("h3", "RRA driver-to-response assessment")',
        'text("h3", "2026-2030 FCV Strategy alignment")',
        'document.createElement("section")',
        'document.createElement("dl")',
        'document.createElement("dt")',
        'document.createElement("dd")',
        "assessment.driver",
        "assessment.cpf_response",
        "assessment.delivery_mechanism",
        "assessment.result_or_indicator",
        "assessment.remaining_gap",
        "assessment.strategic_shift",
        "assessment.assessment",
        "assessment.status",
        "assessment.confidence",
        "assessment.gap_locus",
        "renderEvidenceGroup(result, assessment.evidence_ids)",
        "No current RRA was supplied; RRA alignment was not assessed.",
    ):
        assert fragment in javascript

    assert "innerHTML" not in javascript


def test_task3_holding_screen_limits_live_announcements_and_preserves_control_focus_styles():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    assert 'class="progress-shell"' in html
    assert 'id="progress-title" tabindex="-1"' in html
    assert 'id="progress-track" class="progress-track" aria-hidden="true"' in html
    assert 'id="progress-message" role="status" aria-live="polite"' in html
    assert 'id="while-we-work" aria-live="off"' in html
    assert 'class="progress-keep-open"' in html
    assert "progressFill.style.width" in javascript
    assert "progressTitle.focus({preventScroll: true});" in javascript
    progress_show = javascript.split("function showProgress()", 1)[1].split(
        "\n}\n", 1
    )[0]
    assert progress_show.index("progress.hidden = false;") < progress_show.index(
        "progressTitle.focus({preventScroll: true});"
    )
    assert ".progress-stage + .progress-stage::before" in css
    assert "details summary:focus-visible" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "progress-track" in css and "progress-fill" in css

    reduced_motion = css.split("@media (prefers-reduced-motion: reduce)", 1)[1].split(
        "@media (max-width", 1
    )[0]
    assert ".progress-stage + .progress-stage::before { animation: none; transition: none; }" in reduced_motion
    assert ".progress-stage.is-active .progress-stage-node" in reduced_motion
    assert ".progress-stage.is-complete + .progress-stage::before" in reduced_motion

    mobile = css.split("@media (max-width: 760px)", 1)[1]
    mobile_progress = mobile.split(".progress-steps {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: 1fr;" in mobile_progress
    assert ".progress-stage + .progress-stage::before" in mobile
    assert "right: auto;" in mobile
    assert "width: 2px;" in mobile


def test_task3_result_status_colors_are_supplementary_and_long_content_wraps_on_mobile():
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    for status in (
        "status-aligned",
        "status-partially-aligned",
        "status-not-evidenced",
        "status-not-assessable",
    ):
        assert status in css
    assert "status-badge" in javascript
    assert "min-width: 0" in css
    assert "overflow-wrap: anywhere" in css
    mobile = css.split("@media (max-width: 760px)", 1)[1]
    for fragment in (".result-header", ".result-context", "#actions", ".progress-shell"):
        assert fragment in mobile
