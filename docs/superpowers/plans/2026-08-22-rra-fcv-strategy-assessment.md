# RRA and 2026–2030 FCV Strategy Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make full CPF reviews explicitly assess the RRA driver-to-response chain and the four 2026–2030 FCV Strategy shifts, while preventing incomplete document retrieval from becoming false-negative recommendations.

**Architecture:** Extend the existing immutable review contract with two evidence-linked assessment collections and concise recommendation titles. Improve package sampling inside the existing runtime, ground Strategy judgments in a versioned public registry bundle, and render the same canonical JSON through the existing browser and DOCX paths.

**Tech Stack:** Python 3.12+, Pydantic v2, Flask, python-docx, vanilla JavaScript/CSS, pytest.

---

## File map

- `src/cpf_fcv_reviewer/contracts.py`: add assessment enums/models and expose them on `ReviewDraft`/`ReviewResult`.
- `src/cpf_fcv_reviewer/runtime.py`: select first-page context plus high-value sections from every package document.
- `src/cpf_fcv_reviewer/validators.py`: validate assessment completeness, evidence references, Strategy grounding, and recommendation links.
- `src/cpf_fcv_reviewer/smoke.py`: emit deterministic structured assessments.
- `prompts/review.md` and `prompts/repair.md`: require and preserve the new structure and calibrated statuses.
- `registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.*`: versioned public FCV Strategy language and integrity hash.
- `src/cpf_fcv_reviewer/static/app.js` and `style.css`: render concise summaries plus accessible technical assessment rows.
- `src/cpf_fcv_reviewer/export_docx.py`: render the same briefing and technical layers in one DOCX.
- Existing focused test modules: update fixtures and add contract, retrieval, validation, prompt, frontend, export, smoke, and parity coverage.

## Task 1: Extend the canonical review contract

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py:35-330`
- Modify: `tests/conftest.py:1-85`
- Modify: `tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that construct one RRA row and all four Strategy rows, reject blank narrative fields, require a gap locus for `partially_aligned` and `not_evidenced`, and reject an empty evidence list except for `not_assessable`.

```python
def test_structured_assessments_round_trip(make_valid_result):
    result, _ = make_valid_result
    assert result.rra_driver_assessments[0].driver == "Unequal territorial access"
    assert {row.strategic_shift for row in result.fcv_strategy_assessments} == set(
        FCVStrategicShift
    )
    assert result.revision_summary[0].title == "Strengthen the territorial delivery chain"


def test_partially_aligned_assessment_requires_gap_locus():
    with pytest.raises(ValidationError, match="gap_locus"):
        RRADriverAssessment(
            assessment_id="rra-1",
            driver="Unequal territorial access",
            cpf_response="The CPF prioritizes lagging regions.",
            delivery_mechanism="Area-based delivery is proposed.",
            result_or_indicator="A service-access indicator is included.",
            remaining_gap="Adaptation triggers are not defined.",
            status=AssessmentStatus.PARTIALLY_ALIGNED,
            confidence=AssessmentConfidence.HIGH,
            evidence_ids=("context-001", "primary-001"),
        )
```

- [ ] **Step 2: Run the tests and confirm the contract is missing**

Run:

```powershell
$py = "$env:USERPROFILE\venvs\cpf-fcv-reviewer\Scripts\python.exe"
& $py -m pytest tests/test_contracts.py -q
```

Expected: failures importing the new models and reading `title`/assessment fields.

- [ ] **Step 3: Add the minimal enums and models**

Implement these exact public values in `contracts.py`:

```python
class AssessmentStatus(StrEnum):
    ALIGNED = "aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    NOT_EVIDENCED = "not_evidenced"
    NOT_ASSESSABLE = "not_assessable"


class AssessmentConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapLocus(StrEnum):
    CPF_NARRATIVE = "cpf_narrative"
    RESULTS_FRAMEWORK = "results_framework"
    DELIVERY_ARRANGEMENTS = "delivery_arrangements"
    MONITORING_ADAPTATION = "monitoring_adaptation"
    DOWNSTREAM_OPERATIONALIZATION = "downstream_operationalization"


class FCVStrategicShift(StrEnum):
    ANTICIPATE_BETTER = "anticipate_better"
    DIFFERENTIATED_APPROACH = "differentiated_approach"
    ONE_WBG_JOBS = "one_wbg_jobs"
    TOOLKIT_PARTNERSHIPS_STAFFING = "toolkit_partnerships_staffing"
```

