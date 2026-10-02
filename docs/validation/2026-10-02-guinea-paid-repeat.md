# Guinea paid repeat - 2026-10-02

The owner explicitly requested one further paid assessment on the unchanged candidate.
Guinea on `b8f997035edb63bafb356d93b1bef28dfdda7161` failed safely after bounded
repair: one `unsupported_cpf_response` and one `prohibited_policy_language` issue
remained. No findings were released. Paid testing stopped after this one assessment.
Production acceptance remains open; no application code, deployment or hosting changed.

## Method and frozen scope

Application source remains `b5f0578`; subsequent commits only record validation.
The exact candidate's [CI run 36853735857](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/36853735857)
was successful before submission. The earlier exact code commit passed 1,722
provider-free Linux tests; that full suite was not repeated locally for this unchanged run.

The same three verified public Guinea PDFs, Decision Review stage, approved public
registry v1.1.0 and unsteered guidance were used. The
[existing input set and acceptance criteria](2026-10-01-provider-free-release-gates.md)
remained fixed. A new ignored frozen record captured authorization for this unchanged
repeat, exact release, input/runner/engine hashes, six prior ledger reservations and the
one-assessment stop rule before submission. Runtime imports were guarded to the target
worktree. Existing SQLite state, four-per-UTC-day and two-per-client-hour limits remained.

New copies of the existing runners changed only their exact-head pin, sibling filename,
authorized label and expected ledger count. Before paid submission, this exact runner
passed all 11 synthetic browser checks and exited normally with code 0. Both Word
downloads, synthetic assistant formatting, refresh and desktop/mobile checks passed;
there were no provider calls. Shutdown took longer than the prior rehearsal, but the
runner exited normally after 190.97 seconds. Its summary screenshot was inspected.

The paid runner omitted the assistant option. It reserved the seventh ledger entry
before its single submission and blocks another attempt after that reservation.

## Paid outcome

Submission occurred at 10:01:40 UTC. Extraction, source resolution, public research,
evidence construction, RRA mapping and review generation completed. The first validation
found four blocking issues across two codes; their per-code initial counts are not
available in the safe aggregate. Bounded repair reduced the total to two, with both
codes still present.

| Phase | Blocking issue count | Reported codes |
| --- | --- | --- |
| Initial validation | 4 | `unsupported_cpf_response`, `prohibited_policy_language` |
| After bounded repair | 2 | `unsupported_cpf_response`, `prohibited_policy_language` |
| Final application outcome | Failed | `review_failed`; no findings released |

Six advisory issues had the codes `missing_current_context_support` and
`stage_length_overreach`. No `target_locator_mismatch` code appeared in the reported
blocking sets. This does not establish that the previous locator problem is fixed,
or that the unreleased draft was factually correct.

The final CPF response did not satisfy the verified-quotation/allowed-absence rule,
and policy wording still triggered its guard. These codes do not reveal the rejected
response, row identity, attribution, policy phrase or precise repair cause. Rejected
content and model output were not retrieved or saved. No accepted result or paid Word
exports exist, so the source, factual, analytical and accepted-output experience gates
cannot be graded from this case. No real assistant request followed.

The runner exited normally with code 1 after 664.58 seconds overall, approximately
10 minutes 15 seconds after submission. All four paid screenshots were inspected.
The stopped screen explains that no findings were released and that a new submission
uses another allowance. There were zero JavaScript, console or HTTP resource errors.

## Separate read-only Render check

Following the owner's question about Render diagnostics, the Render connector was used
to inspect this service, its three latest deployment records, error logs and metrics.
The live deployment remains `992c35a`; the two preceding deployment records are
deactivated. A direct TLS-verified `/health` request returned HTTP 200, `status: ok`,
that same release and volatile storage. No configuration or deployment was changed.

The queried 24-hour window ending at 10:16 UTC on 2 October had zero application logs
at error level and zero request logs matching HTTP 500/502/503/504; neither query had
more pages. Thirteen five-minute samples from 09:16 to 10:16 UTC showed approximately
265 MiB memory use against a 512 MiB limit and one instance throughout. These quiet
live-service observations do not test load capacity, durable state or the local
candidate's model failure. Today's assessment ran locally and is absent from Render's
runtime logs. The safe API summary is retained as `20261002_render_readonly_diagnostics.json`
in this paid run's ignored evidence folder.

## Integrity and retained evidence

Post-run checks confirmed unchanged input, runner and engine hashes and the unchanged
canonical hash of the six preceding ledger entries. Read-only SQLite inspection
confirmed global counts of four on 30 September, two on 1 October and one on 2 October.
No quota reset occurred. The prior paid cases and their evidence remain preserved.

Ignored evidence is relative to this worktree under
`output/playwright/20260930_renewed_acceptance/`:

- `20261002_locator_retry_frozen_criteria.json`: authorization and frozen scope.
- `20261002_local_qa_locator_retry.py` and `20261002_quality_browser_locator_retry.py`:
  the exact checked runners.
- `browser/synthetic-locator-retry-preflight-01/`: 11-check preflight, screenshots,
  synthetic accepted JSON and both Word downloads.
- `runs/quality-11-guinea-locator-retry/`: four screenshots, health, runner status,
  allowlisted event status and `20261002_final_evidence_inventory.json` with hashes.

No application fix was inferred from these safe codes. Before another paid acceptance,
the next useful work is provider-free diagnosis of quotation preservation/ownership
and policy repair using public or synthetic controls. Repeated unchanged attempts do
not establish reliability. Fresh factual acceptance, the revised real assistant,
cross-country reliability and owner-deferred live durable hosting remain open.
The stable FCV Project Screener was not modified. PR 39 remains draft.
