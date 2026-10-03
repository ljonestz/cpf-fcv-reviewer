# Source-selection recovery and release evidence - 2026-10-03

Application commit: `09805d696e99537da62879dc03a32d1a79c6cf8f`.
Scope: provider-free repair of the CPF FCV Reviewer. No paid assessment, merge,
Render deployment, hosting charge, quota reset or stable Project Screener change.

## Method

Traced the initial review, repair merge, source verifier, policy/date validators,
runtime diagnostics and browser/export paths. An independent read-only audit identified
mixed-error and row-identity defects; synthetic regressions exercise the real engine.
Public-source controls check exact text round trips, not the substantive quality of a
model assessment. The precise remaining error in the last rejected paid draft is still
unknown because rejected content was not retrieved.

## Changes and safeguards

| Problem | Implemented change | Backup or boundary |
| --- | --- | --- |
| Model must recopy quotations exactly | Model can select an app-owned passage ID; the app materializes exact source text before validation/display. | Exact literal quotations remain supported. A selection requires the same row's known primary/package citation. |
| Quote failures were indistinguishable | Safe reason codes plus an internal zero-based row index reach repair. Public events expose allowlisted reason counts only. | No rejected text, row index or private diagnostic message is published. |
| Unknown citations could cause wholesale row replacement | Quote repairs preserve original identity, analysis, status and confidence; transfer only verified quotation and known citations. | Explicit, separately flagged coverage-status repair retains its existing permitted behavior. |
| Policy/date-only repair lost renamed rows | A unique unchanged driver can recover its original row ID for these repairs too. | Duplicate/ambiguous identities remain blocked. |
| Index could make a complete request too large | Remove the optional index if needed, then apply the unchanged hard input limit. | All original evidence text remains; literal quotation path is used. No sampling or extra calls. |
| An unpunctuated page could become an enormous quote | Only complete source passages up to 1,500 characters are selectable; previews are at most 160 characters. | Oversized passages are not silently shortened; complete evidence remains available. |
| Need a recoverable local state | Created a new native SQLite backup, then compared integrity and all table counts with the live local store. | Existing backups, paid ledger and admission counters were preserved. Remote retention still needs an operational decision. |

Review prompt is v3.0.9; repair prompt is v3.0.10. Schema, policy guards, four-per-day
admission ceiling, provider call limits and bounded repair policy remain unchanged.
A verified quote establishes source wording, not its relevance or the correctness of analysis.

## Verification

- Final application commit passed **1,755 provider-free Linux tests** in 27.19 seconds,
  including Gunicorn concurrency. Python name/import checks passed in
  [CI run 37073544182](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37073544182).
- Final candidate browser test deliberately produced an unsupported initial quotation,
  then returned a selected source ID during the single repair. The app completed normally
  in 50.77 seconds overall (5.18 seconds after submission), with exactly one synthetic
  review and one synthetic repair. All 11 browser checks passed, with zero console,
  page or resource errors. Refresh, assistant history, desktop/mobile views and both
  Word downloads worked. The validated JSON and Word documents contain no selection tokens.
- The final public control resolved **10,251 selectable passages across 513 pages in
  seven CPF/CEN files**: Afghanistan, Chad, Gambia, Guinea overview/results framework,
  Lebanon and Tajikistan. Every resolved quote matched its cited source. All seven
  primary-only request controls fit the existing budget; Guinea retained the index,
  and the five longer documents used the literal fallback with full evidence preserved.
  These controls exclude added RRA/current-research payloads and do not establish that
  every complete country package fits. Gambia's primary-only request was already
  155,459 estimated tokens against the 160,000 ceiling.
- Native backup integrity and source/backup table-count equality passed. The local
  backup contains sensitive session state and stays outside the repository.
- Initial local full-suite execution hit Windows temporary-directory permissions.
  The approved rerun had one obsolete budget-boundary expectation, subsequently
  corrected to test the hard limit after optional-index removal. Final Linux CI is the
  authoritative full-suite result; the local Gunicorn check is platform-skipped.

## Saved local evidence

Ignored output folder `output/20261003_quote_selection/` contains public-control scripts,
JSON, local test XML and backup verification. The final public control is
`20261003_final_public_selection_control.json`; the earlier file documents the unbounded
index experiment and is not the final request-size measurement.

`output/playwright/20260930_renewed_acceptance/browser/20261003-quote-selection-final-09805d6/`
contains nine screenshots, validated synthetic JSON, both Word downloads, browser status
and `recovery-proof.json`. The final desktop screenshot was visually inspected; the earlier
same-layout desktop/mobile pair was also inspected. Artifacts remain local and ignored.

## Remaining launch gates

This is a verified engineering candidate, not a production-readiness declaration.
The next paid assessment must be explicitly authorized against a fixed candidate and the
same hashed public Guinea inputs, with the existing eight renewed paid reservations
preserved. Keep the previous factual acceptance criteria: inspect every quotation,
attribution, date, number and recommendation, plus JSON/Word delivery. Do not retry
an unchanged paid failure. New safe quote reasons will make any remaining rejection
more diagnosable without exposing rejected content.

Real-provider assistant behavior and cross-country factual reliability remain unaccepted.
Before public production launch, the previously documented Render persistence and live
restart/restore checks, off-disk backup retention, and provider-account spending controls
remain outstanding. Existing Render API access was verified on October 2; this engineering
turn made no hosting changes. No additional paid assessment was launched.
