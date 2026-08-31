# Results, Persistent Assistant, and Full-RRA Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved priority-balanced results presentation, full-document RRA mapping, clearer current-research limitations, streamlined Word note, and a genuine 24-hour persistent follow-on assistant.

**Architecture:** Keep the existing Flask/vanilla-JavaScript application and structured review pipeline. Add one concise Strategy synthesis field, wire the existing diagnostic-map concept as a full-text pre-review model stage, and store bounded assistant turns in the existing session payload. No vector database, account layer, frontend framework, or stable Project Screener modification.

**Tech Stack:** Python 3.13, Flask, Pydantic, Anthropic SDK, SQLite/volatile session stores, vanilla JavaScript/CSS, python-docx, pytest.

---

## File map

- `src/cpf_fcv_reviewer/contracts.py`: Strategy synthesis and diagnostic-map response contract.
- `prompts/review.md`: concise readout and integrated RRA-response requirements.
- `prompts/diagnostic_map.md`: full-document page-accounting instructions.
- `prompts/follow_on.md`: bounded advisory assistant instructions.
- `src/cpf_fcv_reviewer/prompts.py`: register the follow-on prompt.
- `src/cpf_fcv_reviewer/runtime.py`: full diagnostic extraction, mapping, evidence-pack wiring, and assistant gateway registration.
- `src/cpf_fcv_reviewer/follow_on.py`: small streaming gateway and context builder.
- `src/cpf_fcv_reviewer/routes.py`: assistant history and streaming endpoints.
- `src/cpf_fcv_reviewer/static/app.js`: new readout hierarchy, compact cards, persistent assistant UI, and secondary correction action.
- `src/cpf_fcv_reviewer/static/styles.css`: existing-style prose panels, priority summaries, and conversation presentation.
- `src/cpf_fcv_reviewer/templates/index.html`: replace the primary correction section with the assistant shell while retaining correction as secondary UI.
- `src/cpf_fcv_reviewer/export_docx.py`: reader-facing export simplification.
- Existing focused test modules under `tests/`: TDD coverage; create `tests/test_follow_on.py` for the isolated gateway.
- `README.md`, `CLAUDE.md`, and `docs/PROJECT_STATUS.md`: final verified behavior and validation state.

## Task 1: Add the concise Strategy synthesis contract

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `prompts/review.md`
- Modify: `tests/test_review_engine.py`
- Modify: `tests/test_prompt_guardrails.py`

- [ ] **Step 1: Write failing contract and prompt tests**

Add `strategy_readout="The CPF advances prevention and jobs. Operational differentiation remains incomplete."` to the valid draft/result fixtures. Assert that blank synthesis is rejected and that `prompts/review.md` requires no more than two short paragraphs for both `alignment_readout` and `strategy_readout`.

```python
def test_review_draft_requires_strategy_readout(valid_review_draft_payload):
    valid_review_draft_payload["strategy_readout"] = " "
    with pytest.raises(ValidationError):
        ReviewDraft.model_validate(valid_review_draft_payload)


def test_review_prompt_bounds_both_readouts():
    prompt = load_prompt("review")
    assert "alignment_readout" in prompt
    assert "strategy_readout" in prompt
    assert "no more than two short paragraphs" in prompt
    assert "naturally incorporate the material delivery mechanism" in prompt
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_engine.py tests/test_prompt_guardrails.py -q
```

Expected: failures because `strategy_readout` is not yet defined or required.

- [ ] **Step 3: Add the minimal field and prompt rules**

Add the field to both `ReviewResult` and `ReviewDraft` and extend the existing nonblank validator:

```python
class ReviewResult(FrozenModel):
    metadata: RunMetadata
    overall_read: str
    alignment_readout: str
    strategy_readout: str
    # existing fields remain unchanged

    @field_validator("overall_read", "alignment_readout", "strategy_readout")
    @classmethod
    def requires_nonblank_readout(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review readout")
```

