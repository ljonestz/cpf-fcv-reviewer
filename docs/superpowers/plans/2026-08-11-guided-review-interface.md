# Guided Review Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a lay-user-friendly guided intake that transitions into a dedicated, evidence-linked results view without adding required inputs or coupling to the stable FCV Project Screener.

**Architecture:** Keep the existing Flask route and volatile-session architecture. Add validated evidence to the existing result response, divide the HTML into landing and review-workspace states, and centralize client-side state transitions in small JavaScript functions. Use semantic HTML, progressive disclosure, and the existing navy/cyan design tokens.

**Tech Stack:** Python 3.13, Flask, Pydantic, vanilla JavaScript, HTML/CSS, pytest, Ruff, in-app browser smoke testing.

---

### Task 1: Complete validated browser-result parity

**Files:**
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing route and renderer contract tests**

Add a route test that stores a valid result plus `evidence_by_id`, requests the result endpoint, and asserts that the response contains the validated locator heading and excerpt. Add frontend contract assertions for `<details>`, validated locator fields, practical options, priority responses, and limitations:

```python
def test_result_includes_validated_traceable_evidence_for_browser_expansion(
    make_valid_result,
):
    result, evidence = make_valid_result
    app = make_app()
    assessment_id = app.extensions["session_store"].create(
        {
            "status": "complete",
            "result": result.model_dump(mode="json"),
            "evidence_by_id": {
                key: item.model_dump(mode="json") for key, item in evidence.items()
            },
        }
    )
    payload = app.test_client().get(
        f"/api/reviews/{assessment_id}/result"
    ).get_json()
    assert payload["evidence_by_id"]["ev-1"]["locator"]["heading"]
    assert payload["evidence_by_id"]["ev-1"]["locator"]["excerpt"]
```

```python
def test_browser_renders_complete_progressively_disclosed_result():
    javascript = JS.read_text(encoding="utf-8")
    assert 'document.createElement("details")' in javascript
    assert "result.evidence_by_id" in javascript
    assert 'text("h2", "Practical options")' in javascript
    assert "result.priority_question_responses" in javascript
    assert 'text("h2", "Limitations")' in javascript
    assert "innerHTML" not in javascript
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_routes.py tests\test_frontend_contract.py -q -p no:cacheprovider --basetemp .pytest_guided_ui_red_1
```

Expected: failures because the result response lacks `evidence_by_id` and the browser lacks evidence and section renderers.

- [ ] **Step 3: Validate evidence before including it in the result response**

In `review_result`, validate every stored evidence item and return a stable 409 error for malformed evidence before merging the serialized mapping into the response:

```python
evidence_payload = state.payload.get("evidence_by_id", {})
if not isinstance(evidence_payload, dict):
    return jsonify(error="Traceable evidence is invalid."), 409
try:
    validated_evidence = {
        evidence_id: EvidenceItem.model_validate(item).model_dump(mode="json")
        for evidence_id, item in evidence_payload.items()
    }
except ValueError:
    return jsonify(error="Traceable evidence is invalid."), 409
response_payload = validated_result.model_dump(mode="json")
response_payload["evidence_by_id"] = validated_evidence
return jsonify(response_payload)
```

- [ ] **Step 4: Render complete result sections with evidence collapsed by default**

Add `renderEvidence(result, evidenceId)` using `document.createElement("details")`, a summary labelled with the evidence ID, and text-only locator/excerpt nodes. Extend `renderResult` to render practical options, priority responses when present, and limitations after findings. Continue using `textContent`; do not introduce `innerHTML`.

- [ ] **Step 5: Run focused tests and lint**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_routes.py tests\test_frontend_contract.py tests\test_end_to_end.py -q -p no:cacheprovider --basetemp .pytest_guided_ui_green_1
.\.venv\Scripts\python.exe -m ruff check --no-cache src\cpf_fcv_reviewer\routes.py tests\test_routes.py tests\test_frontend_contract.py tests\test_end_to_end.py
```

Expected: all focused tests pass and Ruff exits 0.

- [ ] **Step 6: Commit the parity checkpoint**

```powershell
git add -- src/cpf_fcv_reviewer/routes.py src/cpf_fcv_reviewer/static/app.js tests/test_routes.py tests/test_frontend_contract.py
git commit -m "feat: show traceable complete review results"
```

### Task 2: Build the guided landing view

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing semantic-intake tests**

Add assertions for a named landing region, three-step cue, explicit labels, required markers, volatile-storage helper text, one primary submit action, and one optional disclosure containing the supporting upload and guidance controls:

```python
def test_guided_landing_separates_essential_and_optional_inputs():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="landing-view"' in html
    assert 'aria-label="How the review works"' in html
    assert "1. Add the draft" in html
    assert "2. Add context" in html
    assert "3. Review options" in html
    assert '<label for="country">Country <span aria-hidden="true">*</span></label>' in html
    assert '<label for="review-stage">Review stage <span aria-hidden="true">*</span></label>' in html
    assert '<label for="cpf">CPF or CEN <span aria-hidden="true">*</span></label>' in html
    assert '<details id="optional-inputs">' in html
    assert "Supporting documents and specific questions (optional)" in html
    assert "held only for this session" in html
```

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py::test_guided_landing_separates_essential_and_optional_inputs -q
```

Expected: failure because the current form has no guided hierarchy or optional disclosure.

- [ ] **Step 3: Restructure only the intake markup**

