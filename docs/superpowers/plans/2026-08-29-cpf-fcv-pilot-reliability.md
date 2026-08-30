# CPF FCV Pilot Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct verified evidence-coverage false negatives and align the assessment holding/results experience with the FCV Project Screener using the smallest repository-consistent changes.

**Architecture:** Keep the current extraction, evidence-pack, review, validation, and frontend lifecycle. Add bounded distributed PDF sampling and a computed package budget, pass only incomplete document roles into the existing validator/repair loop, strengthen the existing prompts, and restyle the existing progress journey rather than introducing a second implementation.

**Tech Stack:** Python 3.13, Flask, Pydantic, pypdf, pytest, vanilla JavaScript, HTML, CSS.

---

## File map

- Modify `src/cpf_fcv_reviewer/extraction.py`: select bounded PDF pages across the document and record explicit sampling warnings.
- Modify `src/cpf_fcv_reviewer/runtime.py`: raise optional PDF coverage, compute the package segment budget, and pass incomplete roles to validation.
- Modify `src/cpf_fcv_reviewer/validators.py`: reject `not_evidenced` when relevant uploaded-document coverage is incomplete.
- Modify `prompts/review.md` and `prompts/repair.md`: define coverage-aware absence language, scattered-content handling, FCV social-risk lenses, and advisory Strategy wording.
- Modify `src/cpf_fcv_reviewer/templates/index.html`, `static/app.js`, and `static/styles.css`: convert the existing progress view into the dedicated holding screen and apply focused result/status styling.
- Modify existing focused tests only; do not create a new framework, schema, dependency, or frontend component system.

### Task 1: Bounded document coverage

**Files:**
- Modify: `src/cpf_fcv_reviewer/extraction.py:49-86`
- Modify: `src/cpf_fcv_reviewer/runtime.py:99-193, 461-486, 624-646`
- Test: `tests/test_extraction.py`
- Test: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Add failing extraction and package-budget tests**

Add tests that construct a long PDF and assert that a capped extraction includes the first page, last page, evenly distributed interior pages, original page locators, and this warning shape:

```python
assert document.warnings[-1] == (
    "long-rra.pdf: sampled 12 of 40 PDF pages; "
    "conclusions about absence are limited."
)
assert document.segments[0].page == 1
assert document.segments[-1].page == 40
```

Extend the existing multi-document package test to assert three contributions per readable document when nine documents are supplied, subject to the ceiling:

```python
selected = _select_package_segments(documents)
counts = Counter(document.name for document, _, _ in selected)
assert set(counts.values()) == {3}
assert len(selected) == 27
assert len(selected) <= PACKAGE_MAX_SEGMENTS
```

- [ ] **Step 2: Run the focused tests and confirm the intended failures**

Run:

```powershell
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m pytest tests/test_extraction.py tests/test_runtime_wiring.py -q
```

Expected: new deep-page/warning and nine-document minimum assertions fail; established tests remain green.

- [ ] **Step 3: Implement deterministic page selection and package budgeting**

In `extraction.py`, select indices once and preserve their real page numbers:

```python
def _distributed_page_indices(page_count: int, limit: int | None) -> tuple[int, ...]:
    if limit is None or page_count <= limit:
        return tuple(range(page_count))
    if limit <= 1:
        return (0,)
    return tuple(
        dict.fromkeys(
            round(position * (page_count - 1) / (limit - 1))
            for position in range(limit)
        )
    )
```

Iterate `(page_index, reader.pages[page_index])`, use `page_index + 1` for locators, and append the filename-specific warning only when `len(indices) < page_count`.

In `runtime.py`, use these constants and one helper:

```python
OPTIONAL_PDF_SAMPLE_PAGES = 12
PACKAGE_BASE_SEGMENTS = 16
PACKAGE_MIN_SEGMENTS_PER_DOCUMENT = 3
PACKAGE_MAX_SEGMENTS = 32

def _package_segment_budget(documents: tuple) -> int:
    return min(
        PACKAGE_MAX_SEGMENTS,
        max(PACKAGE_BASE_SEGMENTS, len(documents) * PACKAGE_MIN_SEGMENTS_PER_DOCUMENT),
    )
```

Use `OPTIONAL_PDF_SAMPLE_PAGES` in `_extract_optional_uploads()` and use `_package_segment_budget(documents)` in both `_select_package_segments()` and `build_uploaded_evidence()`.

- [ ] **Step 4: Run focused tests and commit**

