# ruff: noqa: E501

import subprocess
import textwrap
from pathlib import Path

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")
CSS = Path("src/cpf_fcv_reviewer/static/styles.css")


def test_express_intake_removes_priority_question_confirmation_controls():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    assert 'id="priority-questions"' not in html
    assert 'id="priority-question-list"' not in html
    assert "Questions requiring a dedicated response" not in html
    assert "function detectedQuestions" not in javascript
    assert 'checkbox.name = "priority_questions"' not in javascript
    assert "renderPriorityQuestions" not in javascript
    assert "#priority-question-list label" not in css
    assert "#priority-question-list input" not in css


def test_process_dialog_has_native_open_and_close_controls():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert 'id="process-dialog"' in html
    assert 'id="open-process-dialog"' in html
    assert 'id="close-process-dialog"' in html
    assert "showModal()" in javascript
    assert ".close()" in javascript


def test_correction_handler_switches_to_child_run_and_watches_it():
    javascript = JS.read_text(encoding="utf-8")

    assert "assessmentId = child.assessment_id" in javascript
    assert 'sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId)' in javascript
    assert "watchEvents(child.event_url, child.result_url, operation)" in javascript


def test_failure_and_reset_are_recoverable_and_keep_review_states_separate():
    javascript = JS.read_text(encoding="utf-8")

    assert "returnToIntake.hidden = false" in javascript
    assert "returnToIntake.addEventListener" in javascript
    assert "form.reset();" in javascript
    assert "results.replaceChildren();" in javascript
    assert "let activeEventSource" in javascript
    assert "activeEventSource?.close();" in javascript
    assert "catch (_error)" in javascript
    assert "finally" in javascript
    assert "The review was cleared from this browser" in javascript
    assert "landingNotice.hidden = !notice" in javascript


def test_guided_journey_cleanup_is_wired_to_existing_lifecycle_boundaries():
    javascript = JS.read_text(encoding="utf-8")

    for function_name in (
        "showResults",
        "showRecoverableFailure",
        "showResearchFailure",
        "resetReview",
    ):
        start = javascript.index(f"function {function_name}")
        end = javascript.index("\n}\n", start)
        assert "stopJourneyClock()" in javascript[start:end]
    assert "activeEventSource?.close();" in javascript
    assert "operationEpoch" in javascript


def test_progress_status_uses_allowlisted_event_names_only():
    javascript = JS.read_text(encoding="utf-8")

    assert 'source.addEventListener("step_start"' in javascript
    assert 'source.addEventListener("run_complete"' in javascript
    assert 'source.addEventListener("run_failed"' in javascript
    assert 'source.addEventListener("expired"' in javascript
    assert "JSON.parse(event.data).step" in javascript
    assert "data.error" in javascript
    assert "event.data" in javascript


