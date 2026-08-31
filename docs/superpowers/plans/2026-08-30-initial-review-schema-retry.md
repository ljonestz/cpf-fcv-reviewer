# Initial Review Schema Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover once from an initial `ReviewDraft` Pydantic validation failure without restarting research or weakening fail-closed safeguards.

**Architecture:** `ReviewEngine.review()` will retain its existing payload and make one second gateway call only after `pydantic.ValidationError`. A small local helper will serialize only error `loc` and `type`; the existing review prompt will explain the bounded retry payload.

**Tech Stack:** Python 3.13, Pydantic 2, pytest, existing model gateway and prompt loader.

---

### Task 1: Add the bounded initial-review retry

**Files:**
- Modify: `tests/test_review_engine.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `src/cpf_fcv_reviewer/review_engine.py`
- Modify: `prompts/review.md`

- [ ] **Step 1: Write the failing review-engine tests**

Import `ValidationError`, add a scripted gateway that raises supplied outcomes in order,
and add tests proving: first validation failure retries once and succeeds; `schema_retry`
contains only `loc` and `type`; a second validation failure propagates after two calls;
and a non-validation exception is not retried.

```python
error = ValidationError.from_exception_data(
    "ReviewDraft",
    [{"type": "missing", "loc": ("priority_areas", 0, "gap_locus"), "input": {"secret": "omit"}}],
)
gateway = ScriptedGateway((error, draft_for(meta)))
result = ReviewEngine(gateway).review(evidence_pack(meta))
assert result.overall_read
assert gateway.calls[1][1]["schema_retry"] == {
    "issues": [{"loc": ["priority_areas", 0, "gap_locus"], "type": "missing"}]
}
```

- [ ] **Step 2: Run the tests and verify RED**

Run:
`python -m pytest tests/test_review_engine.py -k "schema_retry or validation_error" -q`

Expected: failures because current `ReviewEngine.review()` propagates the first
`ValidationError` and never creates `schema_retry`.

- [ ] **Step 3: Add the prompt contract test and verify RED**

Add an assertion that the review prompt recognizes `schema_retry`, corrects only the
listed schema locations/types, returns a complete `ReviewDraft`, and does not echo the
diagnostics into user-facing content.

Run:
`python -m pytest tests/test_prompt_guardrails.py -k schema_retry -q`

Expected: failure because the current prompt does not mention `schema_retry`.

- [ ] **Step 4: Implement the minimal retry**

In `review_engine.py`, import `ValidationError`, add a private serializer using
`errors(include_url=False, include_context=False, include_input=False)`, and wrap only
the initial review gateway call:

```python
try:
    draft = self.gateway.generate(**request)
except ValidationError as exc:
    retry_payload = {
        **payload,
        "schema_retry": {"issues": _safe_schema_issues(exc)},
    }
    draft = self.gateway.generate(
        prompt_name="review",
        payload=retry_payload,
        output_type=ReviewDraft,
    )
```

Update `prompts/review.md` with the corresponding narrow second-attempt instruction.
Do not add loops, retry configuration, schema relaxation, or unrelated refactoring.

- [ ] **Step 5: Verify GREEN**

Run:
`python -m pytest tests/test_review_engine.py tests/test_prompt_guardrails.py -q`

Expected: all focused tests pass.

- [ ] **Step 6: Commit the implementation**

```powershell
git add -- src/cpf_fcv_reviewer/review_engine.py prompts/review.md tests/test_review_engine.py tests/test_prompt_guardrails.py
git commit -m "fix: retry invalid initial review schema once"
```

### Task 2: Complete provider-free verification and documentation

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Create: `docs/validation/2026-08-30-initial-review-schema-retry-validation.md`

- [ ] **Step 1: Run complete no-cost verification**

Run focused tests, `tests/test_smoke_mode.py`, the complete pytest suite, Python
compilation, Ruff when available, and `git diff --check`. No command may call a provider.

- [ ] **Step 2: Review the diff and safety boundary**

Confirm one retry maximum, only `ValidationError` triggers it, retry diagnostics contain
no `msg`, `input`, `ctx`, raw output, or assessment identifiers, and second failure remains
fail-closed.

- [ ] **Step 3: Update active documentation and add validation evidence**

Record the implementation commit, exact test counts, deployment status, the fact that no
paid run was performed, and the remaining requirement for a separately authorized Guinea
acceptance run after deployment.

- [ ] **Step 4: Commit and push**

```powershell
git add -- docs/PROJECT_STATUS.md docs/validation/2026-08-30-initial-review-schema-retry-validation.md
git commit -m "docs: record schema retry verification"
git push origin HEAD:refs/heads/fix/guinea-production-fixes
```