Run the command from Step 2. Expected: PASS.

```powershell
git add -- src/cpf_fcv_reviewer/extraction.py src/cpf_fcv_reviewer/runtime.py tests/test_extraction.py tests/test_runtime_wiring.py
git commit -m "fix: improve bounded document coverage"
```

### Task 2: Coverage-aware findings and FCV guidance

**Files:**
- Modify: `src/cpf_fcv_reviewer/runtime.py:788-809`
- Modify: `src/cpf_fcv_reviewer/validators.py:179-250`
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`
- Test: `tests/test_validators.py`
- Test: `tests/test_prompt_guardrails.py`
- Test: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Add failing validator, prompt, and runtime tests**

Add a validator test using an RRA or Strategy row with `AssessmentStatus.NOT_EVIDENCED`:

```python
issues = validate_review(
    reviewed,
    evidence_ids={"ev-1"},
    prohibited_terms=set(),
    incomplete_document_roles={DocumentRole.PACKAGE},
)
assert "incomplete_coverage_absence_claim" in {issue.code for issue in issues}
```

Assert the same result remains valid when `incomplete_document_roles=set()`, and assert runtime passes the derived set into `validate_review()`.

In `test_prompt_guardrails.py`, assert both prompts contain the exact concepts `scattered`, `not_assessable`, `Do No Harm`, `forced displacement`, `winners and losers`, `natural-resource competition`, and `not determinable at CPF level`.

- [ ] **Step 2: Run the focused tests and confirm they fail**

```powershell
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m pytest tests/test_validators.py tests/test_prompt_guardrails.py tests/test_runtime_wiring.py -q
```

Expected: failures identify the missing validator parameter, runtime wiring, and prompt language.

- [ ] **Step 3: Add the narrow absence guard and prompt rules**

Extend `validate_review()` with an optional immutable input:

```python
def validate_review(
    result: ReviewResult,
    *,
    evidence_ids: set[str],
    prohibited_terms: set[str],
    incomplete_document_roles: set[DocumentRole] | frozenset[DocumentRole] = frozenset(),
) -> tuple[ValidationIssue, ...]:
```

When optional package/context coverage is incomplete, add one repairable `incomplete_coverage_absence_claim` issue for each `not_evidenced` RRA or Strategy row. The message must instruct repair to `not_assessable`, or `partially_aligned` when the supplied evidence shows relevant but scattered content. Do not add a status or schema field.

Derive incomplete roles in runtime from the standardized extraction warning on documents already retained in context, then pass the set to the existing `validate_review()` call.

Add concise prompt rules:

```text
- Treat incomplete sampling as uncertainty, never as evidence of absence.
- When relevant content exists but is scattered or weakly operationalized, acknowledge it and use partially_aligned; recommend consolidation before new text.
- Consider conflict sensitivity and Do No Harm, inclusion and legitimacy, forced displacement and host communities, distributional perceptions of winners and losers, and natural-resource competition only where material and evidenced.
- Do not make an official classification or commitment judgment; use “not determinable at CPF level” when the evidence is insufficient.
```

Mirror the status-repair rule in `repair.md`.

- [ ] **Step 4: Run focused tests and commit**

Run the command from Step 2. Expected: PASS.

```powershell
git add -- src/cpf_fcv_reviewer/runtime.py src/cpf_fcv_reviewer/validators.py prompts/review.md prompts/repair.md tests/test_validators.py tests/test_prompt_guardrails.py tests/test_runtime_wiring.py
git commit -m "fix: qualify findings for incomplete evidence"
```

### Task 3: Screener-style holding screen and focused result polish

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html:85-116, 125-147`
- Modify: `src/cpf_fcv_reviewer/static/app.js:5-12, 207-239, 585-600`
- Modify: `src/cpf_fcv_reviewer/static/styles.css:98-157`
- Test: `tests/test_frontend_contract.py`
- Test: `tests/test_frontend_accessibility.py`
- Test: `tests/test_frontend_readability.py`

- [ ] **Step 1: Add failing holding-screen and semantic-style contracts**

Assert the progress template contains a dedicated holding container, compact timing block, connected stepper, ticker, guidance card, and keep-open note:

```python
for fragment in (
    'class="progress-shell"',
    'id="progress-track"',
    'id="progress-fill"',
    'class="progress-timing"',
    'id="guidance-card"',
    'class="progress-keep-open"',
):
    assert fragment in html
```

