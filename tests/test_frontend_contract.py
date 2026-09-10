# ruff: noqa: E501

import subprocess
import textwrap
from pathlib import Path

from cpf_fcv_reviewer.app import create_app

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")
CSS = Path("src/cpf_fcv_reviewer/static/styles.css")


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
        'id="assistant-card"',
        'id="assistant-conversation"',
        'id="assistant-input"',
        'id="assistant-send"',
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


def test_follow_on_assistant_uses_approved_shell_and_suggestion_labels():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert "What would you like to do next?" in html
    for label in (
        "Draft a peer-review email",
        "Expand a priority measure",
        "Clarify the assessment",
        "Summarise for management",
    ):
        assert label in html
    assert 'id="assistant-conversation" role="log" aria-live="polite"' in html
    assert '<label for="assistant-input">' in html
    assert '>Send<' in html
    assert "Correct source information and rerun" in html
    assert '<details id="corrections"' in html

    for fragment in (
        "function loadAssistantHistory()",
        "function prefillAssistant(",
        "function sendAssistantMessage(",
        "function renderAssistantMessage(",
        "function restoreSavedReview()",
        "if (assessmentId) void restoreSavedReview()",
        "assistantSend.disabled = true",
        'eventName === "chunk"',
        'eventName === "error"',
        'eventName === "done"',
        "/assistant",
        "finally",
    ):
        assert fragment in javascript


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


def test_correction_child_invalidates_parent_assistant_activity():
    javascript = JS.read_text(encoding="utf-8")
    handler = javascript.split(
        'submitCorrection.addEventListener("click", async () => {', 1
    )[1].split("\n});", 1)[0]

    child_handoff = handler.split("assessmentId = child.assessment_id;", 1)[0]
    for fragment in (
        "assistantRequestEpoch += 1",
        "assistantHistoryEpoch += 1",
        "assistantStreaming = false",
        'assistantConversation.setAttribute("aria-busy", "false")',
    ):
        assert fragment in child_handoff


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


def test_saved_review_restores_country_title_from_session_state():
    javascript = JS.read_text(encoding="utf-8")

    assert 'sessionStorage.getItem("cpf_fcv_country")' in javascript
    assert "savedCountry !== assessmentId" in javascript
    submit_handler = javascript.split(
        'form.addEventListener("submit", async (event) => {', 1
    )[1].split("\n});", 1)[0]
    country_write = 'sessionStorage.setItem("cpf_fcv_country", countryInput.value.trim())'
    assessment_write = 'sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId)'
    assert country_write in submit_handler
    assert submit_handler.index(country_write) < submit_handler.index(assessment_write)
    assert 'sessionStorage.removeItem("cpf_fcv_country")' in javascript


def test_start_new_review_and_result_reset_share_guarded_purge_behavior():
    javascript = JS.read_text(encoding="utf-8")

    assert "async function resetReview()" in javascript
    reset_handler = javascript.split("async function resetReview()", 1)[1].split(
        "\n}\n", 1
    )[0]
    for fragment in (
        "if (resetPending) return",
        "const resetEpoch = ++operationEpoch",
        "activeEventSource?.close()",
        'sessionStorage.removeItem("cpf_fcv_assessment_id")',
        "form.reset()",
        'method: "DELETE"',
        "The review was cleared from this browser",
    ):
        assert fragment in reset_handler
    assert 'resetReviewButton.addEventListener("click", resetReview)' in javascript
    assert 'returnToIntake.addEventListener("click", resetReview)' in javascript
    assert javascript.count('sessionStorage.removeItem("cpf_fcv_assessment_id")') == 2


def test_result_rendering_uses_connected_note_sections_and_safe_text_content():
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        'text("h2", "Overall assessment")',
        'text("h2", "Priority measures to strengthen the CPF / CEN")',
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


