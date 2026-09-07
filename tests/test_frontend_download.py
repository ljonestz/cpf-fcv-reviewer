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
  "#assistant-card", "#assistant-conversation", "#assistant-form", "#assistant-input", "#assistant-send", "#assistant-status",
  "#assistant-suggestions",
  "#export-docx", "#export-readout-docx", "#reset-review", "#process-dialog",
  "#open-process-dialog", "#close-process-dialog",
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
            return {ok: status === 202, status};
          };

          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.setAssessmentId("assessment-1");
          const find = (root, predicate) => [
            ...(predicate(root) ? [root] : []),
            ...(root?.children || []).flatMap((child) => find(child, predicate)),
          ];

          for (const expectedStatus of [202, 409, 410, 500]) {
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
          await nodes["#export-readout-docx"].trigger("click");
          const summaryLink = createdElements.filter((item) => item.tagName === "a").at(-1);
          if (requests.at(-1) !== "/api/reviews/assessment-1/export.docx?view=summary" ||
              summaryLink.download !== "CPF-FCV-Five-Minute-Readout.docx" ||
              summaryLink.clicked !== 1) {
            throw Error("five-minute download did not use its endpoint and filename");
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


def test_strategy_summary_uses_single_strategy_readout_prose_panel():
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
          strategy_readout: "The CPF strategy readout explains the current FCV priorities.",
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
          const strategyQuestion = "How does the CPF contribute to current FCV Strategy priorities?";
          const strategyProse = "The CPF strategy readout explains the current FCV priorities.";
          const questionIndex = summaryText.indexOf(strategyQuestion);
          const proseIndex = summaryText.indexOf(strategyProse);
          if (questionIndex < 0 || proseIndex < questionIndex) {
            throw Error("summary did not render the strategy prose panel");
          }
          const strategyLabels = ["Anticipate better", "Differentiated approach", "One WBG approach to jobs", "Toolkit, partnerships, and staffing"];
          for (const label of strategyLabels) {
            if (summaryText.includes(label)) throw Error("summary rendered a detailed Strategy card: " + label);
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_follow_on_assistant_restores_history_prefills_without_sending_and_streams_in_order():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
        const suggestions = [
          node("button"), node("button"), node("button"), node("button"),
        ];
        const labels = [
          "Draft a peer-review email", "Expand a priority measure",
          "Clarify the assessment", "Summarise for management",
        ];
        suggestions.forEach((item, index) => {
          item.dataset.assistantPrompt = labels[index] + " prompt";
        });
        const originalQuerySelectorAll = document.querySelectorAll;
        document.querySelectorAll = (selector) => selector === "[data-assistant-suggestion]"
          ? suggestions : originalQuerySelectorAll(selector);
        let postReader;
        let releaseSecondChunk;
        const secondChunk = new Promise((resolve) => { releaseSecondChunk = resolve; });
        let postCount = 0;
        global.fetch = async (url, options) => {
          if (url.endsWith("/assistant") && options?.method === "POST") {
            postCount += 1;
            postReader = {
              chunks: [
                'event: chunk\ndata: {"text":"New "}\n\n',
                'event: chunk\ndata: {"text":"response"}\n\nevent: done\ndata: {}\n\n',
              ],
              index: 0,
              async read() {
                if (this.index === 1) await secondChunk;
                if (this.index >= this.chunks.length) return {done: true};
                return {done: false, value: this.chunks[this.index++]};
              },
            };
            return {ok: true, body: {getReader: () => postReader}};
          }
          if (url.endsWith("/assistant")) {
            return {
              ok: true,
              json: async () => [
                {role: "user", content: "Restored question"},
                {role: "assistant", content: "Restored answer"},
              ],
            };
          }
          throw Error("unexpected request: " + url);
        };

        (async () => {
          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.setAssessmentId("assessment-1");
          await hooks.loadAssistantHistory();
          const conversation = nodes["#assistant-conversation"];
          if (!conversation.textContent.includes("Restored question") ||
              !conversation.textContent.includes("Restored answer")) {
            throw Error("history was not restored");
          }
          const restoredOrder = conversation.children.map((item) => item.textContent).join("|");
          if (restoredOrder.indexOf("Restored question") > restoredOrder.indexOf("Restored answer")) {
            throw Error("restored messages are out of order");
          }

          await suggestions[1].trigger("click");
          if (nodes["#assistant-input"].value !== "Expand a priority measure prompt") {
            throw Error("suggestion did not only prefill the editable input");
          }
          if (postCount !== 0) throw Error("suggestion triggered a model request");

          nodes["#assistant-input"].value = "Please expand this.";
          const sendPromise = nodes["#assistant-form"].trigger("submit");
          await Promise.resolve();
          if (!nodes["#assistant-send"].disabled) throw Error("Send was not disabled during streaming");
          releaseSecondChunk();
          await sendPromise;
          if (nodes["#assistant-send"].disabled) throw Error("Send stayed disabled after streaming");
          const messageTexts = conversation.children.map((item) => item.textContent).join("|");
          if (messageTexts.indexOf("Please expand this.") > messageTexts.indexOf("New response")) {
            throw Error("new messages are out of order");
          }
          if (!messageTexts.includes("New response")) throw Error("assistant response was not rendered");
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_follow_on_assistant_shows_safe_inline_error_and_reenables_send():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
        global.fetch = async (url, options) => {
          if (!url.endsWith("/assistant") || options?.method !== "POST") {
            throw Error("unexpected request: " + url);
          }
          return {
            ok: true,
            body: {
              getReader: () => ({
                sent: false,
                async read() {
                  if (this.sent) return {done: true};
                  this.sent = true;
                  return {
                    done: false,
                    value: 'event: error\ndata: {"error":"<script>alert(1)</script>"}\n\n',
                  };
                },
              }),
            },
          };
        };

        (async () => {
          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.setAssessmentId("assessment-1");
          nodes["#assistant-input"].value = "Please clarify this.";
          await nodes["#assistant-form"].trigger("submit");
          if (nodes["#assistant-send"].disabled) throw Error("Send stayed disabled after an error");
          const status = nodes["#assistant-status"];
          if (status.hidden || !status.textContent.includes("could not complete")) {
            throw Error("safe inline assistant error was not shown");
          }
          if (status.textContent.includes("<script>")) throw Error("provider error was rendered unsafely");
          if (!nodes["#assistant-conversation"].textContent.includes("Please clarify this.")) {
            throw Error("user message was not retained in the conversation");
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_saved_review_and_assistant_history_restore_after_refresh():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
        const result = {
          metadata: {},
          overall_read: "Overall assessment.",
          alignment_readout: "RRA alignment assessment.",
          strategy_readout: "Strategy assessment.",
          revision_summary: [],
          priority_areas: [],
          rra_driver_assessments: [],
          fcv_strategy_assessments: [],
          limitations: [],
          document_coverage: {
            primary_document: "CPF.docx",
            package_documents: [],
            context_documents: [],
            coverage_note: "Synthetic coverage.",
          },
          evidence_by_id: {},
        };
        global.sessionStorage = {
          getItem(key) { return key === "cpf_fcv_assessment_id" ? "assessment-1" : ""; },
          setItem() {},
          removeItem() {},
        };
        const requests = [];
        global.fetch = async (url) => {
          requests.push(url);
          if (url.endsWith("/result")) {
            return {ok: true, status: 200, json: async () => result};
          }
          if (url.endsWith("/assistant")) {
            return {
              ok: true,
              status: 200,
              json: async () => [
                {role: "user", content: "Restored question"},
                {role: "assistant", content: "Restored answer"},
              ],
            };
          }
          throw Error("unexpected request: " + url);
        };

        (async () => {
          require(process.argv[1]);
          await new Promise((resolve) => setTimeout(resolve, 0));
          await new Promise((resolve) => setTimeout(resolve, 0));
          if (nodes["#results"].hidden || nodes["#assistant-card"].hidden) {
            throw Error("saved completed review was not reopened");
          }
          if (!nodes["#assistant-conversation"].textContent.includes("Restored answer")) {
            throw Error("saved assistant history was not restored");
          }
          if (!requests.includes("/api/reviews/assessment-1/result") ||
              !requests.includes("/api/reviews/assessment-1/assistant")) {
            throw Error("refresh did not request the saved review and history");
          }
          if (!nodes["#result-title"].textContent.startsWith("CPF")) {
            throw Error("refresh rendered a blank country prefix");
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_history_load_blocks_send_until_the_snapshot_is_rendered():
    harness = textwrap.dedent(
        COMMON_HARNESS
        + r'''
        let resolveHistory;
        let postCount = 0;
        global.fetch = (url, options) => {
          if (options?.method === "POST") {
            postCount += 1;
            throw Error("send should not start while history is loading");
          }
          return new Promise((resolve) => { resolveHistory = resolve; });
        };

        (async () => {
          require(process.argv[1]);
          const hooks = window.__cpfFcvReviewerTestHooks;
          hooks.setAssessmentId("assessment-1");
          const loading = hooks.loadAssistantHistory();
          await Promise.resolve();
          if (!nodes["#assistant-send"].disabled) {
            throw Error("Send was enabled while history was loading");
          }
          nodes["#assistant-input"].value = "Race this history request.";
          await nodes["#assistant-form"].trigger("submit");
          if (postCount !== 0) throw Error("a send raced the history snapshot");
          resolveHistory({ok: true, status: 200, json: async () => []});
          await loading;
          if (nodes["#assistant-send"].disabled) {
            throw Error("Send stayed disabled after history loaded");
          }
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
    )
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr
