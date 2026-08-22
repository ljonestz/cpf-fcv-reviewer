import subprocess
import textwrap
from pathlib import Path


JS = Path("src/cpf_fcv_reviewer/static/app.js")


def test_large_primary_document_skips_detector_and_small_file_detection_is_unchanged():
    javascript = JS.read_text(encoding="utf-8")
    assert "COUNTRY_DETECTION_MAX_BYTES" in javascript
    assert "file.size > COUNTRY_DETECTION_MAX_BYTES" in javascript

    harness = textwrap.dedent(
        r'''
        (async () => {
        const nodes = {};
        function node(tagName = "div") {
          const element = {
            tagName: tagName.toLowerCase(), children: [], parentNode: null,
            handlers: {}, hidden: false, disabled: false, value: "", files: [],
            className: "", attributes: {}, type: "", autocomplete: "",
            addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
            async trigger(type) {
              for (const fn of this.handlers[type] || []) await fn({target: this, preventDefault(){}});
            },
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
            focus() {},
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
          "#results", "#corrections", "#actions", "#return-to-intake", "#cpf", "#country",
          "#country-detection", "#submit-review", "#submit-correction", "#correction-text",
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
          setTimeout: (fn) => fn(), clearTimeout() {},
          setInterval: () => 1, clearInterval() {},
          matchMedia: () => ({matches: false}),
        };
        global.sessionStorage = {getItem(){return ""}, setItem(){}, removeItem(){}};
        global.FormData = class { constructor(source) { this.source = source; } append() {} };
        global.EventSource = class { addEventListener() {} close() {} };
        let finalUploads = 0;
        let detectorCalls = 0;
        global.fetch = async (url) => {
          if (url === "/api/detect-country") {
            detectorCalls += 1;
            return {ok: true, json: async () => ({country: "Chad", requires_confirmation: false})};
          }
          if (url === "/api/reviews") {
            finalUploads += 1;
            return {ok: true, json: async () => ({assessment_id: "test", event_url: "/events", result_url: "/result"})};
          }
          return {ok: true, json: async () => ({})};
        };

        require(process.argv[1]);
        const cpf = nodes["#cpf"];
        const submit = nodes["#submit-review"];
        const detection = nodes["#country-detection"];
        const country = nodes["#country"];
        const findInputs = (root) => [
          ...(root?.tagName === "input" ? [root] : []),
          ...(root?.children || []).flatMap((child) => findInputs(child)),
        ];

        cpf.files = [{name: "large.pdf", size: 2 * 1024 * 1024 + 1}];
        await cpf.trigger("change");
        if (detectorCalls !== 0) throw Error("large CPF was uploaded to automatic detection");
        if (!detection.textContent.includes("Enter the country")) {
          throw Error("large CPF did not prompt for manual country confirmation");
        }
        if (!submit.disabled) throw Error("large CPF did not require manual confirmation");
        const manualCountry = findInputs(detection)[0];
        manualCountry.value = "Haiti";
        await manualCountry.trigger("input");
        if (submit.disabled || country.value !== "Haiti") {
          throw Error("manual country confirmation did not enable final submission");
        }
        await nodes["#review-form"].trigger("submit");
        if (finalUploads !== 1) throw Error("large CPF was not uploaded exactly once on final submission");

        cpf.files = [{name: "small.pdf", size: 2 * 1024 * 1024}];
        await cpf.trigger("change");
        if (detectorCalls !== 1 || country.value !== "Chad" || submit.disabled) {
          throw Error("small-file country detection behavior changed");
        }
        })();
        ''',
    )
    completed = subprocess.run(
        ["node", "-e", harness, str(JS.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