Mirror `strategy_readout: str` in `ReviewDraft`. In `prompts/review.md`, require both readouts to use no more than two short paragraphs. Require `cpf_response` to naturally incorporate material delivery and indicator content while still populating the structured fields.

- [ ] **Step 4: Run the focused tests**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py prompts/review.md tests/test_review_engine.py tests/test_prompt_guardrails.py
git commit -m "feat: add concise strategy readout"
```

## Task 2: Rebalance the HTML results without redesigning the shell

**Files:**
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_readability.py`
- Modify: `tests/test_task13_frontend_contract.py`
- Modify: `tests/test_frontend_accessibility.py`

- [ ] **Step 1: Write failing frontend assertions**

Extend the Node DOM harness result fixture with `strategy_readout`. Assert this text order in the summary panel: overall assessment, RRA panel, Strategy panel, priority measures. Assert that only priority items contain links, RRA rows omit delivery/result/gap-locus labels, Strategy rows omit gap locus, status/confidence share one row, and detailed output contains one `Basis and important limitations` disclosure.

```javascript
const summary = hooks.renderFiveMinuteReadout(result);
const summaryText = summary.textContent;
if (!(summaryText.indexOf("RRA prose") < summaryText.indexOf("Strategy prose") &&
      summaryText.indexOf("Strategy prose") < summaryText.indexOf("Priority measures"))) {
  throw Error("five-minute hierarchy is incorrect");
}
if (summaryText.includes("See the detailed RRA") || summaryText.includes("See the detailed FCV")) {
  throw Error("readout panels should not contain navigation links");
}
```

- [ ] **Step 2: Run the focused frontend tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_readability.py tests/test_task13_frontend_contract.py tests/test_frontend_accessibility.py -q
```

Expected: failures against the current summary order and detailed rows.

- [ ] **Step 3: Implement the smallest rendering changes**

In `app.js`:

- add `renderReadoutPanel(title, value, className)`;
- render `alignment_readout` and `strategy_readout` as prose panels before priorities;
- render each priority summary from `area.assessment` plus `area.recommended_action`, with the existing anchor behavior;
- render RRA definitions as Driver, CPF response, Remaining gap, Status and confidence;
- render Strategy definitions as Strategic shift, Assessment, Status and confidence;
- stop calling per-card traceability and top-level evidence-status/traceability renderers;
- append one collapsed plain-language basis/limitations block at the end.

Use one helper for combined status/confidence:

```javascript
function appendAssessmentStanding(definitions, status, confidence) {
  const value = document.createElement("dd");
  value.append(
    text("span", assessmentStatusLabel(status),
      `assessment-status status-badge status-${status.replaceAll("_", "-")}`),
    document.createTextNode(` Γò¼├┤Γö£ΓòóΓö¼Γò¥Γò¼├┤Γö£ΓûôΓö£Γòù ${assessmentValueLabel(confidence)} confidence`),
  );
  definitions.append(text("dt", "Status and confidence"), value);
}
```

Reuse existing variables, colors, shadows, breakpoints, and result-tab logic in `styles.css`; add only `.readout-panel`, `.readout-panel-rra`, `.readout-panel-strategy`, `.priority-summary-grid`, and assistant-related styles in Task 7.

- [ ] **Step 4: Run frontend tests and JavaScript syntax check**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_readability.py tests/test_task13_frontend_contract.py tests/test_frontend_accessibility.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_readability.py tests/test_task13_frontend_contract.py tests/test_frontend_accessibility.py
git commit -m "feat: rebalance CPF review results"
```