def test_research_failure_offers_retry_without_reupload():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'id="research-recovery"' in html
    assert 'id="retry-research"' in html
    assert "research_provider_failed" in javascript
    assert "research_timeout" in javascript
    assert "research_malformed" in javascript
    assert "research_insufficient" in javascript
    assert "function retryResearch()" in javascript
    retry_handler = javascript.split("function retryResearch()", 1)[1].split(
        "\n}\n", 1
    )[0]
    assert 'fetch(`/api/reviews/${assessmentId}/retry-research`' in retry_handler
    assert 'method: "POST"' in retry_handler
    assert "watchEvents(retry.event_url, retry.result_url, operation)" in retry_handler
    assert retry_handler.index("showProgress();") > retry_handler.index(
        "await response.json()"
    )
    assert (
        'progressMessage.textContent = "Restarting the review with '
        'current-country research"' in retry_handler
    )
    assert (
        'progressMessage.textContent = "Restarting current-country research"'
        not in retry_handler
    )
    assert "new FormData(form)" not in retry_handler
    assert "formData" not in retry_handler.lower()


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
        ("documents", "Reading documents"),
        ("research", "Establishing current country evidence"),
        ("note", "Drafting and validating the review"),
    ):
        assert f'data-progress-step="{step}"' in html
        assert label in html
    assert 'id="progress-message" role="status" aria-live="polite"' in html


def test_guided_journey_has_stage_timing_and_rotating_guidance():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        'id="progress-kicker"',
        'id="elapsed-time"',
        'id="remaining-time"',
        'id="while-we-work"',
        'id="guidance-card"',
    ):
        assert fragment in html
    assert html.count('data-progress-step="') == 3
    for fragment in (
        "const stageEstimates",
        "const guidanceCards",
        "function startJourneyClock",
        "function updateJourneyClock",
        "function stopJourneyClock",
        "function rotateGuidanceCard",
        "performance.now()",
        'matchMedia("(prefers-reduced-motion: reduce)")',
    ):
        assert fragment in javascript


def test_timer_formats_singular_and_range_copy():
    javascript = JS.read_text(encoding="utf-8")
    start = javascript.index("function formatRemainingTime(minimumMinutes, maximumMinutes)")
    end = javascript.index("\n}\n", start) + 3
    function_source = javascript[start:end]
    script = f"""
{function_source}
const cases = [
  [1, 1, "About 1 minute remaining"],
  [1, 2, "About 1-2 minutes remaining"],
  [2, 3, "About 2-3 minutes remaining"],
];
for (const [minimum, maximum, expected] of cases) {{
  const actual = formatRemainingTime(minimum, maximum);
  if (actual !== expected) {{
    throw new Error(`${{minimum}}-${{maximum}}: ${{actual}} !== ${{expected}}`);
  }}
}}
"""

    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_progress_events_never_render_backend_payload_text():
    javascript = JS.read_text(encoding="utf-8")

    for unsafe in (
        "data.claim",
        "data.source",
        "data.prompt",
        "data.reason",
        "data.missing_coverage",
        "${data.step}",
    ):
        assert unsafe not in javascript
    for fragment in (
        "const sseStageMap",
        "is-complete",
        "is-active",
        "clearInterval",
        "evidenceStatusLabels",
        "current_evidence_tier",
        "current_evidence_limitation",
    ):
        assert fragment in javascript


def test_result_removes_obsolete_evidence_status_region():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert "id=\"evidence-status\"" not in html
    assert "id=\"evidence-status-label\"" not in html
    assert "id=\"evidence-status-limitation\"" not in html
    assert "document.querySelector(\"#evidence-status\") || document.createElement(\"aside\")" in javascript


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


def test_hidden_sections_remain_hidden_when_layout_rules_set_display():
    css = CSS.read_text(encoding="utf-8")

    assert "[hidden]" in css
    assert "display: none !important" in css


def test_results_have_accessible_summary_and_detailed_tabs():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'role="tablist"' in html
    assert "Five-minute readout" in html
    assert "Detailed analysis" in html
    assert "aria-selected" in javascript
    assert "ArrowLeft" in javascript
    assert "ArrowRight" in javascript
    assert 'case "Home"' in javascript
    assert 'case "End"' in javascript


def test_summary_uses_only_canonical_result_fields():
    javascript = JS.read_text(encoding="utf-8")

    assert "result.overall_read" in javascript
    assert "result.alignment_readout" in javascript
    assert "result.revision_summary" in javascript
    assert "fetchSummary" not in javascript


