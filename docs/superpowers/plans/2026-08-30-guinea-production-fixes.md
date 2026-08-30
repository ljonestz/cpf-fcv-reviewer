# Guinea Production Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the production defects exposed by the Guinea finalization run with narrow, regression-tested changes.

**Architecture:** Preserve the existing review pipeline. Add deterministic validation at its current validation boundary, remove an unused registry lookup from DOCX export, and correct two small presentation strings at their sources.

**Tech Stack:** Python 3.13, Flask, Pydantic, pytest, vanilla JavaScript.

---

### Task 1: Correct limitation and timer copy

**Files:**
- Modify: `tests/test_research_controller.py`
- Modify: `tests/test_frontend_contract.py`
- Modify: `src/cpf_fcv_reviewer/research_controller.py`
- Modify: `src/cpf_fcv_reviewer/static/app.js`

- [ ] Add an exact regression assertion that three recent sources produce `Only 3 public sources were established recently`.
- [ ] Add a frontend contract assertion for a helper that formats `1-1` as `About 1 minute remaining` and keeps non-equal bounds as a range.
- [ ] Run the two focused tests and confirm they fail for the observed wording.
- [ ] Change `_reduced_limitation` to select `was` only for one source and `were` otherwise.
- [ ] Add the smallest estimate formatter in `app.js` and call it from `updateJourneyClock`.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Enforce narrative and registry guardrails

**Files:**
- Modify: `tests/test_validators.py`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `src/cpf_fcv_reviewer/validators.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`

- [ ] Add failing validator tests for a supplied evidence ID embedded in narrative and for `Guinea is not on the FCV list`.
- [ ] Add a failing runtime test showing an unknown `institutional_referral_ids` value becomes a repair issue.
- [ ] Add prompt-contract assertions requiring structured evidence references, no raw IDs in prose, no country FCV-list classification, and calibrated trend claims.
- [ ] Run the focused tests and confirm each fails for its intended missing guardrail.
- [ ] Add two validation issue codes and minimal checks in `validate_review`; pass the registry entry-ID set from the existing runtime bundle.
- [ ] Update only the relevant review and repair prompt sentences.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Make DOCX export independent of unused referrals

**Files:**
- Modify: `tests/test_docx_export.py`
- Modify: `src/cpf_fcv_reviewer/routes.py`

- [ ] Add a failing route regression test whose completed result contains unknown institutional referral IDs but otherwise valid evidence and assert that DOCX export returns a valid ZIP response.
- [ ] Run the focused route test and confirm the current hydration lookup causes failure.
- [ ] Pass an empty referral tuple to `build_docx` because the builder explicitly discards that argument; add `current_app.logger.exception` to the existing unexpected-error branch.
- [ ] Re-run the focused route test and confirm it passes.

### Task 4: Verify, review, and deploy

**Files:**
- Review all modified files; no additional production files expected.

- [ ] Run all focused regression tests.
- [ ] Run `C:\WBG\Python313\python.exe -m ruff check .`.
- [ ] Run `C:\WBG\Python313\python.exe -m pytest -q` and require zero failures.
- [ ] Inspect `git diff --check` and the full diff for unrelated complexity.
- [ ] Commit and push `fix/guinea-production-fixes`.
- [ ] Deploy the branch commit through Render MCP, confirm the deploy is live, and verify the existing Guinea assessment exports a valid DOCX.
- [ ] Run a fresh Guinea review and confirm corrected visible wording and absence of raw evidence IDs or official-list classification.