## Task 3: Simplify the Word note

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py`
- Modify: `tests/test_reproducibility_export.py`
- Modify: `tests/test_docx_export.py`
- Modify: `tests/test_output_parity.py`

- [ ] **Step 1: Write the failing export test**

Build a valid note, extract `word/document.xml`, and assert it contains Strategy synthesis, priority headings, `Status and confidence`, and the advisory caveat. Assert it omits `Evidence and reproducibility`, `Evidence and document locations`, `Coverage note`, `Current evidence tier`, `Gap locus`, `Delivery mechanism`, and `Result / indicator`.

```python
def test_docx_is_reader_facing(valid_result, evidence):
    data = build_docx(valid_result, evidence=evidence, hydrated_referrals=())
    with ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert valid_result.strategy_readout in xml
    assert "Status and confidence" in xml
    for excluded in ("Evidence and reproducibility", "Coverage note", "Gap locus"):
        assert excluded not in xml
```

- [ ] **Step 2: Run the export tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_reproducibility_export.py -q
```

Expected: failure because the current export contains the technical sections.

- [ ] **Step 3: Remove only the obsolete helper calls and consolidate rows**

Render `result.strategy_readout` once. In `_add_rra_assessments` output only Driver, CPF response, Remaining gap, and a combined standing string. In `_add_strategy_assessments` output only Strategic shift, Assessment, and combined standing. Remove the calls that add evidence status, coverage, and the evidence register; leave internal evidence validation intact.

```python
standing = (
    f"{ASSESSMENT_STATUS_LABELS[assessment.status]} Γò¼├┤Γö£ΓòóΓö¼Γò¥Γò¼├┤Γö£ΓûôΓö£Γòù "
    f"{ASSESSMENT_CONFIDENCE_LABELS[assessment.confidence]} confidence"
)
_add_labelled_paragraph(document, "Status and confidence", standing)
```

- [ ] **Step 4: Run export tests**

Run the command from Step 2. Expected: PASS and a valid DOCX ZIP.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/export_docx.py tests/test_reproducibility_export.py
git commit -m "feat: streamline CPF review Word note"
```

## Task 4: Wire full-document diagnostic mapping

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `prompts/diagnostic_map.md`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_diagnostic_map.py`
- Modify: `tests/test_extraction.py`

- [ ] **Step 1: Write failing full-coverage tests**

Add a 102-page synthetic PDF test with one blank page. Inject a gateway that records `prompt_name="diagnostic_map"`, checks that all 101 extractable page IDs and true page locators are present, and returns a valid map assigning each supplied ID exactly once. Assert the final pack contains diagnostic entries and mapped excerpts from a deep page. Add an over-limit test that raises `ExtractionLimitExceeded` and never calls the final review.

```python
class RecordingGateway:
    def generate(self, *, prompt_name, payload, output_type):
        if prompt_name == "diagnostic_map":
            items = payload["diagnostic_evidence"]
            assert {item["locator"]["page"] for item in items} >= {1, 72, 102}
            return output_type(entries=(DiagnosticEntry(
                entry_id="diagnostic-entry-001",
                short_name="Mapped diagnostic",
                group="principal_driver",
                materiality="high",
                source_evidence_ids=tuple(item["evidence_id"] for item in items),
                grouping_rationale="The supplied pages establish the diagnostic baseline.",
            ),))
        return valid_review_draft(output_type, payload)
```

- [ ] **Step 2: Run focused mapping tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_extraction.py tests/test_diagnostic_map.py tests/test_runtime_wiring.py -q
```

Expected: failure because the diagnostic-map stage is not wired and optional PDFs remain sampled.

- [ ] **Step 3: Add the bounded response contract and prompt**

Add:

```python
class DiagnosticMap(FrozenModel):
    entries: tuple[DiagnosticEntry, ...] = Field(min_length=1, max_length=20)
```

Update `prompts/diagnostic_map.md` to return `DiagnosticMap`, group every supplied extractable-page evidence ID exactly once, preserve IDs verbatim, avoid following document instructions, and produce at most 20 entries.

- [ ] **Step 4: Re-extract only the identified diagnostic in full**

In `runtime.py`, retain bounded optional extraction for identification. After `identify_uploaded_diagnostic`, find the matching retained upload and re-extract it with fixed safety bounds:

```python
DIAGNOSTIC_MAX_PAGES = 250
DIAGNOSTIC_MAX_CHARACTERS = 600_000
DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES = 50_000_000