Add `RRADriverAssessment` and `FCVStrategyAssessment` as frozen models with nonblank text validation, `status`, `confidence`, optional `gap_locus`, and `evidence_ids`. Use one model validator on each model: `partially_aligned` and `not_evidenced` require `gap_locus`; all statuses except `not_assessable` require at least one evidence ID.

Change `RevisionSummaryItem.action` to `RevisionSummaryItem.title` with `max_length=100`. Add `gap_locus: GapLocus` to `PriorityArea`. Add these fields to both `ReviewDraft` and `ReviewResult`:

```python
rra_driver_assessments: tuple[RRADriverAssessment, ...] = ()
fcv_strategy_assessments: tuple[FCVStrategyAssessment, ...]
```

Keep both assessment collections structurally valid but allow zero or incomplete rows at contract level so application validation can issue one bounded repair request. Do not require RRA rows at contract level because limited-framing mode legitimately has none.

- [ ] **Step 4: Update the shared valid fixture**

Give `make_valid_result` one RRA row, four Strategy rows, `RevisionSummaryItem(title=...)`, and `PriorityArea(gap_locus=GapLocus.CPF_NARRATIVE)`. Use existing `ev-1` for all affirmative fixture rows so downstream tests remain small.

- [ ] **Step 5: Run contract tests**

Run: `& $py -m pytest tests/test_contracts.py -q`

Expected: all contract tests pass.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py tests/conftest.py tests/test_contracts.py
git commit -m "feat: add structured RRA and strategy assessments"
```

## Task 2: Ground the four shifts in the full public Strategy

**Files:**
- Create: `registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json`
- Create: `registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.sha256`
- Create: `registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0_provenance.md`
- Modify: `registry_bundles/README.md`
- Modify: `tests/test_registry.py:14-215`
- Modify: `tests/fixtures/registry_bundle.synthetic.json`

- [ ] **Step 1: Write a failing registry test**

Point `PUBLIC_BUNDLE` at v1.1.0 and assert the existing four guardrails plus these IDs:

```python
assert tuple(entry.entry_id for entry in bundle.entries) == (
    "PUB-GUARD-001", "PUB-GUARD-002", "PUB-GUARD-003", "PUB-GUARD-004",
    "PUB-FCV-STRAT-001", "PUB-FCV-STRAT-002",
    "PUB-FCV-STRAT-003", "PUB-FCV-STRAT-004",
)
assert bundle.version == "1.1.0"
```

- [ ] **Step 2: Run the registry test and verify it fails**

Run: `& $py -m pytest tests/test_registry.py::test_checked_in_public_guardrail_bundle_is_valid_and_hash_pinned -q`

Expected: FAIL because the v1.1.0 files do not exist.

- [ ] **Step 3: Create the versioned bundle**

Copy the four existing guardrails unchanged and add four concise `approved_text` entries derived from the 76-page official Strategy:

```json
{
  "entry_id": "PUB-FCV-STRAT-001",
  "approved_text": "2026-2030 FCV Strategy shift - Anticipate better: country engagement should use forward-looking FCV risk analysis to support preparedness, proactive decisions, real-time program adjustment, and adaptive management. Source: World Bank Group, A World Bank Group Strategy for Engaging in Fragility, Conflict and Violence Affected Settings (2026-2030), pp. 21-25 and 53-54."
}
```

Use equivalent source-bounded text for: differentiated engagement (CPF outcomes address FCV drivers, trajectory-shifting actions, government commitment or sustainable delivery pathways, scenarios and calibration); One WBG jobs (explicit CPF jobs objectives, foundations/reforms/firm finance, MSMEs, gender lens, defined institutional roles); and toolkit/partnerships/staffing (RRA uptake, conflict sensitivity, operational flexibilities, delivery modalities and partnerships, with corporate staffing commitments not treated as automatic CPF gaps).

Record the official PDF URL and report number 211078 in the provenance file. Add matching synthetic entries to the smoke fixture, clearly marked synthetic.

- [ ] **Step 4: Generate and pin the bundle hash**

Run:

```powershell
$hash = (Get-FileHash 'registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json' -Algorithm SHA256).Hash.ToLowerInvariant()
$hash
```

Write exactly the printed 64-character value plus a newline to the `.sha256` file, then rerun the same command and compare it with `Get-Content`.

- [ ] **Step 5: Run registry tests**

Run: `& $py -m pytest tests/test_registry.py -q`

Expected: all registry tests pass and the production bundle is hash-pinned.

- [ ] **Step 6: Commit**

```powershell
git add -- registry_bundles tests/fixtures/registry_bundle.synthetic.json tests/test_registry.py
git commit -m "feat: ground reviews in the 2026 FCV strategy"
```

## Task 3: Fix multi-document package evidence coverage

**Files:**
- Modify: `src/cpf_fcv_reviewer/runtime.py:95-120,498-515`
- Modify: `tests/test_runtime_wiring.py:1220-1360`

- [ ] **Step 1: Add a failing deep-section retrieval test**

Create four package documents whose first segment is an introduction and whose later segments contain one of: `Results framework`, `Intervention logic`, `Implementation arrangements`, or `Adaptive management`. Run the existing runtime pipeline and assert every package document contributes both its introduction and its high-value segment.

```python
package_items = [
    item for item in captured["pack"].evidence
    if item.document_role is DocumentRole.PACKAGE
]
assert {item.locator.document_title for item in package_items} == {
    "results.txt", "implementation.txt", "monitoring.txt", "partnerships.txt"
}
for title in {item.locator.document_title for item in package_items}:
    selected_text = " ".join(
        item.text.casefold()
        for item in package_items
        if item.locator.document_title == title
    )
    assert any(marker in selected_text for marker in (
        "results framework", "implementation arrangements",
        "adaptive management", "partnerships",
    ))
