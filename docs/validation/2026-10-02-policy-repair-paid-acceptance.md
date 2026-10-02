# Guinea paid acceptance after quotation/policy repair - 2026-10-02

The owner approved one controlled paid Guinea assessment and a readiness/access check.
Candidate `5cfb64104b67d65f1571b9f603d822a4505dae41` contains application repair
`54cdf2a888f0fa6854039b76f230f4751c4f7faf`. No merge, deployment or hosting change occurred.

## Method and result

Before submission, exact-candidate CI passed all 1,730 provider-free tests and Python
name/import checks. The exact external runner passed 11/11 synthetic browser checks,
including file injection, results, assistant, refresh and both downloads, and exited
normally with code 0. Desktop detail and mobile summary screenshots were inspected.
A first launch with the test-only virtual environment lacked python-dotenv and exited
before app creation; the existing WBG browser-test runtime completed the preflight.
The provider's read-only models endpoint returned 200 with verified TLS; no model call
was made by this credential check.

The same verified public Guinea strategic overview, results framework and June 2023
RRA were used at Decision Review, with no special guidance. Their SHA-256 values,
registry, runner, engine, candidate, unchanged counters and stop criteria were frozen
before submission. Review prompt is 3.0.8; repair prompt is 3.0.9; registry is 1.1.0.

| Stage | Observed result |
| --- | --- |
| Submission | One new assessment at 15:35:39 UTC; existing SQLite store and four/day, two/client/hour limits retained. |
| Pipeline | Extraction, source resolution, current research, evidence building, mapping and draft review completed. |
| Initial validation | Three blocking issues across `unsupported_cpf_response` and `prohibited_policy_language`. |
| Advisory diagnostics | Six issues across `missing_current_context_support` and `stage_length_overreach`. |
| Bounded repair | One blocking `unsupported_cpf_response` remained. No policy-language code was reported at final failure. |
| Outcome | Failed safely; no findings, accepted JSON or Word exports released. No real assistant call. |
| Runner | Normal exit 1 after 879.20 seconds overall; approximately 831.40 seconds after submission. Zero console, JavaScript or resource errors. |

The policy check cleared in this attempt, but that does not establish durable policy
reliability or factual correctness. The remaining code means at least one CPF response
could not be verified against its own cited primary/package evidence (or allowed absence
rule). It does not identify whether the problem was quotation wording, citation choice
or another verifier condition. Rejected draft content was not retrieved. No exact cause
or specific faulty quotation is claimed from aggregate codes alone.

The earlier deterministic tests remain evidence of the repaired code defects; this real
run establishes that those repairs are insufficient for reliable completion. Another
unchanged paid retry is not recommended. The next engineering gate is a reproducible
remaining quotation case, supported by safe reason-level diagnostics, before proposing
a further correction or paid acceptance. Do not loosen source verification to obtain a pass.

## Cost and retained evidence

Paid testing stopped after this one assessment. The ledger now has eight renewed
reservations; a canonical hash confirmed all seven preceding entries unchanged. Read-only
global counters are four on 30 September, two on 1 October and two on 2 October. No quota
reset occurred and no automatic replacement assessment was submitted.

Ignored evidence is under `output/playwright/20260930_renewed_acceptance/`:

- `20261002_policy_repair_frozen_criteria.json` and the two dated policy-repair runners.
- `browser/synthetic-policy-repair-preflight-01/`: synthetic screenshots, accepted fixture,
  two Word downloads and the 11-check report.
- `runs/quality-12-guinea-policy-repair/`: four full-page PNGs, health and QA status,
  allowlisted event diagnostics, final hash inventory and Render/access checklists.

All four paid-run PNGs were directly inspected. Private assessment identifiers remain in
the existing OS-temp handoff only. Raw/rejected model content is not retained here.

## Render and launch prerequisites

| Requirement | Verified state / remaining action |
| --- | --- |
| Render API | Connected: service details, deployment, logs and metrics retrieved for the separate CPF Reviewer. No new API credentials needed for monitoring. |
| Live release | Older `992c35a`; TLS-verified health 200, status OK, volatile storage. This was not the host of the local paid test. |
| Runtime | One 0.5 CPU / 512 MB instance; one gthread worker and 16 threads configured. |
| Monitoring | No error-level app entries in 14:35:56-15:35:56 UTC. Thirteen five-minute memory samples about 265/512 MiB, one instance. Idle samples do not establish stress capacity. |
| Dashboard / server shell | Logged-in dashboard navigation observed, but disk-page navigation and follow-up snapshot timed out. Direct SSH timed out during banner exchange. Disk-management and backup-shell access remain unverified. No remote command or setting change ran. |
| Persistence | Prepared `render.yaml`: 1 GB at `/var/data`, SQLite `/var/data/reviews.sqlite3`, volatile exception disabled, one instance. Still requires owner approval of the previously deferred hosting change and live verification. |
| Backups | Native SQLite backup utility and local restore checks exist. Live shell access, backup retention and an off-disk recovery destination remain to be settled and tested. |
| Provider account budget | Authentication verified; account-level spending cap not verified. Four admissions/day limits starts, not exact dollar spending. |
| Quality / release | Remaining quotation failure, fresh factual/export/assistant acceptance and cross-country reliability remain open. Deploy only after acceptance; then verify persistent health, restart/quota retention and backup/restore. |

Render lists persistent disk storage at $0.25/GB/month, so the prepared 1 GB disk would
add approximately $0.25/month to existing hosting, subject to current billing terms:
[Render pricing](https://render.com/pricing). A disk restricts the service to one instance
and removes zero-downtime deployment; attaching it triggers a deployment. Database-native
backups are required instead of relying on disk snapshots for recovery:
[Render disk documentation](https://render.com/docs/disks).

The stable FCV Project Screener was untouched. Production readiness is not established;
Render access alone will not resolve the model quotation failure. No additional paid run,
new hosting charge, merge or deployment is implied by this record.