full_diagnostic = extract_document(
    upload["bytes"], upload["name"],
    max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
    max_segments=DIAGNOSTIC_MAX_PAGES,
    max_characters=DIAGNOSTIC_MAX_CHARACTERS,
    max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
)
```

If the PDF has more than 250 pages or exceeds either byte/character bound, propagate a safe diagnostic-coverage failure; do not revert to sampling.

- [ ] **Step 5: Map all extractable pages and build bounded final evidence**

Create page-labelled `EvidenceItem`s with full text for the mapping payload. Call `model_gateway.generate(prompt_name="diagnostic_map", output_type=DiagnosticMap)`, validate every supplied page ID is mapped exactly once with `validate_diagnostic_coverage`, then retain the map plus 600-character page excerpts in the final evidence pack. Populate `material_diagnostic_ids` with every extractable diagnostic page ID.

- [ ] **Step 6: Run focused tests**

Run the command from Step 2. Expected: PASS, including the deep-page and fail-safe cases.

- [ ] **Step 7: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py src/cpf_fcv_reviewer/runtime.py prompts/diagnostic_map.md tests/test_runtime_wiring.py tests/test_diagnostic_map.py tests/test_extraction.py
git commit -m "feat: map complete uploaded RRA"
```

## Task 5: Clarify and target current-country research

**Files:**
- Modify: `src/cpf_fcv_reviewer/research_controller.py`
- Modify: `prompts/public_research.md`
- Modify: `tests/test_research_controller.py`
- Modify: `tests/test_public_research.py`

- [ ] **Step 1: Write failing wording and retry tests**

Assert that two recent claims from two URLs produce wording that says `Two recent claims from two institutional sources` rather than `Only 2 public sources`. Assert that a retry missing structural dynamics explicitly requests non-economic governance, conflict, institutional, or social evidence without requesting duplicate economic evidence.

- [ ] **Step 2: Run focused tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py tests/test_public_research.py -q
```

Expected: current wording calls claim count a source count.

- [ ] **Step 3: Implement the narrow wording and prompt change**

Count both recent claims and unique normalized URLs. Produce:

```python
return (
    f"{recent_count} recent claims from {source_count} institutional sources were "
    f"established; current-country coverage remains incomplete for {gaps}."
)
```

When `structural_dynamic` or `current_development` is missing, append a retry instruction to seek non-economic governance, conflict, institutional, security, social, or service-delivery evidence relevant to the named RRA. Keep the existing four-claim/two-publisher threshold and reduced route.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/research_controller.py prompts/public_research.md tests/test_research_controller.py tests/test_public_research.py
git commit -m "fix: clarify current research coverage"
```

## Task 6: Add the bounded persistent assistant backend

**Files:**
- Create: `src/cpf_fcv_reviewer/follow_on.py`
- Create: `prompts/follow_on.md`
- Create: `tests/test_follow_on.py`
- Modify: `src/cpf_fcv_reviewer/prompts.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_persistent_processing.py`

- [ ] **Step 1: Write failing gateway and route tests**

Cover: completed review required; expired review returns 410; empty or over-10,000-character request returns 400; history GET returns `[]`; two successful POSTs send prior turns to the gateway; only a completed streamed response is stored; history is capped at 20 messages; `assistant_active` returns 409; reset removes the history with the review.

Use an injected gateway:

```python
class StubFollowOnGateway:
    def __init__(self):
        self.calls = []

    def stream(self, *, review, evidence, history, message):
        self.calls.append((review, evidence, history, message))
        yield "Draft "
        yield "response"
```