Wrap the existing form in `<section id="landing-view">`. Add a plain-language purpose sentence and an ordered three-step cue. Keep `country`, `review-stage`, and `cpf` visible. Move `supporting`, `guidance`, and `priority-questions` into:

```html
<details id="optional-inputs">
  <summary>Supporting documents and specific questions (optional)</summary>
  <!-- existing supporting upload, guidance, and priority question controls -->
</details>
```

Use explicit `for` attributes for every label and retain the existing field IDs and names so route contracts do not change.

- [ ] **Step 4: Apply the restrained FCV visual system**

Retain the existing `--navy`, `--blue`, `--paper`, `--ink`, `--muted`, and `--rule` tokens. Add styles for `.steps`, `.form-card`, `.field-grid`, `.helper`, and `#optional-inputs`. Required additions:

```css
:focus-visible { outline: 3px solid var(--blue); outline-offset: 3px; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.field-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
@media (max-width: 680px) {
  .steps, .field-grid { grid-template-columns: 1fr; }
  header, main { width: min(100% - 24px, 980px); }
}
```

Do not add imagery, navigation menus, animation, or additional form controls.

- [ ] **Step 5: Run frontend tests and lint**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py tests\test_priority_question_intake.py tests\test_task13_frontend_contract.py -q
.\.venv\Scripts\python.exe -m ruff check --no-cache tests\test_frontend_contract.py
```

Expected: all tests pass and Ruff exits 0.

- [ ] **Step 6: Commit the guided intake**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py
git commit -m "feat: add guided review intake"
```

### Task 3: Add dedicated progress and results states

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Write failing state-transition tests**

Add contract assertions for a hidden `review-workspace`, state functions, dedicated result transition, recoverable failure action, and reset returning to intake:

```python
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
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py::test_interface_transitions_between_landing_progress_and_results -q
```

Expected: failure because the current landing form remains visible throughout the run.

- [ ] **Step 3: Group review-only markup into one workspace**

Move `progress`, `results`, `corrections`, and `actions` inside `<section id="review-workspace" hidden>`. Add a hidden `return-to-intake` button used only after a recoverable failure. Rename the reset button's visible label to **Start a new review** while retaining `id="reset-review"`.

- [ ] **Step 4: Centralize view transitions**

Add these functions and use them from submit, completion, failure recovery, and reset handlers:

```javascript
function showLanding() {
  landingView.hidden = false;
  reviewWorkspace.hidden = true;
}
function showProgress() {
  landingView.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = false;
  results.hidden = true;
  corrections.hidden = true;
  actions.hidden = true;
}
function showResults() {
  landingView.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = false;
  results.hidden = false;
  corrections.hidden = false;
  actions.hidden = false;
}
```

On `run_failed`, show the safe failure label and reveal `return-to-intake`. That button calls `showLanding` without persisting content. On reset, delete the volatile assessment, clear the form and result nodes, then call `showLanding`.

- [ ] **Step 5: Run UI and route regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py tests\test_task13_frontend_contract.py tests\test_routes.py tests\test_end_to_end.py -q -p no:cacheprovider --basetemp .pytest_guided_ui_green_3
```

Expected: all tests pass.

- [ ] **Step 6: Commit dedicated states**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_task13_frontend_contract.py
git commit -m "feat: separate review setup and results"
```

### Task 4: Verify usability, accessibility, and release safety

**Files:**
- Modify: `docs/validation/2026-08-10-mvp-validation.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the synthetic browser flow**

Start the synthetic-only local server and verify at desktop and a viewport no wider than 680px:

- the landing purpose and three steps are visible;
- only country, stage, and primary document are visible by default;
- optional inputs expand from one disclosure;
- run submission hides the intake and shows progress;
- completion shows the dedicated results view;
- evidence expands to a locator and excerpt;
- practical options and limitations are visible;
- correction rerun returns to results;
- Word export triggers a download;
- **Start a new review** purges state and restores the landing view; and
- browser console has no warnings or errors.

Expected: every item passes with the three synthetic language fixtures used only through automated tests and `synthetic_en.txt` used for the manual browser smoke.

- [ ] **Step 2: Document the final local boundary and validation result**

Update the README and CLAUDE operational sections from Task 15. Record the executed SHA, timestamp, test total, coverage, lint, secret scan, synthetic fixtures, browser checks, and known limitations in `docs/validation/2026-08-10-mvp-validation.md`. Do not include raw fixture content, model output, secrets, or correction text.

- [ ] **Step 3: Run complete release checks**

Run:

```powershell
$env:COVERAGE_FILE='C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\20260811_guided_ui_coverage'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_guided_ui_release --cov=cpf_fcv_reviewer --cov-report=term-missing --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check --no-cache src tests
rg -n --hidden -g '!*.docx' -g '!*.pdf' '(ANTHROPIC_API_KEY\s*=\s*[^$]|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-ant-|password\s*=)' .
git diff --check
git status --short
```

Expected: all tests pass, coverage is at least 90%, Ruff exits 0, the secret scan has no matches, and the diff contains only approved reviewer files.

- [ ] **Step 4: Commit the validated handoff**

```powershell
git add -- README.md CLAUDE.md docs/validation/2026-08-10-mvp-validation.md
git commit -m "docs: record MVP validation and safe-use boundary"
```

- [ ] **Step 5: Stop before deployment**

Report Task 15 complete and ask separately whether to begin Task 16. Do not create, configure, or submit a Render service until the user confirms at action time.
