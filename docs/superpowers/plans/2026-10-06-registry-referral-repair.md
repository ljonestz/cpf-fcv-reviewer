# Registry Referral Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Complete mechanical referral correction using the approved registry.

**Architecture:** Runtime supplies the same trusted registry IDs used by validation.
The review engine filters original referrals only for the named repair issue and
preserves all other repair behavior. No new service, dependency or model call.

**Tech Stack:** Python, Pydantic, pytest; existing Render service.

## Task 1: Reproduce before implementation

Files: create `tests/test_registry_referral_repair.py`; extend `tests/test_runtime_wiring.py`.

- [ ] Test that a model retaining an unknown reference or dropping an approved original
  cannot determine the repaired reference tuple. Use a synthetic fixture with safe
  original strategy evidence. For both diagnostic modes expect original approved IDs
  in original order, with all other content unchanged and one existing repair call.
- [ ] Test model-added approved/unknown IDs, absent/empty allowlist, issue gating and
  that unrelated prohibited-language validation still fails.
- [ ] Run `python -m pytest tests/test_registry_referral_repair.py -q` and confirm
  expected failures before modifying source.

## Task 2: Minimal correction

Files: `src/cpf_fcv_reviewer/review_engine.py`, `src/cpf_fcv_reviewer/runtime.py`.

- [ ] Add optional keyword `registry_entry_ids: set[str] | None = None` to repair.
- [ ] After issue-specific normalization and before result assembly, apply:

```python
if "unknown_institutional_referral" in issue_codes and registry_entry_ids is not None:
    draft = draft.model_copy(update={
        "institutional_referral_ids": tuple(
            entry_id for entry_id in result.institutional_referral_ids
            if entry_id in registry_entry_ids
        ),
    })
```

- [ ] Pass `registry_entry_ids=registry_entry_ids` from runtime's existing repair closure.
- [ ] Run focused tests, review engine/runtime/validators tests, Ruff on changed files,
  `git diff --check`, and the full provider-free suite (Windows Gunicorn skip disclosed).

## Task 3: Acceptance and handoff

- [ ] Run 38 smoke tests and existing synthetic browser checks for the candidate.
- [ ] Get independent focused review of the diff before merge.
- [ ] Update validation/status with exact checks, safe failure history and limits.
- [ ] Commit/push the feature branch, create a substantive PR, and confirm Linux CI.
- [ ] Follow existing deployment authorization; verify the exact live release before
  requesting approval for another paid CPF plus RRA trial.