- [ ] **Step 2: Run focused backend tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_follow_on.py tests/test_routes.py tests/test_persistent_processing.py -q
```

Expected: missing module and endpoints.

- [ ] **Step 3: Implement the small gateway**

Define a protocol and Anthropic implementation in `follow_on.py`:

```python
class FollowOnGateway(Protocol):
    def stream(
        self, *, review: dict, evidence: dict,
        history: tuple[dict[str, str], ...], message: str,
    ) -> Iterator[str]: ...
```

Construct Anthropic messages as one initial user context containing JSON for the validated review and evidence, followed by stored alternating turns and the new user message. Use `client.messages.stream`, a 4,000-token output cap, the configured model, and `load_prompt("follow_on")`. The prompt must preserve advisory/non-clearance boundaries and prohibit invented evidence or locators.

- [ ] **Step 4: Register the gateway and endpoints**

Register `follow_on` in `PROMPT_NAMES` and add `follow_on_gateway` to runtime services. Add:

- `GET /api/reviews/<assessment_id>/assistant`
- `POST /api/reviews/<assessment_id>/assistant`

The POST route validates the stored `ReviewResult` and evidence, sets `assistant_active=True`, streams SSE `chunk` events, then stores only the completed user and assistant messages and clears the flag in `finally`. Bound with:

```python
ASSISTANT_MESSAGE_MAX_LENGTH = 10_000
ASSISTANT_HISTORY_MAX_MESSAGES = 20
history = [*history, {"role": "user", "content": message},
           {"role": "assistant", "content": completed}][-ASSISTANT_HISTORY_MAX_MESSAGES:]
```

Return a safe inline error event on provider failure without changing the completed review.

- [ ] **Step 5: Run focused backend tests**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/follow_on.py prompts/follow_on.md src/cpf_fcv_reviewer/prompts.py src/cpf_fcv_reviewer/runtime.py src/cpf_fcv_reviewer/routes.py tests/test_follow_on.py tests/test_routes.py tests/test_persistent_processing.py
git commit -m "feat: add persistent follow-on assistant"
```

## Task 7: Replace the primary correction box with the assistant UI

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_frontend_download.py`
- Modify: `tests/test_frontend_accessibility.py`

- [ ] **Step 1: Write failing DOM-contract tests**

Require the heading `What would you like to do next?`, four suggestion buttons, conversation region with `aria-live="polite"`, assistant textarea, Send button, and secondary `Correct source information and rerun` control. Assert suggestions only prefill text. In the Node harness, mock history GET and a two-chunk POST stream, then assert restored and new messages render in order and Send is disabled during streaming.

- [ ] **Step 2: Run frontend tests and confirm failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_download.py tests/test_frontend_accessibility.py -q
```

Expected: missing assistant DOM and behavior.

- [ ] **Step 3: Implement the assistant shell and behavior**

Replace the visible correction section with the assistant card and keep the existing correction controls in a secondary collapsed block. Add `loadAssistantHistory`, `prefillAssistant`, `sendAssistantMessage`, and `renderAssistantMessage` to `app.js`. Call history loading after `assessmentId` and the completed result are available. Parse the route's SSE chunks using the same bounded incremental pattern already used for assessment events.

Suggested prompts must be editable and must not send until the user clicks Send. Use the approved labels exactly.

- [ ] **Step 4: Add restrained responsive styles**

Reuse existing card, button, input, muted text, and focus styles. Add only assistant transcript/message/chip selectors; at mobile width, stack the input and Send button and preserve no-horizontal-overflow behavior.

- [ ] **Step 5: Run frontend tests and syntax check**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_download.py tests/test_frontend_accessibility.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_frontend_download.py tests/test_frontend_accessibility.py
git commit -m "feat: add follow-on review workspace"
```

## Task 8: Integrated provider-free verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md` only if commands/protocol or architecture facts changed
- Modify: `docs/PROJECT_STATUS.md`
- Create: `docs/validation/2026-09-01-results-assistant-rra-coverage-validation.md`