```

- [ ] **Step 2: Run the test and confirm the current first-segment sampling fails**

Run: `& $py -m pytest tests/test_runtime_wiring.py -k "deep_section or role_budgets" -q`

Expected: the new test fails because later high-value sections are absent.

- [ ] **Step 3: Implement bounded package-aware selection**

Keep `_select_role_segments` for primary and context documents. Add a package-specific selector with:

```python
PACKAGE_SECTION_MARKERS = (
    "results framework", "results matrix", "intervention logic",
    "implementation arrangement", "delivery arrangement", "adaptive management",
    "risk monitoring", "partnership", "fragility", "conflict", "rra",
)
PACKAGE_MIN_SEGMENTS_PER_DOCUMENT = 3
PACKAGE_MAX_SEGMENTS = 16
```

For each package document, order candidates as: first segment, matching segments in original order, then remaining segments. Round-robin across documents until each receives up to three segments, then continue round-robin until `PACKAGE_MAX_SEGMENTS`. Deduplicate segments by original index. This keeps selection deterministic, bounded, and representative without semantic search or new dependencies.

Replace the fixed package budget of eight with this selector. Preserve primary=12 and context=4.

- [ ] **Step 4: Update the existing role-budget expectations**

For three saturated package documents, expect nine package items and a total of 25 uploaded-document evidence items. Keep the assertions that context retains four items and every document is represented.

- [ ] **Step 5: Run focused runtime tests**

Run: `& $py -m pytest tests/test_runtime_wiring.py -k "role_budgets or deep_section or evidence_truncation or three_upload_roles" -q`

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/runtime.py tests/test_runtime_wiring.py
git commit -m "fix: cover material sections in package evidence"
```

## Task 4: Enforce evidence-linked assessment behavior

**Files:**
- Modify: `src/cpf_fcv_reviewer/validators.py:1-260`
- Modify: `tests/test_validators.py`
- Modify: `tests/test_narrative_quality.py`

- [ ] **Step 1: Write failing validation tests**

Cover these cases: unknown evidence in either assessment collection; missing/duplicate Strategy shift; RRA-alignment mode with no RRA rows; a non-assessable row does not itself trigger a priority; summary titles remain under 100 characters and link uniquely to priority areas.

