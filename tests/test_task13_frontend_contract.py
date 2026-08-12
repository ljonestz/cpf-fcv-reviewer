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


def test_event_lifecycle_handles_result_retry_stale_stream_errors_and_double_clicks():
    harness = textwrap.dedent(
        """
        const nodes = {};
        function node() { return { hidden: false, disabled: false, value: "", children: [], handlers: {},
          addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }, append(...v) { this.children.push(...v); },
          replaceChildren(...v) { this.children = v; }, reset() {}, click() { return Promise.all((this.handlers.click || []).map(fn => fn())); },
          trigger(type) { return Promise.all((this.handlers[type] || []).map(fn => fn({preventDefault(){}}))); } }; }
        for (const id of ["#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress", "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country", "#country-detection", "#primary-upload", "#detail-level", "#submit-review", "#submit-correction", "#correction-text", "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog", "#close-process-dialog"]) nodes[id] = node();
        nodes["#cpf"].files = [{}]; nodes["#country"].value = "Chad";
        global.document = { querySelector: id => nodes[id], createElement: () => node(), createTextNode: value => ({textContent:value}) };
        global.window = { __CPF_FCV_REVIEWER_TEST__: true, setTimeout: fn => fn(), location: {assign(){}} };
        let stored = ""; global.sessionStorage = { getItem(){return stored}, setItem(k,v){stored=v}, removeItem(){stored=""} };
        global.FormData = class {};
        class FakeSource { constructor() { this.listeners = {}; this.closed = false; FakeSource.all.push(this); } addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); } close(){this.closed=true;} async emit(t, data="{}") { for (const fn of this.listeners[t] || []) await fn({data}); } error(){this.onerror?.();} }
        FakeSource.all = []; global.EventSource = FakeSource;
        const complete = { executive_judgment:"Judgment", diagnostic_title:"Diagnostic", findings:[], recommendations:[], priority_question_responses:[], limitations:[] };
        let responses = [{status:202, ok:true}, {status:200, ok:true, json:async()=>complete}];
        let calls = 0; global.fetch = async () => { calls++; return responses.shift() || {status:200, ok:true, json:async()=>complete}; };
        (async () => {
        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        hooks.watchEvents("one", "result"); const one = FakeSource.all[0]; one.error(); await one.emit("run_complete"); one.error();
        if (calls !== 2 || nodes["#results"].hidden) throw Error("202 result did not retry to completion");
        hooks.watchEvents("old", "old-result"); const old = FakeSource.all[1]; hooks.watchEvents("new", "new-result"); const newer = FakeSource.all[2]; await old.emit("run_failed", JSON.stringify({error:"review_failed"}));
        if (hooks.getActiveSource() !== newer) throw Error("stale stream mutated active stream");
        newer.error(); newer.error(); if (nodes["#return-to-intake"].hidden) throw Error("transport failure was not recoverable");
        hooks.setAssessmentId("parent"); nodes["#correction-text"].value = "context"; let resolvePost; calls = 0;
        global.fetch = () => { calls++; if (calls === 1) return new Promise(resolve => { resolvePost = resolve; }); return Promise.resolve({ok:true}); };
        const first = nodes["#submit-correction"].click(); const second = nodes["#submit-correction"].click();
        if (calls !== 1 || !nodes["#submit-correction"].disabled) throw Error("correction was not locked");
        const reset = nodes["#reset-review"].click(); resolvePost({ok:true, json:async()=>({assessment_id:"late", event_url:"late", result_url:"late"})});
        await Promise.all([first, second, reset]);
        if (stored || FakeSource.all.length !== 3) throw Error("late correction resurrected review state");
        hooks.setAssessmentId("old"); nodes["#correction-text"].value = "blocked"; let resolveDelete; calls = 0;
        global.fetch = () => { calls++; if (calls === 1) return new Promise(resolve => { resolveDelete = resolve; }); return Promise.resolve({ok:true, json:async()=>({assessment_id:"new", event_url:"new", result_url:"new-result"})}); };
        const pendingReset = nodes["#reset-review"].click(); await nodes["#submit-correction"].click();
        if (calls !== 1 || FakeSource.all.length !== 3 || stored) throw Error("correction ran during pending reset");
        nodes["#country"].value = "Chad"; nodes["#cpf"].files = [{}]; nodes["#submit-review"].disabled = false;
        await nodes["#review-form"].trigger("submit"); const current = FakeSource.all[3];
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