- [ ] **Step 1: Run the narrow combined suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_engine.py tests/test_prompt_guardrails.py tests/test_frontend_readability.py tests/test_task13_frontend_contract.py tests/test_reproducibility_export.py tests/test_extraction.py tests/test_diagnostic_map.py tests/test_runtime_wiring.py tests/test_research_controller.py tests/test_public_research.py tests/test_follow_on.py tests/test_routes.py tests/test_persistent_processing.py -q
```

Expected: PASS.

- [ ] **Step 2: Run provider-free smoke and static checks**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py -q
.\.venv\Scripts\python.exe -m compileall -q src tests
node --check src/cpf_fcv_reviewer/static/app.js
git diff --check
```

Expected: PASS. Run Ruff only if the repository virtual environment contains it; record an unavailable executable as an environment limitation rather than a pass.

- [ ] **Step 3: Run the full provider-free suite once**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass with no external model calls.

- [ ] **Step 4: Perform local smoke-browser QA**

Use the explicit smoke application. Verify desktop and mobile summary hierarchy, priority links, detailed-card consolidation, basis disclosure, assistant history restoration with the stub gateway, correction secondary action, and DOCX download. Save screenshots clearly labelled `smoke`; do not present them as Guinea quality output.

- [ ] **Step 5: Update current documentation**

Update README and Project Status with verified behavior and exact test counts. Record commands, outcomes, screenshot paths, and remaining deployment/quality requirements in the new validation note. Do not rewrite historical validation records or commit raw model output, uploaded documents, conversations, or live assessment IDs.

- [ ] **Step 6: Commit and push the verified implementation branch**

```powershell
git add -- README.md CLAUDE.md docs/PROJECT_STATUS.md docs/validation/2026-09-01-results-assistant-rra-coverage-validation.md
git commit -m "docs: validate results and assistant redesign"
git status --short
git push origin HEAD
```

Expected: clean branch synchronized with origin.

## Task 9: Deploy and run one Guinea quality assessment

**Files:**
- Append a new deployment/quality section to `docs/validation/2026-09-01-results-assistant-rra-coverage-validation.md`
- Update: `README.md`
- Update: `docs/PROJECT_STATUS.md`

- [ ] **Step 1: Deploy the exact verified commit**

Follow the repository's existing Render deployment path. Confirm Render reports the exact Git commit live, `/health` returns `ok`, and the public intake page returns HTTP 200 before submitting documents.

- [ ] **Step 2: Run one authorized Guinea production-quality review**

Use the public Guinea CPF and RRA. Keep the free Render service awake only during the active run, using a separate page approximately every four to five minutes. Do not start another paid run on unchanged code.

- [ ] **Step 3: Verify the complete result**

Confirm:

- all 102 RRA pages were attempted and every extractable page was accounted for by the diagnostic map;
- deep-page evidence survives into the final RRA assessment;
- the Five-minute readout follows the approved order and prose limits;
- priority links focus the correct detailed recommendations;
- detailed rows and DOCX omit the removed technical fields;
- two assistant requests preserve context, and the conversation restores after refresh; and
- result, evidence, reproducibility, and application validation pass.

- [ ] **Step 4: Capture required artifacts**

Save unique full-page PNGs for intake, holding, summary, detailed analysis, first assistant response, restored conversation after refresh, and any failure state. Save the DOCX and inspect its ZIP structure and rendered pages if a Word renderer is available. Record only safe validation codes and artifact paths in the validation note.

- [ ] **Step 5: Update, commit, and push the validation record**

```powershell
git add -- README.md docs/PROJECT_STATUS.md docs/validation/2026-09-01-results-assistant-rra-coverage-validation.md
git commit -m "docs: record Guinea results assistant quality run"
git push origin HEAD
```

Expected: documentation distinguishes provider-free smoke from the single paid Guinea quality run and identifies the exact deployed commit.