```python
def test_rra_alignment_requires_driver_assessment(make_valid_result):
    result, evidence = make_valid_result
    result = result.model_copy(update={
        "metadata": result.metadata.model_copy(update={"diagnostic_mode": DiagnosticMode.RRA_ALIGNMENT}),
        "rra_driver_assessments": (),
    })
    issues = validate_review(result, evidence_ids=set(evidence), prohibited_terms=set())
    assert "missing_rra_driver_assessment" in {issue.code for issue in issues}
```

- [ ] **Step 2: Run tests and verify failures**

Run: `& $py -m pytest tests/test_validators.py tests/test_narrative_quality.py -q`

Expected: new validation cases fail.

- [ ] **Step 3: Extend validation minimally**

Add issue codes `missing_rra_driver_assessment`, `incomplete_strategy_assessment`, and `unknown_assessment_evidence`. Include all assessment prose and `summary.title` in `result_text`. Reuse `_append_unknown_evidence_issue` for both row collections. Require all four Strategy shifts exactly once and at least one RRA row only when `diagnostic_mode` is `rra_alignment`.

For every Strategy row except `not_assessable`, require at least one evidence ID beginning `registry-PUB-FCV-STRAT-`. Do not require or infer corporate staffing evidence from the CPF. Leave materiality selection to the prompt; the existing priority-area evidence requirement prevents an unsupported `not_assessable` row from becoming a recommendation by itself.

- [ ] **Step 4: Update review-engine repairability**

Add the three new issue codes to `REPAIRABLE_ISSUE_CODES` in `src/cpf_fcv_reviewer/review_engine.py` and add a focused test in `tests/test_review_engine.py` showing the single repair pass receives them.

- [ ] **Step 5: Run focused validation and engine tests**

Run: `& $py -m pytest tests/test_validators.py tests/test_narrative_quality.py tests/test_review_engine.py -q`

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/validators.py src/cpf_fcv_reviewer/review_engine.py tests/test_validators.py tests/test_narrative_quality.py tests/test_review_engine.py
git commit -m "feat: validate evidence-linked FCV assessments"
```

## Task 5: Update review, repair, and deterministic smoke generation

**Files:**
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`
- Modify: `src/cpf_fcv_reviewer/smoke.py:130-205`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `tests/test_smoke_mode.py`

- [ ] **Step 1: Add failing prompt and smoke contract tests**

Assert the review prompt names all four strategic shifts, defines the four statuses, requires the RRA chain, distinguishes `not_evidenced` from `not_assessable`, prohibits recommendations based only on unavailable evidence, and requires short summary titles rather than drafting instructions. Assert repair preserves both assessment collections. Assert smoke output contains one RRA row in RRA mode, all four Strategy rows, and `revision_summary[0].title`.

- [ ] **Step 2: Run the tests and verify failures**

Run: `& $py -m pytest tests/test_prompt_guardrails.py tests/test_smoke_mode.py -q`

Expected: prompt fragments and smoke fields are missing.

- [ ] **Step 3: Revise `review.md` to version 3.0.0**

Keep the note-first structure. Insert a required evidence preflight and require:

```text
rra_driver_assessments: material RRA driver -> CPF response -> delivery mechanism -> result/indicator -> remaining gap.
fcv_strategy_assessments: exactly one row for each supplied 2026-2030 FCV Strategy shift.
Statuses: aligned, partially_aligned, not_evidenced, not_assessable.
Use not_assessable when necessary source coverage is unavailable; never convert it into a substantive gap or priority.
revision_summary.title: a concise issue label, not a sentence-count instruction, locator, or ready-to-paste edit.
```

Replace references to new-Strategy “pillars” with “strategic shifts.” Require `gap_locus` on material gaps and keep paragraph/section specificity in `PriorityArea.recommended_action` and `target_locator` only.

- [ ] **Step 4: Revise `repair.md` to version 3.0.0**

Require the complete new `ReviewDraft` schema and preservation of valid RRA rows, Strategy rows, statuses, confidence, loci, evidence IDs, summary titles, and priority links. Permit repair only for supplied validation issues.

- [ ] **Step 5: Update deterministic smoke output**

Import the new models/enums. Build one synthetic RRA row only when the payload metadata says `rra_alignment`; otherwise use an empty tuple. Always build four Strategy rows using the matching synthetic registry IDs plus the supplied primary/current evidence. Set the summary `title` and priority `gap_locus`.