Assert JavaScript updates `progressFill.style.width` from the existing allowlisted stage mapping and does not read backend message payloads. Assert CSS includes connected stepper selectors, compact timer styles, reduced-motion rules for ticker/pulse/guidance, semantic status classes, and 390px wrapping.

- [ ] **Step 2: Run frontend tests and confirm they fail**

```powershell
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_frontend_readability.py -q
```

Expected: new structural/style assertions fail while current lifecycle tests pass.

- [ ] **Step 3: Refactor only the existing progress markup and state updates**

Wrap the existing progress elements in `.progress-shell`, keep all current IDs, and add:

```html
<div id="progress-track" class="progress-track" aria-hidden="true">
  <span id="progress-fill" class="progress-fill"></span>
</div>
<p class="progress-timing" aria-label="Review timing">
  <span id="elapsed-time">0:00 elapsed</span>
  <span aria-hidden="true">·</span>
  <span id="remaining-time">Estimating time remaining</span>
</p>
<p class="progress-keep-open">Keep this page open while the review is prepared.</p>
```

Set the fill from the already-sanitized stage group:

```javascript
const progressPercent = {documents: 18, research: 58, note: 88};
progressFill.style.width = `${progressPercent[group] || 0}%`;
```

Set it to `100%` on completion and `0%` in the existing reset path. Keep the current stage clock, rotating phrase interval, `aria-live="polite"` progress message, and `aria-live="off"` guidance. Do not add new backend events or timers.

- [ ] **Step 4: Apply the focused CSS changes**

Restyle the existing three stages as compact connected nodes/cards; use a slim navy/cyan progress track, small centered timing text, the current pulse/fade animations, and a static reduced-motion state. Add status modifiers through the existing badge builder:

```javascript
const badge = text(
  "span",
  assessmentStatusLabel(status),
  `assessment-status status-badge status-${status.replaceAll("_", "-")}`,
);
```

Use green/amber/muted-red/grey modifiers with text remaining primary. Give `.coverage-panel`, `.evidence-status-panel`, `.traceability-panel`, and `.evidence-group` the same bordered, rounded, lightly shaded disclosure treatment. Add only targeted wrapping and `min-width: 0` rules inside results/progress at 390px.

- [ ] **Step 5: Run frontend tests and commit**

Run the command from Step 2, then:

```powershell
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: frontend tests PASS; `node --check` PASS. If Node is unavailable, record that and rely on the browser/frontend contract tests.

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_frontend_readability.py
git commit -m "feat: align assessment holding experience"
```

### Task 4: Regression and country acceptance

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`
- Create: dated validation artifacts in the repository root only where existing project convention requires them; do not overwrite or commit source PDFs/provider output.

- [ ] **Step 1: Run focused regressions and the full suite once**

```powershell
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m pytest tests/test_extraction.py tests/test_runtime_wiring.py tests/test_validators.py tests/test_prompt_guardrails.py tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_frontend_readability.py -q
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m pytest -q
```

Expected: PASS, apart from any already documented Windows temporary-directory permission warnings.

- [ ] **Step 2: Run bounded reference checks**

Use the public Guinea CPF and RRA already supplied by the user. Confirm deep RRA pages contribute evidence for supported natural-resource, legitimacy, inclusion, jobs, and conflict findings. Re-run Haiti and confirm jobs/IFC/MIGA content is acknowledged as existing but scattered. Run Benin only as the package-coverage stress test unless real provider credentials are available; do not relabel smoke output as provider acceptance.

Save new dated JSON/HTML/DOCX and 1280px/390px screenshots without overwriting prior evidence. Visually inspect the holding and result screens at both widths, and render/inspect every DOCX page if a new DOCX is produced.

- [ ] **Step 3: Update status only from verified evidence**

Update `README.md` and `PROJECT_STATUS.md` with the tested commit, exact checks, Guinea/Haiti outcomes, and any remaining Benin/provider blocker. Verify the live `/health` release before changing deployment claims.

- [ ] **Step 4: Final checks and commit**

```powershell
git diff --check
& 'C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe' -m ruff check src tests
git status --short
git diff --cached
```

Expected: no whitespace errors; Ruff PASS if permitted by Windows Application Control; staged changes contain no user PDFs, credentials, raw provider responses, or unrelated untracked artifacts.

```powershell
git add -- README.md PROJECT_STATUS.md
git commit -m "docs: record pilot reliability validation"
git push -u origin fix/research-resilience-guided-journey
```