def test_event_lifecycle_handles_result_retry_stale_stream_errors_and_double_clicks():
    harness = textwrap.dedent(
        """
        const nodes = {};
        function node() { return { hidden: false, disabled: false, value: "", id: "", tagName: "", tabIndex: 0, focused: false, children: [], handlers: {}, attributes: {},
          addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }, append(...v) { this.children.push(...v); },
          setAttribute(name, value) { this.attributes[name] = String(value); },
          replaceChildren(...v) { this.children = v; }, reset() {}, focus() { this.focused = true; }, click() { return Promise.all((this.handlers.click || []).map(fn => fn())); },
          trigger(type) { return Promise.all((this.handlers[type] || []).map(fn => fn({preventDefault(){}}))); } }; }
        for (const id of ["#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress", "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country", "#country-detection", "#primary-upload", "#detail-level", "#submit-review", "#submit-correction", "#correction-text", "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog", "#close-process-dialog"]) nodes[id] = node();
        nodes["#cpf"].files = [{}]; nodes["#country"].value = "Chad";
        const findElementById = (root, id) => {
          if (!root || typeof root !== "object") return null;
          if (root.id === id) return root;
          for (const child of root.children || []) {
            const match = findElementById(child, id);
            if (match) return match;
          }
          return null;
        };
        global.document = { querySelector: id => nodes[id], getElementById: id => findElementById(nodes["#results"], id), createElement: tag => Object.assign(node(), {tagName: tag}), createTextNode: value => ({textContent:value}) };
        global.window = { __CPF_FCV_REVIEWER_TEST__: true, setTimeout: fn => fn(), location: {assign(){}} };
        let stored = ""; global.sessionStorage = { getItem(){return stored}, setItem(k,v){stored=v}, removeItem(){stored=""} };
        global.FormData = class {};
        class FakeSource { constructor() { this.listeners = {}; this.closed = false; FakeSource.all.push(this); } addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); } close(){this.closed=true;} async emit(t, data="{}") { for (const fn of this.listeners[t] || []) await fn({data}); } error(){this.onerror?.();} }
        FakeSource.all = []; global.EventSource = FakeSource;
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
          evidence_by_id: {
            "ev-1": {locator: {document_title: "CPF.docx", page: 4, heading: "Results", excerpt: "The programme will deliver results."}},
            "ev-context": {evidence_type: "current_context", source_url: "https://example.test/context", text: "Context note explains the regional setting."}
          }
        };
        let responses = [{status:202, ok:true}, {status:200, ok:true, json:async()=>complete}];
        let calls = 0; global.fetch = async () => { calls++; return responses.shift() || {status:200, ok:true, json:async()=>complete}; };
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.watchEvents("one", "result"); const one = FakeSource.all[0]; one.error(); await one.emit("run_complete"); one.error();
        if (calls !== 2) throw Error("202 result did not retry to completion");
        if (nodes["#results"].hidden) throw Error("result did not render after retry");
        const findByHref = (root, href) => {
          if (!root || typeof root !== "object") return null;
          if (root.href === href) return root;
          for (const child of root.children || []) {
            const match = findByHref(child, href);
            if (match) return match;
          }
          return null;
        };
        const findById = (root, id) => {
          if (!root || typeof root !== "object") return null;
          if (root.id === id) return root;
          for (const child of root.children || []) {
            const match = findById(child, id);
            if (match) return match;
          }
          return null;
        };
        const summaryLink = findByHref(nodes["#results"], "#cpf-priority-area-1");
        if (!summaryLink) throw Error("revision summary did not link to its priority area");
        if (findByHref(nodes["#results"], "#results / delivery#1")) throw Error("raw model ID was used as a fragment");
        const prioritySection = findById(nodes["#results"], "cpf-priority-area-1");
        if (!prioritySection) throw Error("revision summary target was not rendered");
        if (prioritySection.tabIndex !== -1) throw Error("priority area was not keyboard-focusable");
        await summaryLink.click();
        if (!prioritySection.focused) throw Error("summary link did not focus its priority area");
        const collectText = (root) => [
          root && typeof root.textContent === "string" ? root.textContent : "",
          ...(root?.children || []).flatMap(collectText),
        ].join(" ");
        const renderedText = collectText(nodes["#results"]);
        for (const visibleText of [
          "The draft has a sound foundation.",
          "Clarify the delivery pathway.",
          "Delivery pathway",
          "The pathway is not yet explicit.",
          "Readers cannot follow implementation logic.",
          "Add a short explanation of the pathway.",
          "CPF.docx | page 4 | Results",
          "QER comment 3",
          "The RRA was not supplied.",
          "Basis and important limitations",
          "CPF.docx | page 4 | Results",
        ]) {
          if (!renderedText.includes(visibleText)) throw Error(`result omitted ${visibleText}`);
        }
        if (renderedText.includes("ev-1") || renderedText.includes("ev-context")) throw Error("internal evidence ID was rendered");
        const empty = {...complete, overall_read: "The empty review returned a controlled response.", revision_summary: [], priority_areas: []};
        global.fetch = async () => ({status:200, ok:true, json:async()=>empty});
        hooks.watchEvents("empty", "empty-result"); const emptySource = FakeSource.all[1]; await emptySource.emit("run_complete");
        const emptyText = collectText(nodes["#results"]);
        for (const emptyState of [
          "No revision summary was returned for this review.",
          "No priority areas were returned for this review.",
        ]) {
          if (!emptyText.includes(emptyState)) throw Error(`empty result omitted ${emptyState}`);
        }
        const findByTag = (root, tagName) => {
          if (!root || typeof root !== "object") return null;
          if (root.tagName === tagName) return root;
          for (const child of root.children || []) {
            const match = findByTag(child, tagName);
            if (match) return match;
          }
          return null;
        };
        if (findByTag(nodes["#results"], "ol")) throw Error("empty revision summary rendered a blank list");
        hooks.watchEvents("old", "old-result"); const old = FakeSource.all[2]; hooks.watchEvents("new", "new-result"); const newer = FakeSource.all[3]; await old.emit("run_failed", JSON.stringify({error:"review_failed"}));
        if (hooks.getActiveSource() !== newer) throw Error("stale stream mutated active stream");
        newer.error(); newer.error(); if (nodes["#return-to-intake"].hidden) throw Error("transport failure was not recoverable");
        hooks.setAssessmentId("parent"); nodes["#correction-text"].value = "context"; let resolvePost; calls = 0;
        global.fetch = () => { calls++; if (calls === 1) return new Promise(resolve => { resolvePost = resolve; }); return Promise.resolve({ok:true}); };
        const first = nodes["#submit-correction"].click(); const second = nodes["#submit-correction"].click();
        if (calls !== 1 || !nodes["#submit-correction"].disabled) throw Error("correction was not locked");
        const reset = nodes["#reset-review"].click(); resolvePost({ok:true, json:async()=>({assessment_id:"late", event_url:"late", result_url:"late"})});
        await Promise.all([first, second, reset]);
        if (stored || FakeSource.all.length !== 4) throw Error("late correction resurrected review state");
        hooks.setAssessmentId("old"); nodes["#correction-text"].value = "blocked"; let resolveDelete; calls = 0;
        global.fetch = () => { calls++; if (calls === 1) return new Promise(resolve => { resolveDelete = resolve; }); return Promise.resolve({ok:true, json:async()=>({assessment_id:"new", event_url:"new", result_url:"new-result"})}); };
        const pendingReset = nodes["#reset-review"].click(); await nodes["#submit-correction"].click();
        if (calls !== 1 || FakeSource.all.length !== 4 || stored) throw Error("correction ran during pending reset");
        nodes["#country"].value = "Chad"; nodes["#cpf"].files = [{}]; nodes["#submit-review"].disabled = false;
        await nodes["#review-form"].trigger("submit"); const current = FakeSource.all[4];
        if (stored !== "new" || hooks.getActiveSource() !== current) throw Error("new run did not start during pending purge");
        resolveDelete({ok:true}); await pendingReset;
        if (stored !== "new" || hooks.getActiveSource() !== current || !nodes["#landing-view"].hidden) throw Error("stale purge overwrote new run");
        hooks.setAssessmentId("old-again"); global.fetch = async () => ({ok:false}); await nodes["#reset-review"].click();
        if (nodes["#landing-notice"].hidden || !nodes["#landing-notice"].textContent.includes("not confirmed")) throw Error("non-ok purge lacked safe notice");
        })().catch(error => { console.error(error); process.exit(1); });
        """
    )
    completed = subprocess.run(
        ["node", "-e", harness, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_country_preflight_behavior_runs_real_app_handlers():
    harness = textwrap.dedent(
        """
        const nodes = {};
        function node() {
          const element = {
            hidden: false, disabled: false, value: "", files: [], children: [], focused: false,
            handlers: {}, className: "", parentNode: null,
            addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
            append(...values) {
              for (const value of values) {
                if (value && typeof value === "object") value.parentNode = this;
                this.children.push(value);
              }
            },
            replaceChildren(...values) { this.children = []; this.append(...values); },
            reset() { this.files = []; this.value = ""; },
            focus() { this.focused = true; },
            remove() {
              if (!this.parentNode) return;
              this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
              this.parentNode = null;
            },
            click() { return Promise.all((this.handlers.click || []).map((fn) => fn())); },
            trigger(type) {
              return Promise.all((this.handlers[type] || []).map((fn) => fn({preventDefault(){}})));
            },
          };
          let text = "";
          Object.defineProperty(element, "textContent", {
            get() { return text; },
            set(value) { text = String(value); this.children = []; },
          });
          return element;
        }
        for (const id of [
          "#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress",
          "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country",
          "#country-detection", "#primary-upload", "#detail-level", "#submit-review", "#submit-correction",
          "#correction-text", "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog",
          "#close-process-dialog",
        ]) nodes[id] = node();
        nodes["#country"].value = "";
        global.document = {
          querySelector: (id) => nodes[id],
          createElement: () => node(),
          createTextNode: (value) => ({textContent: value}),
        };
        nodes["#process-dialog"].hidden = true;
        global.window = {__CPF_FCV_REVIEWER_TEST__: true, setTimeout: (fn) => fn(), location: {assign(){}}};
        let stored = "";
        global.sessionStorage = {getItem(){return stored}, setItem(k, v){stored = v}, removeItem(){stored = ""}};
        global.FormData = class { append() {} };
        const deferred = () => {
          let resolve;
          const promise = new Promise((done) => { resolve = done; });
          return {promise, resolve};
        };
        const response = (country, requiresConfirmation = false) => ({
          ok: true, status: 200,
          json: async () => ({country, requires_confirmation: requiresConfirmation}),
        });
        let requests = [];
        global.fetch = () => {
          const request = deferred();
          requests.push(request);
          return request.promise;
        };
        const findInputs = (root) => [
          ...(root.type === "text" ? [root] : []),
          ...root.children.flatMap((child) => child && child.children ? findInputs(child) : []),
        ];
        const findButtons = (root) => [
          ...(root.type === "button" ? [root] : []),
          ...root.children.flatMap((child) => child && child.children ? findButtons(child) : []),
        ];
        (async () => {
          require(process.argv[1]);
          const cpf = nodes["#cpf"];
          const submit = nodes["#submit-review"];
          const detection = nodes["#country-detection"];
          const processDialog = nodes["#process-dialog"];

          if (!processDialog.hidden) throw Error("fallback dialog was not initially hidden");
          await nodes["#open-process-dialog"].click();
          if (processDialog.hidden) throw Error("fallback dialog did not open");
          await nodes["#close-process-dialog"].click();
          if (!processDialog.hidden) throw Error("fallback dialog did not close");

          cpf.files = [{name: "first.docx"}];
          const pending = cpf.trigger("change");
          if (!submit.disabled) throw Error("submit was not disabled during detection");
          requests.shift().resolve(response("Chad"));
          await pending;
          if (nodes["#country"].value !== "Chad" || submit.disabled) throw Error("high-confidence detection did not unlock submit");
          if (findInputs(detection).length !== 0) throw Error("high-confidence detection created correction input");

          cpf.files = [{name: "second.docx"}];
          const needsConfirmation = cpf.trigger("change");
          requests.shift().resolve(response("Sudan", true));
          await needsConfirmation;
          if (!submit.disabled || findInputs(detection).length !== 1 || findButtons(detection).length !== 1) throw Error("confirmation detection was not gated");
          const acceptSuggested = findButtons(detection)[0];
          if (acceptSuggested.textContent !== "Use detected country") throw Error("suggested country acceptance control was missing");
          await acceptSuggested.click();
          if (nodes["#country"].value !== "Sudan" || submit.disabled || findInputs(detection).length !== 0 || !submit.focused) throw Error("unchanged suggested country was not accepted");

          cpf.files = [{name: "third.docx"}];
          const editableConfirmation = cpf.trigger("change");
          requests.shift().resolve(response("Sudan", true));
          await editableConfirmation;
          const editableCorrection = findInputs(detection)[0];
          if (!editableCorrection) throw Error("editable confirmation input was missing");
          editableCorrection.value = "South Sudan";
          await editableCorrection.trigger("input");
          if (nodes["#country"].value !== "South Sudan" || submit.disabled) throw Error("correction did not unlock submit");

          cpf.files = [{name: "fourth.docx"}];
          const failed = cpf.trigger("change");
          requests.shift().resolve({ok: false, status: 400});
          await failed;
          if (!submit.disabled || findInputs(detection).length !== 1) throw Error("failed detection did not remain gated");

          cpf.files = [{name: "fifth.docx"}];
          const retried = cpf.trigger("change");
          requests.shift().resolve(response("Kenya"));
          await retried;
          if (detection.className !== "country-detection") throw Error("successful retry kept the error class");

          cpf.files = [{name: "stale-first.docx"}];
          const first = cpf.trigger("change");
          cpf.files = [{name: "fresh-second.docx"}];
          const second = cpf.trigger("change");
          const staleRequest = requests.shift();
          const freshRequest = requests.shift();
          freshRequest.resolve(response("Ghana"));
          await second;
          staleRequest.resolve(response("Nigeria"));
          await first;
          if (nodes["#country"].value !== "Ghana" || !detection.textContent.includes("Ghana")) throw Error("stale detection overwrote the latest country");
        })().catch((error) => { console.error(error); process.exit(1); });
        """
    )
    completed = subprocess.run(
        ["node", "-e", harness, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_assessment_rows_expose_allowlisted_status_and_confidence_labels():
    javascript = JS.read_text(encoding="utf-8")

    assert "const assessmentStatusLabels = {" in javascript
    for label in (
        'aligned: "Aligned"',
        'partially_aligned: "Partially aligned"',
        'not_evidenced: "Not evidenced"',
        'not_assessable: "Not assessable"',
    ):
        assert label in javascript
    for field in ("assessment.status", "assessment.confidence"):
        assert field in javascript
    assert "function appendAssessmentStanding(definitions, status, confidence)" in javascript
    assert 'text("dt", "Status and confidence")' in javascript
    rra_renderer = javascript.split("function renderRraAssessments(result)", 1)[1].split(
        "function renderStrategyAssessments(result)", 1
    )[0]
    strategy_renderer = javascript.split("function renderStrategyAssessments(result)", 1)[1].split(
        "function priorityAreaAnchorIds(result)", 1
    )[0]
    for renderer in (rra_renderer, strategy_renderer):
        assert "renderEvidenceGroup" not in renderer
        assert "assessment.gap_locus" not in renderer

def test_task6_result_rendering_uses_human_assessment_labels_and_truthful_empty_states():
    harness = textwrap.dedent(
        """
        const nodes = {};
        function node() {
          const element = {
            hidden: false, disabled: false, value: "", files: [], children: [], focused: false,
            handlers: {}, className: "", parentNode: null, tagName: "",
            addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
            append(...values) {
              for (const value of values) {
                if (value && typeof value === "object") value.parentNode = this;
                this.children.push(value);
              }
            },
            replaceChildren(...values) { this.children = []; this.append(...values); },
            reset() { this.files = []; this.value = ""; },
            focus() { this.focused = true; },
            remove() {
              if (!this.parentNode) return;
              this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
              this.parentNode = null;
            },
          };
          let text = "";
          Object.defineProperty(element, "textContent", {
            get() { return text; },
            set(value) { text = String(value); this.children = []; },
          });
          return element;
        }
        for (const id of [
          "#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress",
          "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country",
          "#country-detection", "#submit-review", "#submit-correction", "#correction-text",
          "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog",
          "#close-process-dialog",
        ]) nodes[id] = node();
        nodes["#country"].value = "Chad";
        global.document = {
          querySelector: (id) => nodes[id],
          createElement: (tag) => Object.assign(node(), {tagName: tag}),
          createTextNode: (value) => ({textContent: value}),
        };
        global.window = {
          __CPF_FCV_REVIEWER_TEST__: true,
          setTimeout: (fn) => fn(),
          location: {assign(){}},
        };
        global.sessionStorage = {getItem(){return ""}, setItem(){}, removeItem(){}};
        global.FormData = class {};
        class FakeSource {
          constructor() {
            this.listeners = {};
            this.closed = false;
            FakeSource.all.push(this);
          }
          addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
          close() { this.closed = true; }
          async emit(type, data = "{}") {
            for (const fn of this.listeners[type] || []) await fn({data});
          }
        }
        FakeSource.all = [];
        global.EventSource = FakeSource;

        const populated = {
          metadata: {diagnostic_mode: "rra_alignment"},
          overall_read: "Overall synthesis for the review.",
          alignment_readout: "Alignment synthesis for the review.",
          strategy_readout: "Strategy synthesis for the review.",
          revision_summary: [],
          priority_areas: [],
          rra_driver_assessments: [{
            driver: "Unequal access to services",
            cpf_response: "CPF prioritizes lagging regions.",
            delivery_mechanism: "Area-based delivery is proposed.",
            result_or_indicator: "Service access indicator.",
            remaining_gap: "Adaptation triggers are not defined.",
            status: "partially_aligned",
            confidence: "high",
            gap_locus: "monitoring_adaptation",
            evidence_ids: ["rra-evidence"],
          }],
          fcv_strategy_assessments: [
            {
              strategic_shift: "anticipate_better",
              assessment: "The CPF uses forward-looking risk analysis.",
              status: "aligned",
              confidence: "medium",
              gap_locus: null,
              evidence_ids: ["strategy-evidence"],
            },
            {
              strategic_shift: "one_wbg_jobs",
              assessment: "Jobs roles are not yet explicit.",
              status: "not_evidenced",
              confidence: "low",
              gap_locus: "cpf_narrative",
              evidence_ids: ["missing-evidence"],
            },
          ],
          limitations: [],
          document_coverage: {
            primary_document: "CPF.docx",
            package_documents: [],
            context_documents: [],
            coverage_note: "Synthetic coverage.",
          },
          evidence_by_id: {
            "rra-evidence": {
              locator: {
                document_title: "RRA.docx",
                page: 3,
                heading: "Drivers",
                excerpt: "RRA excerpt for access.",
              },
            },
            "strategy-evidence": {
              locator: {
                document_title: "FCV Strategy.pdf",
                page: 21,
                heading: "Anticipate better",
                excerpt: "Strategy excerpt for preparedness.",
              },
            },
          },
        };
        const limited = {
          ...populated,
          metadata: {diagnostic_mode: "limited_framing"},
          rra_driver_assessments: [],
          fcv_strategy_assessments: [],
        };
        const unexpectedEmpty = {
          ...populated,
          metadata: {diagnostic_mode: "rra_alignment"},
          rra_driver_assessments: [],
          fcv_strategy_assessments: [],
        };
        const responses = [populated, limited, unexpectedEmpty];
        global.fetch = async () => ({
          status: 200,
          ok: true,
          json: async () => responses.shift(),
        });

        const collectText = (root) => [
          root && typeof root.textContent === "string" ? root.textContent : "",
          ...(root?.children || []).flatMap(collectText),
        ].join(" ");
        const countTag = (root, tagName) => [
          ...(root && root.tagName === tagName ? [root] : []),
          ...(root?.children || []).flatMap((child) => countTag(child, tagName)),
        ].length;

        (async () => {
          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.watchEvents("populated", "populated-result");
          await FakeSource.all[0].emit("run_complete");
          const renderedText = collectText(nodes["#results"]);
          for (const visibleText of [
            "RRA driver-to-response assessment",
            "Unequal access to services",
            "CPF prioritizes lagging regions.",
            "Partially aligned - High confidence",
            "2026-2030 FCV Strategy alignment",
            "Anticipate better",
            "The CPF uses forward-looking risk analysis.",
            "Aligned - Medium confidence",
            "One WBG approach to jobs",
            "Jobs roles are not yet explicit.",
            "Not evidenced - Low confidence",
          ]) {
            if (!renderedText.includes(visibleText)) throw Error("result omitted " + visibleText);
          }
          for (const rawId of ["rra-evidence", "strategy-evidence", "missing-evidence"]) {
            if (renderedText.includes(rawId)) throw Error("raw evidence ID was rendered: " + rawId);
          }
          if (countTag(nodes["#results"], "section") < 2) throw Error("assessment sections were not rendered");
          if (countTag(nodes["#results"], "dl") < 2) throw Error("assessment definition lists were not rendered");
          if ((collectText(nodes["#results"]).match(/Basis and important limitations/g) || []).length !== 1) throw Error("basis disclosure count was not exactly one");

          hooks.watchEvents("limited", "limited-result");
          await FakeSource.all[1].emit("run_complete");
          const limitedText = collectText(nodes["#results"]);
          const limitedMessage = "No current RRA was supplied; RRA alignment was not assessed.";
          if (!limitedText.includes(limitedMessage)) throw Error("limited-mode RRA message was missing");
          if (limitedText.includes("No RRA driver assessments were returned for this review.")) {
            throw Error("limited mode used the unexpected-empty message");
          }

          hooks.watchEvents("unexpected-empty", "unexpected-empty-result");
          await FakeSource.all[2].emit("run_complete");
          const unexpectedText = collectText(nodes["#results"]);
          const unexpectedMessage = "No RRA driver assessments were returned for this review.";
          if (!unexpectedText.includes(unexpectedMessage)) throw Error("unexpected empty RRA message was missing");
          if (unexpectedText.includes(limitedMessage)) throw Error("unexpected empty RRA used limited-mode wording");
        })().catch((error) => { console.error(error); process.exit(1); });
        """
    )
    completed = subprocess.run(
        ["node", "-e", harness, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