- [ ] **Step 6: Run prompt and smoke tests**

Run: `& $py -m pytest tests/test_prompt_guardrails.py tests/test_smoke_mode.py -q`

Expected: all pass in provider-free mode.

- [ ] **Step 7: Commit**

```powershell
git add -- prompts/review.md prompts/repair.md src/cpf_fcv_reviewer/smoke.py tests/test_prompt_guardrails.py tests/test_smoke_mode.py
git commit -m "feat: generate structured RRA and strategy reviews"
```

## Task 6: Render the briefing and technical assessment in-browser

**Files:**
- Modify: `src/cpf_fcv_reviewer/static/app.js:470-610`
- Modify: `src/cpf_fcv_reviewer/static/style.css`
- Modify: `tests/test_frontend_contract.py:420-470`
- Modify: `tests/test_frontend_accessibility.py`
- Modify: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Add failing frontend contract tests**

Assert the summary links use `item.title`; the detailed tab includes `RRA driver-to-response assessment` and `2026-2030 FCV Strategy alignment`; every row exposes status and confidence text; and rendering continues to use DOM APIs without `innerHTML`.

- [ ] **Step 2: Run frontend tests and verify failures**

Run: `& $py -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py -q`

Expected: missing field and renderer assertions fail.

- [ ] **Step 3: Add compact accessible renderers**

Implement `renderRraAssessments(result)` and `renderStrategyAssessments(result)` using semantic `<section>`, `<h3>`, `<dl>`, `<dt>`, and `<dd>` elements. Display user-facing labels:

```javascript
const assessmentStatusLabels = {
  aligned: "Aligned",
  partially_aligned: "Partially aligned",
  not_evidenced: "Not evidenced",
  not_assessable: "Not assessable",
};
```

Show the chain fields for RRA rows and assessment/locus for Strategy rows. Reuse `renderEvidenceGroup` for evidence. In limited-framing mode, show “No current RRA was supplied; RRA alignment was not assessed.” Keep the summary to overall read, alignment synthesis, and 3–5 linked titles.

- [ ] **Step 4: Add minimal responsive styling**

Add classes for an assessment list/card, definition grid, and status badge. At `max-width: 760px`, collapse the definition grid to one column. Extend the existing reduced-motion rules only if new transitions are introduced; otherwise add none.

- [ ] **Step 5: Run frontend tests and JavaScript syntax check**

Run:

```powershell
& $py -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: tests pass and Node exits 0.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/style.css tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py
git commit -m "feat: show RRA and strategy assessments in results"
```

## Task 7: Render the same structure in the DOCX

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py:363-455`
- Modify: `tests/test_docx_export.py`
- Modify: `tests/test_output_parity.py`
- Modify: `tests/test_reproducibility_export.py`

- [ ] **Step 1: Add failing export and parity tests**

Assert the DOCX contains the RRA and Strategy headings, all four shift labels, row status/confidence/locus, the short summary title, detailed recommendation text, and human-readable evidence locators. Assert canonical JSON, browser contract, and DOCX use the same structured fields.

- [ ] **Step 2: Run export tests and verify failures**

Run: `& $py -m pytest tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py -q`

Expected: new headings and fields are absent.

- [ ] **Step 3: Add two compact technical sections**

After the alignment synthesis and before priority measures, add:

1. `RRA driver-to-response assessment` with one Heading 2 per driver and labelled paragraphs for CPF response, delivery, result/indicator, remaining gap, status, confidence, locus, and sources.
2. `2026-2030 FCV Strategy alignment` with one Heading 2 per strategic shift and labelled paragraphs for assessment, status, confidence, locus, and sources.

Use existing `locator_text` and `evidence_excerpt`; do not print raw evidence IDs. Use `item.title` in the numbered summary. Keep reproducibility metadata in the existing final section.

- [ ] **Step 4: Run export and parity tests**

Run: `& $py -m pytest tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/export_docx.py tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py
git commit -m "feat: export structured FCV assessments to DOCX"
```

## Task 8: Complete end-to-end regression and browser QA

**Files:**
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_adversarial_matrix.py`
- Modify: `docs/deployment/` release evidence file following the existing convention

- [ ] **Step 1: Add the deterministic multi-document regression**

