import subprocess
import textwrap
from pathlib import Path


JS = Path("src/cpf_fcv_reviewer/static/app.js")


COMMON_HARNESS = r'''
const nodes = {};
const createdElements = [];

function node(tagName = "div") {
  const element = {
    tagName: tagName.toLowerCase(),
    children: [],
    parentNode: null,
    handlers: {},
    hidden: false,
    disabled: false,
    value: "",
    files: [],
    className: "",
    attributes: {},
    dataset: {},
    focused: false,
    clicked: 0,
    classList: {
      toggle() {},
      remove() {},
    },
    addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
    async trigger(type, event = {target: this, preventDefault() {}}) {
      for (const fn of this.handlers[type] || []) await fn(event);
    },
    append(...values) {
      for (const value of values) {
        if (value == null) continue;
        if (typeof value === "object") value.parentNode = this;
        this.children.push(value);
      }
    },
    replaceChildren(...values) { this.children = []; this.append(...values); },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name]; },
    removeAttribute(name) { delete this.attributes[name]; },
    focus() { this.focused = true; },
    click() { this.clicked += 1; },
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
  "#progress-message", "#progress-country", "#elapsed-time", "#remaining-time", "#guidance-card",
  "#results", "#summary-panel", "#detailed-panel", "#corrections", "#actions", "#return-to-intake",
  "#cpf", "#country", "#country-detection", "#submit-review", "#submit-correction", "#correction-text",
  "#export-docx", "#reset-review", "#process-dialog", "#open-process-dialog", "#close-process-dialog",
  "#research-recovery", "#research-recovery-heading", "#research-recovery-message", "#retry-research",
  "#evidence-status", "#evidence-status-label", "#evidence-status-limitation", "#result-title", "#result-context",
]) nodes[id] = node();

const body = node("body");
global.document = {
  body,
  querySelector: (selector) => nodes[selector],
  querySelectorAll: () => [],
  createElement: (tagName) => {
    const element = node(tagName);
    createdElements.push(element);
    return element;
  },
  createDocumentFragment: () => node("fragment"),
  createTextNode: (value) => {
    const textNode = node("text");
    textNode.textContent = value;
    return textNode;
  },
};
global.window = {
  __CPF_FCV_REVIEWER_TEST__: true,
  setTimeout: (fn) => fn(),
  clearTimeout() {},
  setInterval: () => 1,
  clearInterval() {},
  matchMedia: () => ({matches: false}),
  location: {href: "/results", assign() { this.assigned = true; }},
};
global.performance = {now: () => 0};
global.sessionStorage = {getItem() {return "";}, setItem() {}, removeItem() {}};
global.FormData = class {};
global.EventSource = class {};
'''


def run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", script, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )


def test_docx_download_fetches_blob_and_keeps_results_page_on_recoverable_errors():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
        (async () => {
          nodes["#results"].hidden = false;
          nodes["#landing-view"].hidden = true;
          nodes["#actions"].hidden = false;
          let status = 500;
          const requests = [];
          const blobs = [];
          const objectUrls = [];
          const revokedUrls = [];
          global.URL = {
            createObjectURL(blob) {
              blobs.push(blob);
              const url = `blob:cpf-${blobs.length}`;
              objectUrls.push(url);
              return url;
            },
            revokeObjectURL(url) { revokedUrls.push(url); },
          };
          global.fetch = async (url) => {
            requests.push(url);
            if (status === 200) {
              return {
                ok: true,
                status,
                blob: async () => ({kind: "docx"}),
              };
            }
            return {ok: false, status};
          };

          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.setAssessmentId("assessment-1");
          const find = (root, predicate) => [
            ...(predicate(root) ? [root] : []),
            ...(root?.children || []).flatMap((child) => find(child, predicate)),
          ];

          for (const expectedStatus of [409, 410, 500]) {
            status = expectedStatus;
            await nodes["#export-docx"].trigger("click");
            if (requests.at(-1) !== "/api/reviews/assessment-1/export.docx") {
              throw Error("download did not request the review export endpoint");
            }
            if (nodes["#results"].hidden || !nodes["#landing-view"].hidden) {
              throw Error(`download error navigated away from results for HTTP ${expectedStatus}`);
            }
            if (window.location.assigned || window.location.href !== "/results") {
              throw Error(`download error changed the current page for HTTP ${expectedStatus}`);
            }
            const notices = find(nodes["#actions"], (item) => item?.className === "download-error");
            if (notices.length !== 1 || notices[0].hidden || !notices[0].textContent.includes("download")) {
              throw Error(`download error was not shown inline for HTTP ${expectedStatus}`);
            }
          }

          status = 200;
          await nodes["#export-docx"].trigger("click");
          const links = createdElements.filter((item) => item.tagName === "a");
          const link = links.at(-1);
          if (!link || link.clicked !== 1) throw Error("successful download did not trigger an anchor download");
          if (link.href !== "blob:cpf-1" || link.download !== "CPF-FCV-Review.docx") {
            throw Error("successful download did not preserve the DOCX filename and blob URL");
          }
          if (blobs.length !== 1 || revokedUrls.length !== 1 || revokedUrls[0] !== "blob:cpf-1") {
            throw Error("successful download did not consume and revoke the response blob URL");
          }
          const notices = find(nodes["#actions"], (item) => item?.className === "download-error");
          if (!notices[0].hidden || notices[0].textContent) {
            throw Error("a stale download error remained visible after a successful retry");
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_strategy_summary_names_each_shift_before_its_assessment():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
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
        const result = {
          metadata: {},
          overall_read: "Overall assessment.",
          alignment_readout: "RRA alignment assessment.",
          revision_summary: [],
          priority_areas: [],
          rra_driver_assessments: [],
          fcv_strategy_assessments: [
            {strategic_shift: "anticipate_better", assessment: "The CPF anticipates risks."},
            {strategic_shift: "differentiated_approach", assessment: "The CPF differentiates its approach."},
            {strategic_shift: "one_wbg_jobs", assessment: "The CPF addresses jobs through a One WBG lens."},
            {strategic_shift: "toolkit_partnerships_staffing", assessment: "The CPF uses partnerships and staffing."},
          ],
          limitations: [],
          document_coverage: {
            primary_document: "CPF.docx",
            package_documents: [],
            context_documents: [],
            coverage_note: "Synthetic coverage.",
          },
          evidence_by_id: {},
        };
        global.fetch = async () => ({ok: true, status: 200, json: async () => result});

        (async () => {
          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.watchEvents("events", "result");
          await FakeSource.all[0].emit("run_complete");
          const summary = nodes["#summary-panel"];
          const summaryText = summary.textContent;
          const expectedPairs = [
            ["Anticipate better", "The CPF anticipates risks."],
            ["Differentiated approach", "The CPF differentiates its approach."],
            ["One WBG approach to jobs", "The CPF addresses jobs through a One WBG lens."],
            ["Toolkit, partnerships, and staffing", "The CPF uses partnerships and staffing."],
          ];
          for (const [label, assessment] of expectedPairs) {
            const labelIndex = summaryText.indexOf(label);
            const assessmentIndex = summaryText.indexOf(assessment);
            if (labelIndex < 0 || assessmentIndex < 0 || labelIndex > assessmentIndex) {
              throw Error(`summary did not name ${label} before its assessment`);
            }
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr
