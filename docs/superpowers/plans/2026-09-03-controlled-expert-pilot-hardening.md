# Controlled Expert Pilot Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app reliable enough for a controlled expert pilot by activating existing curated research recovery, making document-led fallback diagnosable, and ensuring priority recommendations visibly and proportionately connect to FCV.

**Architecture:** Reuse `CuratedResearchGateway`, `ResearchController`, `PriorityArea.why_it_matters`, the prompt files, validator, and summary renderer. Add no schema fields, dependencies, general news feed, scoring framework, or service layer. Tests remain provider-free until the existing external smoke runner is exercised after deployment.

**Tech Stack:** Python 3, Flask, Pydantic, pytest, vanilla JavaScript, existing Anthropic and institutional HTTP gateways.

---

## Task 1: Activate curated recovery and safe fallback reasons

**Files:**
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `src/cpf_fcv_reviewer/research_controller.py`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_research_controller.py`

- [x] Add a failing runtime-wiring test that replaces `BoundedInstitutionalClient` and `CuratedResearchGateway` with fakes, builds production services, and asserts that the created `ResearchController` receives a recovery gateway configured with `RELIEFWEB_APP_NAME`.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_runtime_wiring.py -q` and confirm the new assertion fails because `recovery_gateway` is currently `None`.
- [x] In `runtime.py`, import `BoundedInstitutionalClient` and `CuratedResearchGateway`, construct them only in the existing default-controller branch, and pass the gateway as `recovery_gateway`. Reuse `RESEARCH_ATTEMPT_TIMEOUT_SECONDS` for its timeout and `RELIEFWEB_APP_NAME` for attribution.
- [x] Add parameterized controller tests for document-led terminal reasons covering total-budget exhaustion, provider timeout/failure, rejected claims, and insufficient coverage. Assert only a stable allowlisted reason is emitted and `_assert_events_are_privacy_safe` still passes.
- [x] Implement one private reason-selection helper using existing state. Emit only `budget_exhausted`, `provider_timeout`, `provider_failure`, `source_rejected`, or `insufficient_coverage`; never emit exception messages, URLs, claims, or prompts.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py tests/test_runtime_wiring.py -q`.
- [x] Commit: `fix: activate curated research recovery`

## Task 2: Make FCV relevance and ordering part of the existing contract

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`
- Modify: `src/cpf_fcv_reviewer/validators.py`
- Modify: `tests/test_contracts.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `tests/test_validators.py`

- [x] Add failing contract/prompt tests requiring `why_it_matters` to explain a direct or indirect FCV causal link; priorities to be ordered by FCV materiality, evidence strength, then stage-appropriate actionability; indirect links to be explicit; and finalization actions not to introduce new binding commitments, conditionality, or institutional/delivery architecture.
- [x] Add a failing validator test where summary and priority IDs are identical and unique but differently ordered, expecting the existing repairable `unknown_priority_area` code.
- [x] Add failing finalization validator cases for imperative creation of a binding commitment, conditionality, or new institutional/delivery architecture, plus a negative descriptive case.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_prompt_guardrails.py tests/test_validators.py -q` and confirm failure.
- [x] Add a concise Pydantic `Field(description=...)` to existing `PriorityArea.why_it_matters`; add no field or machine score.
- [x] Tighten `review.md` so every selected priority states the evidenced direct or indirect FCV pathway, follows the approved ordering, and keeps finalization changes within existing commitments and architecture.
- [x] Mirror only repair-relevant wording in `repair.md`, including exact summary/priority order restoration and narrow finalization-overreach correction.
- [x] In `validate_review`, compare summary IDs with priority IDs and emit one `unknown_priority_area` issue when their order differs. Expand the existing finalization guard with a small regex or phrase tuple narrowly matching imperative creation of the prohibited commitments or architecture.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_prompt_guardrails.py tests/test_validators.py -q`.
- [x] Commit: `fix: require explicit FCV priority relevance`

## Task 3: Show FCV relevance on summary cards

**Files:**
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `tests/test_task13_frontend_contract.py`
- Modify: `tests/test_frontend_readability.py`

- [x] Add a failing frontend assertion that the summary card renders `FCV relevance` and the first sentence of `area.why_it_matters` before its response.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_task13_frontend_contract.py tests/test_frontend_readability.py -q` and confirm failure.
- [x] Add one `labelledNarrative` call in `renderRevisionSummary`, reusing `firstNarrativeSentence`; add no CSS or abstraction unless a focused test proves a layout defect.
- [x] Re-run the two focused frontend test files.
- [x] Commit: `fix: surface FCV relevance in summaries`

## Task 4: Verify the pilot gate and update current documentation

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Create only after meaningful release validation: `docs/validation/2026-09-03-controlled-expert-pilot-<commit>.md`

- [x] Run `.\.venv\Scripts\python.exe -m ruff check .` (attempted; unavailable because the worktree has no `.venv` and the configured Python 3.13 runtime has no Ruff module).
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py -q` (equivalent Python 3.13 command: 36 passed).
- [x] Run `.\.venv\Scripts\python.exe -m pytest -q` (equivalent Python 3.13 command with a non-OneDrive base temp directory: 1,237 passed).
- [x] Run `git diff --check`, inspect `git status --short`, and review the complete branch diff (whitespace check passed; generated browser output is ignored).
- [x] Run the existing external QA runner end to end against smoke mode, including file injection, result, assistant, refresh, and DOCX download. This is a hard gate before paid submission (passed with no console/page errors).
- [x] Update `docs/PROJECT_STATUS.md` with verified commits, checks, deployment state, limitations, and next action. Preserve the dated Guinea validation record.
- [x] Commit: `docs: record controlled pilot hardening`.
- [ ] Stop before push, deployment, or a paid Guinea run without explicit authorization. After authorized deployment, verify the exact commit is live with no-cost checks and permit at most one paid Guinea run for the fix cycle.

## Acceptance criteria

- [x] Default runtime supplies configured curated recovery to `ResearchController`.
- [x] Document-led runs expose one privacy-safe terminal reason distinguishing budget, timeout/provider, rejection, and insufficiency.
- [x] Priorities explain direct or indirect FCV pathways and follow the approved ordering.
- [x] Summary ordering is validator-enforced; finalization cannot introduce the prohibited commitments or architecture.
- [x] Summary cards visibly show the existing FCV rationale.