def test_detailed_analysis_keeps_priority_prose_and_hides_technical_coverage():
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        "function renderDetailedAnalysis(result)",
        "result.priority_areas",
        "area.heading",
        "area.assessment",
        "area.why_it_matters",
        "area.recommended_action",
        "area.target_locator",
        "area.comment_reference",
        "result.evidence_by_id",
        "result.limitations",
        "function renderBasisAndLimitations(result)",
    ):
        assert fragment in javascript

    detailed_renderer = javascript.split("function renderDetailedAnalysisView", 1)[1].split("function inferDocumentType", 1)[0]
    for wired in (
        "renderCoverageView(result)",
        "renderEvidenceStatusDisclosure(result)",
        "renderBasisAndLimitations(result)",
    ):
        assert wired in detailed_renderer
    priority_renderer = javascript.split("function renderPriorityAreas", 1)[1].split(
        "function labelledNarrative", 1
    )[0]
    assert "renderTraceabilityForEvidence(result, area.evidence_ids)" in priority_renderer
    assert "innerHTML" not in javascript


def test_exports_share_the_validated_note_endpoint():
    javascript = JS.read_text(encoding="utf-8")

    assert '/api/reviews/${assessmentId}/export.docx${summary ? "?view=summary" : ""}' in javascript
    assert "summary/export" not in javascript
    assert 'document.createElement("a")' in javascript
    assert "downloadLink.click()" in javascript
    assert "window.location.assign" not in javascript


def test_result_header_uses_confirmed_country_type_and_coverage_context():
    javascript = JS.read_text(encoding="utf-8")

    assert 'document.querySelector("#result-title")' in javascript
    assert "countryInput.value.trim()" in javascript
    assert "inferDocumentType(result.document_coverage.primary_document)" in javascript
    assert "resultTitle.textContent" in javascript
    assert "resultContext.textContent" in javascript
    assert "result.document_coverage.primary_document" in javascript
    assert "result.metadata?.review_stage" in javascript


def test_document_type_inference_is_conservative():
    javascript = JS.read_text(encoding="utf-8")
    start = javascript.index("function inferDocumentType(primaryDocumentName)")
    end = javascript.index("\n}\n", start) + 3
    function_source = javascript[start:end]
    script = f"""
{function_source}
const cases = [
  ["Benin CEN draft.docx", "CEN"],
  ["benin-cen_v2.pdf", "CEN"],
  ["Chad CPF draft.docx", "CPF"],
  ["chad_cpf-v3.pdf", "CPF"],
  ["Chad CPF CEN draft.docx", "CPF / CEN"],
  ["Country partnership draft.docx", "CPF / CEN"],
  ["vacancy agenda.pdf", "CPF / CEN"],
];
for (const [name, expected] of cases) {{
  const actual = inferDocumentType(name);
  if (actual !== expected) throw new Error(`${{name}}: ${{actual}} !== ${{expected}}`);
}}
"""

    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_task6_summary_links_use_revision_titles_and_renderers_remain_dom_only():
    javascript = JS.read_text(encoding="utf-8")
    summary_renderer = javascript.split("function renderRevisionSummary", 1)[1].split(
        "\n}\n", 1
    )[0]

    assert "item.title" in summary_renderer
    assert "item.action" not in summary_renderer
    assert "function renderRraAssessments(result)" in javascript
    assert "function renderStrategyAssessments(result)" in javascript
    assert "innerHTML" not in javascript


def test_task6_assessment_cards_have_responsive_definition_grid_styles():
    css = CSS.read_text(encoding="utf-8")

    for class_name in (
        ".assessment-list",
        ".assessment-card",
        ".assessment-definitions",
        ".assessment-status",
    ):
        assert class_name in css
    mobile = css.split("@media (max-width: 760px)", 1)[1]
    assert ".assessment-definitions" in mobile
    assert "grid-template-columns: 1fr" in mobile


def test_task3_progress_is_a_dedicated_holding_screen_with_ticker_and_keep_open_note():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    for fragment in (
        'class="progress-shell"',
        'id="progress-track"',
        'id="progress-fill"',
        'class="progress-timing"',
        'id="guidance-card"',
        'class="progress-keep-open"',
    ):
        assert fragment in html
    assert "const progressPercent = {documents: 18, research: 58, note: 88};" in javascript
    assert "progressFill.style.width" in javascript
    assert 'progressFill.style.width = "100%"' in javascript
    assert 'progressFill.style.width = "0%"' in javascript
    assert "setProgressStages(stageOrder.length, true)" in javascript


def test_task3_result_disclosures_and_statuses_use_focused_visual_contracts():
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    for class_name in (
        ".output-card",
        ".traceability-panel",
        ".coverage-panel",
        ".basis-limitations-panel",
        ".readout-panel",
        ".evidence-group",
        ".status-aligned",
        ".status-partially-aligned",
        ".status-not-evidenced",
        ".status-not-assessable",
    ):
        assert class_name in css
    assert "status-${status.replaceAll(\"_\", \"-\")}" in javascript
    assert "#results.output-card" in css


