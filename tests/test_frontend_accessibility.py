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
    assert ".progress-steps li:focus-visible" in css
