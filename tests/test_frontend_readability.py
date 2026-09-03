import subprocess
import textwrap
from pathlib import Path


JS = Path("src/cpf_fcv_reviewer/static/app.js")
CSS = Path("src/cpf_fcv_reviewer/static/styles.css")


def test_detailed_readout_contracts_collapsible_accessible_sections_and_question_framing():
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    for fragment in (
        "function splitNarrativeIntoChunks(value)",
        "function renderNarrative(value",
        "function renderDisclosure(label",
        "function renderReadoutPanel(title, value, className)",
        "function appendAssessmentStanding(definitions, status, confidence)",
        "How well does the CPF respond to the RRA and current FCV dynamics?",
        "How does the CPF contribute to current FCV Strategy priorities?",
        "renderReadoutPanel(",
        "renderReadoutPanel(",
        'renderDisclosure("Basis and important limitations", "basis-limitations-panel", list)',
    ):
        assert fragment in javascript

    for fragment in (
        ".narrative-chunk",
        ".narrative-chunk > strong",
        ".readout-panel",
        ".readout-panel-rra",
        ".readout-panel-strategy",
        ".priority-summary-grid",
        ".basis-limitations-panel",
    ):
        assert fragment in css


def test_detailed_readout_chunks_narrative_and_uses_native_disclosures():
    harness = textwrap.dedent(
        r'''
        const nodes = {};
        function node(tagName = "div") {
          const element = {
            tagName: tagName.toLowerCase(), children: [], parentNode: null,
            handlers: {}, hidden: false, disabled: false, value: "", files: [],
            className: "", attributes: {}, style: {width: ""}, open: false, focused: false, tabIndex: 0,
            addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
            append(...values) {
              for (const value of values) {
                if (value && typeof value === "object") value.parentNode = this;
                this.children.push(value);
              }
            },
            replaceChildren(...values) { this.children = []; this.append(...values); },
            setAttribute(name, value) { this.attributes[name] = String(value); },
            getAttribute(name) { return this.attributes[name]; },
            removeAttribute(name) { delete this.attributes[name]; },
            focus() { this.focused = true; },
            remove() {
              if (!this.parentNode) return;
              this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
              this.parentNode = null;
            },
          };
          element.classList = {
            toggle(name, force) {
              const classes = new Set(element.className.split(/\s+/).filter(Boolean));
              const shouldHave = force === undefined ? !classes.has(name) : force;
              if (shouldHave) classes.add(name); else classes.delete(name);
              element.className = [...classes].join(" ");
              return shouldHave;
            },
            remove(...names) {
              const classes = new Set(element.className.split(/\s+/).filter(Boolean));
              names.forEach((name) => classes.delete(name));
              element.className = [...classes].join(" ");
            },
            contains(name) {
              return element.className.split(/\s+/).includes(name);
            },
          };
          let ownText = "";
          Object.defineProperty(element, "textContent", {
            get() {
              return ownText + element.children.map((child) => child?.textContent || "").join("");
            },
            set(value) { ownText = String(value); element.children = []; },
          });
          return element;
        }
        for (const id of [
          "#review-form", "#landing-view", "#landing-notice", "#review-workspace", "#progress",
          "#results", "#summary-panel", "#detailed-panel", "#corrections", "#actions",
          "#return-to-intake", "#cpf", "#country", "#country-detection", "#primary-upload",
          "#detail-level", "#submit-review", "#submit-correction", "#correction-text",
          "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog",
          "#close-process-dialog", "#progress-country", "#elapsed-time", "#remaining-time",
          "#guidance-card", "#research-recovery", "#research-recovery-heading",
          "#research-recovery-message", "#retry-research", "#evidence-status",
          "#evidence-status-label", "#evidence-status-limitation", "#result-title", "#result-context",
          "#progress-title", "#progress-fill",
        ]) nodes[id] = node();
        const progressStages = [node("li"), node("li"), node("li")];
        const progressStatuses = [node("span"), node("span"), node("span")];
        global.document = {
          querySelector: (id) => nodes[id],
          querySelectorAll: (selector) => {
            if (selector === "[data-progress-step]") return progressStages;
            if (selector === "[data-progress-status]") return progressStatuses;
            return [];
          },
          getElementById: () => null,
          createElement: (tagName) => node(tagName),
          createDocumentFragment: () => node("fragment"),
          createTextNode: (value) => { const text = node("text"); text.textContent = value; return text; },
        };
        const lifecycleMarks = [];
        let intervalId = 0;
        global.window = {
          __CPF_FCV_REVIEWER_TEST__: true,
          setTimeout: (fn) => fn(),
          clearTimeout() {},
          setInterval: () => ++intervalId,
          clearInterval: () => lifecycleMarks.push("clock-stopped"),
          matchMedia: () => ({matches: false}),
        };
        global.sessionStorage = {getItem(){return ""}, setItem(){}, removeItem(){}};
        global.FormData = class {};
        global.performance = {now: () => 0};
        class FakeSource {
          constructor() { this.listeners = {}; this.closed = false; FakeSource.all.push(this); }
          addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
          close() { this.closed = true; }
          async emit(type, data = "{}") {
            for (const fn of this.listeners[type] || []) await fn({data});
          }
        }
        FakeSource.all = [];
        global.EventSource = FakeSource;
        global.fetch = () => { lifecycleMarks.push("result-load"); return new Promise(() => {}); };

        const sentence = (number) => `Sentence ${number} explains the evidenced point.`;
        const longNarrative = Array.from({length: 9}, (_, index) => sentence(index + 1)).join(" ");
        const result = {
          metadata: {current_evidence_tier: "reduced", current_evidence_limitation: "Some current evidence was unavailable."},
          overall_read: longNarrative,
          alignment_readout: longNarrative,
          strategy_readout: "Strategy prose.",
          revision_summary: [
            {priority_area_id: "delivery#1", title: "Delivery pathway"},
            {priority_area_id: "inclusion#2", title: "Inclusive services"},
            {priority_area_id: "jobs#3", title: "Jobs and livelihoods"},
            {priority_area_id: "finance#4", title: "Climate finance"},
            {priority_area_id: "partnerships#5", title: "Local partnerships"},
          ],
          rra_driver_assessments: [],
          fcv_strategy_assessments: [{
            strategic_shift: "anticipate_better", assessment: longNarrative,
            status: "partially_aligned", confidence: "medium", gap_locus: null, evidence_ids: [],
          }],
          priority_areas: [{
            priority_area_id: "delivery#1", heading: "Delivery pathway", assessment: longNarrative,
            why_it_matters: longNarrative, recommended_action: longNarrative,
            target_locator: null, comment_reference: null, evidence_ids: [],
          }, {
            priority_area_id: "inclusion#2", heading: "Inclusive services",
            assessment: "The inclusion gap is not yet explicit.",
            why_it_matters: "Unequal access can deepen fragility.",
            recommended_action: "Name the inclusion response in the CPF.",
            target_locator: null, comment_reference: null, evidence_ids: [],
          }, {
            priority_area_id: "jobs#3", heading: "Jobs and livelihoods",
            assessment: "The jobs gap needs a clearer response.",
            why_it_matters: "Livelihoods shape resilience.",
            recommended_action: "Clarify the jobs pathway and delivery roles.",
            target_locator: null, comment_reference: null, evidence_ids: [],
          }, {
            priority_area_id: "finance#4", heading: "Climate finance",
            assessment: "Climate finance needs a clearer conflict-sensitive pathway.",
            why_it_matters: "Financing choices shape implementation feasibility.",
            recommended_action: "Clarify the finance pathway and safeguards.",
            target_locator: null, comment_reference: null, evidence_ids: [],
          }, {
            priority_area_id: "partnerships#5", heading: "Local partnerships",
            assessment: "Local partnerships are not yet described.",
            why_it_matters: "Local ownership supports durable delivery.",
            recommended_action: "Name local partners and delivery roles.",
            target_locator: null, comment_reference: null, evidence_ids: [],
          }],
          limitations: ["The RRA was not supplied."],
          document_coverage: {
            primary_document: "CPF.docx", package_documents: [], context_documents: [],
            coverage_note: "The detailed review covers the supplied CPF.",
          },
          evidence_by_id: {},
        };

        require(process.argv[1]);
        const hooks = window.__cpfFcvReviewerTestHooks;
        if (!hooks?.renderDetailedAnalysis || !hooks?.splitNarrativeIntoChunks) {
          throw Error("readability render hooks are missing");
        }
        if (!hooks?.showProgress || !hooks?.updateProgress || !hooks?.resetProgress || !hooks?.appendAssessmentStatus) {
          throw Error("progress lifecycle hooks are missing");
        }
        hooks.showProgress();
        if (!nodes["#progress-title"].focused) {
          throw Error("showProgress did not focus the holding-screen title");
        }
        hooks.updateProgress("extract");
        if (nodes["#progress-fill"].style.width !== "18%") {
          throw Error("document stage did not set the holding-screen fill");
        }
        hooks.updateProgress("research");
        if (nodes["#progress-fill"].style.width !== "58%") {
          throw Error("research stage did not set the holding-screen fill");
        }
        hooks.resetProgress();
        if (nodes["#progress-fill"].style.width !== "0%") {
          throw Error("reset did not clear the holding-screen fill");
        }
        const definitions = node("dl");
        hooks.appendAssessmentStatus(definitions, "partially_aligned");
        const badge = definitions.children[1]?.children?.find((item) => item?.className?.includes("status-badge"));
        if (!badge?.className?.includes("status-partially-aligned")) {
          throw Error("assessment status did not render its semantic class");
        }
        hooks.showProgress();
        lifecycleMarks.length = 0;
        hooks.watchEvents("events", "result");
        const completion = FakeSource.all[0].emit("run_complete");
        const clockStopIndex = lifecycleMarks.indexOf("clock-stopped");
        const resultLoadIndex = lifecycleMarks.indexOf("result-load");
        if (clockStopIndex < 0 || resultLoadIndex < 0 || clockStopIndex > resultLoadIndex) {
          throw Error("completion loaded the result before stopping the journey clock");
        }
        if (nodes["#progress-fill"].style.width !== "100%") {
          throw Error("completion did not fill the holding-screen track");
        }
        for (const stage of progressStages) {
          if (!stage.classList.contains("is-complete")
              || stage.classList.contains("is-active")
              || stage.attributes["aria-current"]) {
            throw Error("completion did not finalize progress stage state");
          }
        }
        if (progressStatuses.some((status) => status.textContent !== "Complete")) {
          throw Error("completion did not label every stage complete");
        }
        void completion;
        const chunks = hooks.splitNarrativeIntoChunks(longNarrative);
        if (chunks.length !== 3 || chunks.some((chunk) => chunk.length > 4)) {
          throw Error(`narrative was not chunked into at most four sentences: ${JSON.stringify(chunks)}`);
        }
        const findAll = (root, predicate) => [
          ...(predicate(root) ? [root] : []),
          ...(root?.children || []).flatMap((child) => findAll(child, predicate)),
        ];
        const view = hooks.renderDetailedAnalysis(result);
        const summary = hooks.renderFiveMinuteReadout(result);
        const summaryText = summary.textContent;
        if (!(summaryText.indexOf("Overall assessment") < summaryText.indexOf("How well does the CPF respond") &&
              summaryText.indexOf("How well does the CPF respond") < summaryText.indexOf("Strategy prose.") &&
              summaryText.indexOf("Strategy prose.") < summaryText.indexOf("Priority measures"))) {
          throw Error("five-minute hierarchy is incorrect");
        }
        if (!summaryText.includes("The inclusion gap is not yet explicit.") ||
            !summaryText.includes("Name the inclusion response in the CPF.") ||
            !summaryText.includes("The jobs gap needs a clearer response.") ||
            !summaryText.includes("Clarify the jobs pathway and delivery roles.")) {
          throw Error("priority summaries omitted their gap and response content");
        }
        const summaryPriorityCards = findAll(summary, (item) => item?.className === "priority-area");
        if (summaryPriorityCards.length !== 3) throw Error("five-minute readout did not cap priority summaries at three cards");
        const inclusionSummary = summaryPriorityCards.find((card) => card.textContent.includes("Inclusive services"));
        const inclusionSummaryText = inclusionSummary?.textContent || "";
        const relevanceLabel = "FCV relevance.";
        if (!inclusionSummaryText.includes(relevanceLabel) ||
            !inclusionSummaryText.includes("Unequal access can deepen fragility.") ||
            !(inclusionSummaryText.indexOf("The inclusion gap is not yet explicit.") < inclusionSummaryText.indexOf(relevanceLabel) &&
              inclusionSummaryText.indexOf(relevanceLabel) < inclusionSummaryText.indexOf("Name the inclusion response in the CPF."))) {
          throw Error("priority summaries omitted FCV relevance or rendered it out of order");
        }
        const detailedPriorityCards = findAll(view, (item) => item?.className === "priority-area");
        if (detailedPriorityCards.length !== 5) throw Error("detailed analysis did not retain all five priority areas");
        for (const title of ["Delivery pathway", "Inclusive services", "Jobs and livelihoods", "Climate finance", "Local partnerships"]) {
          if (!view.textContent.includes(title)) throw Error("detailed analysis omitted priority " + title);
        }
        const summaryLinks = findAll(summary, (item) => item?.tagName === "a");
        const linkNames = summaryLinks.map((link) => link.attributes?.["aria-label"] || "");
        if (summaryLinks.length !== 3 || new Set(linkNames).size !== 3 || ["Delivery pathway", "Inclusive services", "Jobs and livelihoods"].some((title) => !linkNames.some((name) => name.includes(title)))) {
          throw Error("priority summary links did not have unique accessible names");
        }
        const readoutPanels = findAll(summary, (item) => item?.className?.includes("readout-panel"));
        if (readoutPanels.length !== 2 || readoutPanels.some((panel) => findAll(panel, (item) => item?.tagName === "a").length)) {
          throw Error("analytical readout panels contained navigation links or were missing");
        }
        const details = findAll(view, (item) => item?.tagName === "details");
        const summaries = details.map((item) => item.children[0]?.textContent || "");
        for (const label of ["Basis and important limitations"]) {
          if (!summaries.includes(label)) throw Error(`missing accessible disclosure: ${label}`);
        }
        for (const detail of details) {
          if (detail.children[0]?.tagName !== "summary") throw Error("details lacked a native summary");
        }
        const chunksInView = findAll(view, (item) => item?.className?.startsWith("narrative-chunk"));
        if (chunksInView.length < 6) throw Error("long narrative fields were not chunked");
        for (const chunk of chunksInView) {
          const strong = findAll(chunk, (item) => item?.tagName === "strong");
          if (strong.length !== 1) throw Error("narrative chunk lacked one bold active sentence");
        }
        '''
    )
    completed = subprocess.run(
        ["node", "-e", harness, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_task3_holding_and_result_surfaces_use_compact_readable_treatment():
    css = CSS.read_text(encoding="utf-8")

    for fragment in (
        ".progress-shell",
        ".progress-track",
        ".progress-fill",
        ".progress-timing",
        ".progress-keep-open",
        ".output-card",
        ".evidence-group",
        ".traceability-panel",
        ".coverage-panel",
        ".evidence-status-panel",
    ):
        assert fragment in css
    assert "text-align: center" in css
    assert "border-radius" in css
    assert "background" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