def test_app_js_renders_current_context_verification_banner():
    completed = _run_dom_harness(
        """
        global.fetch = async () => ({status: 200, ok: true, json: async () => complete});
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.watchEvents("events", "result");
        await FakeSource.all[0].emit("run_complete");
        const rendered = collectText(nodes["#results"]);
        for (const expected of [
          "AI-generated from trusted sources — verify before use",
          "Partially verified — verify before use",
        ]) {
          if (!rendered.includes(expected)) throw Error(`result omitted ${expected}`);
        }
        })().catch(error => { console.error(error); process.exit(1); });
        """
    )

    assert completed.returncode == 0, completed.stderr


DOM_PRELUDE = textwrap.dedent(
    """
    const nodes = {};
    function node() { return { hidden: false, disabled: false, value: "", id: "", tagName: "", tabIndex: 0, focused: false, textContent: "", children: [], handlers: {}, attributes: {},
      addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }, append(...v) { this.children.push(...v); },
      setAttribute(name, value) { this.attributes[name] = String(value); }, removeAttribute(name) { delete this.attributes[name]; },
      replaceChildren(...v) { this.children = v; }, reset() {}, focus() { this.focused = true; }, click() { return Promise.all((this.handlers.click || []).map(fn => fn())); },
      trigger(type) { return Promise.all((this.handlers[type] || []).map(fn => fn({preventDefault(){}}))); } }; }
    for (const selector of ["#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress", "#progress-title", "#progress-kicker", "#progress-message", "#progress-steps", ".progress-timing", "#while-we-work", ".progress-keep-open", "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country", "#country-detection", "#primary-upload", "#submit-review", "#submit-correction", "#correction-text", "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog", "#close-process-dialog"]) nodes[selector] = node();
    nodes["#cpf"].files = [{}]; nodes["#country"].value = "Benin";
    nodes["#progress-title"].textContent = "Building your FCV review";
    nodes["#progress-kicker"].textContent = "BUILDING YOUR FCV REVIEW";
    global.document = { querySelector: selector => nodes[selector], getElementById: () => null,
      createElement: tag => Object.assign(node(), {tagName: tag}), createTextNode: value => ({textContent: value, children: []}) };
    global.window = { __CPF_FCV_REVIEWER_TEST__: true, setTimeout: fn => fn(), location: {assign(){}} };
    let stored = ""; global.sessionStorage = { getItem(){return stored}, setItem(k,v){stored=v}, removeItem(){stored=""} };
    global.FormData = class {};
    class FakeSource { constructor() { this.listeners = {}; this.closed = false; FakeSource.all.push(this); } addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); } close(){this.closed=true;} async emit(t, data="{}") { for (const fn of this.listeners[t] || []) await fn({data}); } error(){this.onerror?.();} }
    FakeSource.all = []; global.EventSource = FakeSource;
    const collectText = (root) => [
      root && typeof root.textContent === "string" ? root.textContent : "",
      ...(root?.children || []).flatMap(collectText),
    ].join(" ");
    const complete = {
      overall_read: "The draft has a sound foundation.",
      alignment_readout: "RRA prose.",
      strategy_readout: "Strategy prose.",
      revision_summary: [{priority_area_id: "results / delivery#1", title: "Clarify the delivery pathway."}],
      priority_areas: [{
        priority_area_id: "results / delivery#1", heading: "Delivery pathway",
        assessment: "The pathway is not yet explicit.",
        why_it_matters: "Readers cannot follow implementation logic.",
        recommended_action: "Add a short explanation of the pathway.",
        target_locator: {document_title: "CPF.docx", page: 4, heading: "Results"},
        evidence_ids: ["ev-1", "ev-context"], comment_reference: "QER comment 3"
      }],
      limitations: ["The RRA was not supplied."],
      document_coverage: {
        primary_document: "CPF.docx", package_documents: ["CPF package annex.docx"], context_documents: [],
        coverage_note: "The review covers the supplied CPF."
      },
      metadata: {review_stage: "concept", current_evidence_tier: "reduced", current_evidence_limitation: "Source breadth was reduced."},
      evidence_by_id: {
        "ev-1": {locator: {document_title: "CPF.docx", page: 4, heading: "Results", excerpt: "The programme will deliver results."}},
        "ev-context": {evidence_type: "current_context", verification: "partially_verified", source_url: "https://example.test/context", text: "Context note explains the regional setting."}
      }
    };
    """
)


