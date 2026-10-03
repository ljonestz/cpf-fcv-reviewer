# Guinea paid acceptance after quotation repair - 2026-10-01

The owner authorized one assessment on the repaired candidate. Guinea on exact
commit `c272e7923ad4479f89e68f88a18f26c409ed9bbc` failed safely: one
`target_locator_mismatch` remained after bounded repair. No findings were released.
Paid testing stopped; no replacement assessment or real assistant request followed.
No deployment, merge or hosting change occurred. Production acceptance remains open.

## Method and frozen scope

Application source is the quotation-identity repair `b5f0578`; `c272e79` adds its CI
record only. Exact-head Linux CI was successful before submission. The target imports
and release were pinned, with the approved registry v1.1.0 and existing persistent
SQLite store. The four-per-UTC-day and two-per-client-hour admission limits remained
active. The existing five paid reservations were preserved, and one new reservation
was made before submission. The ledger now contains six. Read-only database inspection
confirmed global counts of four on 30 September and two on 1 October; no reset occurred.

The same three public Guinea PDFs, Decision Review stage and unsteered guidance were
used. Their hashes matched the
[previously frozen input set and acceptance criteria](2026-10-01-provider-free-release-gates.md)
before and after this assessment. A new ignored frozen record captured the exact
candidate, runner/source hashes, prior-ledger hash and one-assessment stop rule before
the paid submission.

The exact browser runner first passed all 11 synthetic smoke checks with normal exit 0,
including programmatic upload, synthetic assistant formatting, refresh restoration,
desktop/mobile views and both Word downloads. It made no provider calls. The quality
runner omitted the assistant option and admitted only this label, country, candidate
and sixth ledger reservation; repeating it after reservation is blocked.

## Paid outcome

Submission occurred at 10:41:38 UTC. The runner finished normally with exit 1 after
788.53 seconds overall, approximately 12 minutes 45 seconds after submission. Extraction,
source resolution, current research, evidence construction, diagnostic mapping and
review generation completed. Initial validation reported two fatal issues:

| Phase | Blocking codes | Safe locator aggregate |
| --- | --- | --- |
| Initial validation | `target_locator_mismatch`, `prohibited_policy_language` | `coordinate_not_cited`: 1 |
| After bounded repair | `target_locator_mismatch` | `coordinate_not_cited`: 1 |
| Final application outcome | `review_failed` | No findings released |

Four advisory issues had the codes `stage_length_overreach` and
`missing_current_context_support`. No `unsupported_cpf_response` code appeared in the
reported initial or final blocking sets. This does not establish that the previous
paid failure was caused by the repaired row-identity defect, or that this draft was
factually correct. The policy-language issue cleared; target grounding did not.

`coordinate_not_cited` means that no cited primary/package record supported the stated
source location and specified version. It does not reveal whether the underlying
problem was a page/element/heading, version, citation selection, ambiguous passage or
repair-identity problem. Rejected targets, validation messages, draft findings and
model output were not retrieved or saved. No accepted result, Word exports or real
assistant response exists, so the factual and analytical acceptance criteria cannot
be graded from this case.

All four paid screenshots were inspected. The failure screen says that no findings
were released and another submission uses another allowance. Browser JavaScript,
console and resource error counts were zero. The process completed without a cleanup
hang; no application-source change was made during or after the run.

## Provider-free follow-up

Read the locator classification, cited-only resolution and priority-repair merge paths.
Safe reason/count diagnostics were retrieved through a filtered read-only helper; its
synthetic checks reject unknown reasons, invalid counts and extra content fields.
Ten relevant existing engine/validator tests passed after the failure.

Four new controls used actual public Guinea physical pages 3, 5 and 7, with the target
module import guarded. All passed:

| Control | Observed behavior |
| --- | --- |
| Unique cited passage with a wrong coordinate | Copied its actual source coordinate and passed |
| Passage present only in an uncited source page | Retained the unsupported target and blocked it |
| Actual repeated land-tenure passage on two cited pages with an invalid coordinate | Remained ambiguous and blocked |
| The same repeated passage with a valid cited coordinate | Kept the selected page and passed |

These controls establish resolver behavior, not the content or precise cause of the
rejected assessment. No reproducible resolver defect was found in this follow-up,
so no speculative code change, relaxed source check, retry increase or further paid
call was made. Reliable target selection and repair remain a production blocker.

The independent source read also found inconsistent Human Capital Index figures:
0.38 in the overview (physical page 6) and 0.35 in the results framework (physical
page 3). This is an input inconsistency, not a finding from the rejected review; a
future accepted assessment must qualify it if it uses that statistic.

## Saved evidence and remaining gates

New ignored artifacts remain under
`output/playwright/20260930_renewed_acceptance/`:

- `20261001_quotation_fix_frozen_criteria.json` and the uniquely named runner copies.
- `browser/synthetic-quotation-fix-preflight-01/`: nine screenshots, synthetic validated
  JSON, QA status and two Word downloads. Representative summary/detail/mobile and
  assistant screenshots were inspected.
- `runs/quality-10-guinea-quotation-fix/`: four inspected screenshots, health and QA
  status, safe event and locator diagnostics, public control script/JSON, artifact
  hashes and read-only quota verification. Private identifiers remain in OS temp storage.

The first inventory's quota query used the wrong scope filter and returned no rows.
It is preserved; `20261001_quota_verification.json` uses the application-owned
`review_day`/global key and records the verified four-plus-two counts. This was a QA
query correction, not an application defect or state reset.

Next engineering work should review the target-selection contract with provider-free
fixtures before any further paid acceptance. Fresh factual/model acceptance, the revised
real assistant, cross-country reliability and the owner-deferred live durable-hosting
gate remain open. The stable FCV Project Screener remains untouched.
