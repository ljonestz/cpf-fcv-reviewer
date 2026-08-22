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
        "function renderEvidenceStatusDisclosure(result)",
        "function renderTraceability(result)",
        "function renderCoverage(result)",
        "How well does the CPF respond to the RRA and current FCV dynamics?",
        "How does the CPF contribute to current FCV Strategy priorities?",
        'text("summary", "Traceability")',
        'text("summary", "Coverage and limitations")',
        'text("summary", "Evidence status")',
    ):
        assert fragment in javascript

    for fragment in (
        ".narrative-chunk",
        ".narrative-chunk > strong",
        ".traceability-panel",
        ".coverage-panel",
        ".evidence-status-panel",
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
            className: "", attributes: {}, open: false, focused: false, tabIndex: 0,
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
            focus() { this.focused = true; },
            remove() {
              if (!this.parentNode) return;
              this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
              this.parentNode = null;
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
        ]) nodes[id] = node();
        global.document = {
          querySelector: (id) => nodes[id],
          querySelectorAll: () => [],
          getElementById: () => null,
          createElement: (tagName) => node(tagName),
          createDocumentFragment: () => node("fragment"),
          createTextNode: (value) => { const text = node("text"); text.textContent = value; return text; },
        };
        global.window = {
          __CPF_FCV_REVIEWER_TEST__: true,
          setTimeout: (fn) => fn(),
          clearTimeout() {},
          matchMedia: () => ({matches: false}),
        };
        global.sessionStorage = {getItem(){return ""}, setItem(){}, removeItem(){}};
        global.FormData = class {};
        global.EventSource = class {};

        const sentence = (number) => `Sentence ${number} explains the evidenced point.`;
        const longNarrative = Array.from({length: 9}, (_, index) => sentence(index + 1)).join(" ");
        const result = {
          metadata: {current_evidence_tier: "reduced", current_evidence_limitation: "Some current evidence was unavailable."},
          overall_read: longNarrative,
          alignment_readout: longNarrative,
          revision_summary: [],
          rra_driver_assessments: [],
          fcv_strategy_assessments: [{
            strategic_shift: "anticipate_better", assessment: longNarrative,
            status: "partially_aligned", confidence: "medium", gap_locus: null, evidence_ids: [],
          }],
          priority_areas: [{
            priority_area_id: "delivery#1", heading: "Delivery pathway", assessment: longNarrative,
            why_it_matters: longNarrative, recommended_action: longNarrative,
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
        const chunks = hooks.splitNarrativeIntoChunks(longNarrative);
        if (chunks.length !== 3 || chunks.some((chunk) => chunk.length > 4)) {
          throw Error(`narrative was not chunked into at most four sentences: ${JSON.stringify(chunks)}`);
        }
        const view = hooks.renderDetailedAnalysis(result);
        const findAll = (root, predicate) => [
          ...(predicate(root) ? [root] : []),
          ...(root?.children || []).flatMap((child) => findAll(child, predicate)),
        ];
        const details = findAll(view, (item) => item?.tagName === "details");
        const summaries = details.map((item) => item.children[0]?.textContent || "");
        for (const label of ["Evidence status", "Traceability", "Coverage and limitations"]) {
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