def _run_dom_harness(body):
    return subprocess.run(
        ["node", "-e", DOM_PRELUDE + textwrap.dedent(body), str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )


def test_detailed_view_renders_evidence_sources_status_and_coverage():
    completed = _run_dom_harness(
        """
        global.fetch = async () => ({status: 200, ok: true, json: async () => complete});
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.watchEvents("events", "result");
        await FakeSource.all[0].emit("run_complete");
        const rendered = collectText(nodes["#results"]);
        for (const expected of [
          "Traceability",
          "Evidence and document locations",
          "CPF.docx | page 4 | Results",
          "The programme will deliver results.",
          "Current context | https://example.test/context",
          "Context note explains the regional setting.",
          "AI-generated from trusted sources — verify before use",
          "Partially verified — verify before use",
          "Evidence status",
          "Current evidence partially established",
          "Source breadth was reduced.",
          "Coverage and limitations",
          "CPF package annex.docx",
          "The review covers the supplied CPF.",
        ]) {
          if (!rendered.includes(expected)) throw Error(`result omitted ${expected}`);
        }
        if (rendered.includes("ev-1") || rendered.includes("ev-context")) throw Error("internal evidence ID was rendered");
        })().catch(error => { console.error(error); process.exit(1); });
        """
    )

    assert completed.returncode == 0, completed.stderr


def test_failure_screen_stops_presenting_a_running_review():
    completed = _run_dom_harness(
        """
        global.fetch = async () => ({status: 200, ok: true, json: async () => complete});
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.watchEvents("events", "result");
        await FakeSource.all[0].emit("run_failed", JSON.stringify({error: "review_failed"}));
        for (const selector of ["#progress-steps", ".progress-timing", "#while-we-work", ".progress-keep-open"]) {
          if (!nodes[selector].hidden) throw Error(`${selector} still shown on the failure screen`);
        }
        if (!nodes["#progress-title"].textContent.toLowerCase().includes("stopped")) {
          throw Error("failure heading still announces a running review");
        }
        if (nodes["#progress-kicker"].textContent.toLowerCase().includes("building")) {
          throw Error("failure kicker still announces a running review");
        }
        if (!nodes["#progress-title"].focused) throw Error("focus did not move to the failure heading");
        if (!nodes["#progress-message"].textContent.includes("Review stopped: The review could not be completed.")) {
          throw Error("failure message text changed");
        }
        if (nodes["#return-to-intake"].hidden) throw Error("failure was not recoverable");
        hooks.showProgress();
        for (const selector of ["#progress-steps", ".progress-timing", "#while-we-work", ".progress-keep-open"]) {
          if (nodes[selector].hidden) throw Error(`${selector} stayed hidden for the next run`);
        }
        if (!nodes["#progress-title"].textContent.includes("Building your FCV review")) {
          throw Error("next run kept the stopped heading");
        }
        })().catch(error => { console.error(error); process.exit(1); });
        """
    )

    assert completed.returncode == 0, completed.stderr


def test_capped_stream_close_reconnects_without_failing_the_review():
    completed = _run_dom_harness(
        """
        global.fetch = async () => ({status: 200, ok: true, json: async () => complete});
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.showProgress();
        hooks.watchEvents("events", "result");
        const source = FakeSource.all[0];
        // The server caps each SSE response: a clean capped close fires error, the browser reopens.
        source.error();
        await source.emit("open");
        source.error();
        await source.emit("open");
        source.error();
        if (!nodes["#return-to-intake"].hidden) throw Error("capped stream closes aborted the run");
        if (nodes["#progress-title"].textContent.toLowerCase().includes("stopped")) {
          throw Error("capped stream close showed the failure screen");
        }
        // Two consecutive failures with no successful reopen must still fail closed.
        source.error();
        if (nodes["#return-to-intake"].hidden) throw Error("consecutive transport failures were not surfaced");
        if (!nodes["#progress-title"].textContent.toLowerCase().includes("stopped")) {
          throw Error("consecutive transport failures did not show the failure screen");
        }
        })().catch(error => { console.error(error); process.exit(1); });
        """
    )

    assert completed.returncode == 0, completed.stderr