Extend the end-to-end fixture to include a Results Matrix and implementation document. Assert their evidence appears in the pack, the result includes RRA and four-shift assessments, unavailable evidence is labelled `not_assessable`, and no summary title contains sentence-count instructions.

- [ ] **Step 2: Run focused end-to-end tests**

Run:

```powershell
& $py -m pytest tests/test_end_to_end.py tests/test_adversarial_matrix.py tests/test_routes.py -q
```

Expected: all pass.

- [ ] **Step 3: Run the full provider-free suite once**

Run:

```powershell
& $py -m pytest -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: all pytest tests pass; JavaScript syntax exits 0. If Windows temp-directory `WinError 5` recurs, rerun only the interrupted command with a new explicit pytest temp directory and record it as environmental. Do not recreate the virtual environment. Ruff remains optional because Windows Application Control may block it with `WinError 4551`.

- [ ] **Step 4: Start smoke mode and inspect both widths**

Use the existing project smoke-server command and the project Python environment. In browser QA at 1280px and 390px, verify:

- the summary shows only concise priority titles;
- RRA and all four Strategy rows are visible in Detailed analysis;
- statuses, confidence, loci, and evidence are readable;
- `Not assessable` is visually distinct and does not appear as a recommendation;
- the layout has no horizontal overflow;
- DOCX download returns a valid document. The separately reported current-tab navigation problem remains outside this approved assessment redesign.

- [ ] **Step 5: Record release evidence**

Add a dated deployment note under `docs/deployment/` containing the commit, exact checks, browser widths, smoke URL, and known environmental limitations. Do not include credentials or private document content.

- [ ] **Step 6: Commit the regression and release evidence**

```powershell
git add -- tests/test_end_to_end.py tests/test_adversarial_matrix.py docs/deployment
git commit -m "test: verify structured FCV review journey"
```

## Task 9: Publish and verify the production release

**Files:**
- Modify: the Task 8 deployment evidence note only if production verification adds release-specific facts

- [ ] **Step 1: Confirm the branch is release-ready**

Invoke `superpowers:verification-before-completion`, inspect `git status`, and confirm only intended commits differ from the PR base. Do not include the pre-existing `.pytest_*` artifacts.

- [ ] **Step 2: Push the existing feature branch and update PR #2**

Push `fix/research-resilience-guided-journey` and confirm PR #2 includes the structured assessment commits and passing checks. Use `superpowers:finishing-a-development-branch` for the handoff decision; do not merge without the user's direction.

- [ ] **Step 3: Point Render to the v1.1.0 registry bundle**

Using the applicable Render deployment/environment skill, set the existing service's `REGISTRY_BUNDLE_PATH` to `registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json` and `REGISTRY_BUNDLE_SHA256` to the exact checked-in v1.1.0 hash. Do not expose or alter provider credentials.

- [ ] **Step 4: Deploy and monitor the release**

Deploy the PR-approved branch or merged release according to the repository's existing Render workflow. Verify `/health` reports the new release and monitor startup logs for registry hash, schema, or prompt failures.

- [ ] **Step 5: Run production browser acceptance**

At 1280px and 390px, run an approved non-confidential test package and verify the RRA rows, four Strategy shifts, concise recommendation titles, evidence statuses, and valid DOCX content. Record only non-sensitive release evidence.

- [ ] **Step 6: Update release evidence if needed**

If production facts were not known at Task 8, append the deployed commit, Render release identifier, health result, and browser acceptance result to the existing deployment note and commit that documentation change separately.

## Final acceptance checklist

- [ ] Every uploaded package document contributes representative evidence, including high-value later sections.
- [ ] RRA-mode results contain at least one driver-to-response row.
- [ ] Every result contains exactly four Strategy-shift rows grounded in the versioned public Strategy entries.
- [ ] `Not evidenced` and `Not assessable` remain distinct in JSON, browser, and DOCX.
- [ ] Summary titles are concise issue labels; detailed actions retain justified drafting specificity.
- [ ] Only 3–5 material priorities are summarized, with no recommendation generated solely from unavailable evidence.
- [ ] Full, reduced, document-led, and deterministic smoke modes pass.
- [ ] Browser QA passes at 1280px and 390px, including DOCX export behavior.
