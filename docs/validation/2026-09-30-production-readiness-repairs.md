# Production readiness repair candidate: 2026-09-30

Branch: `fix/production-readiness-20260930`, based on main `f65c3e3`.
The live release remains `992c35a`; no deployment or additional paid assessment is recorded here.
The original four paid audit assessments exhausted the approved test ceiling.

## Scope and acceptance method

Repair the demonstrated audit defects using provider-free regressions, full public-source
extraction checks, independent code inspection, synthetic browser QA and Linux CI.
Synthetic results establish application behavior; they do not establish model quality.
The approved public FCV Strategy registry v1.1.0 already contains all four core shifts.
No Strategy upload or internal policy content is required.

## Issue disposition

| Audit issue | Candidate behavior | Acceptance limit |
|---|---|---|
| CA-01: unbounded paid submissions and streams | Global four new assessments per UTC day; two per client/hour; same admission for correction and research retry. One review worker, four active/pending reviews, eight review streams, one assistant stream. | Single instance/process required. Four admissions cap starts, not exact dollars. |
| CA-02/CA-05: partial primary/contradictory package bounds | Every readable primary segment and complete retained package text is supplied. Primary 400 PDF pages/600k characters; package 400 segments/300k aggregate characters, 400 pages per PDF. Final compact request limit 160k estimated tokens. | Unextractable figures/images are excluded. Oversized inputs fail explicitly; early raw-text overflow rejects before paid research, final complete gate remains. |
| CA-03: invalid stages accepted | Unsupported stages rejected before session/job/provider work. | Provider-free endpoint and runtime regressions. |
| CA-04: raw exception logging | Assistant/export exceptions log type only; safe failure responses remain. | No raw rejected output is stored in this record. |
| CA-06: stale metadata | Runtime release, actual prompt declarations and loaded registry version are retained with existing content hashes. | Local default is dev; live release must be checked after deployment. |
| QA-01/QA-02: historical present-state and wrong target/owner | Prompt contracts preserve real CPF provisions and section/institution ownership; physical-page and exact target excerpt guard added; unsupported ongoing-transition assertions require recent cited support or a condition tied to that assertion. | Paraphrase accuracy, ownership interpretation and broader factual quality still require fresh model-output review. |
| QA-03: Gambia diagnostic provenance | Cover full dates accepted and normalized to publication month; whitespace and country aliases handled conservatively. | Actual public RRA is recognized with June 2017 provenance. Prior recognition failure's cause is not proven; date parsing defect is proven. |
| UX: oversized management view and vague failures | Sentence-complete bounded summaries in browser/Word; complete detailed measures retained; actionable safe errors and refresh-to-reconnect guidance. | Summary explicitly directs users to full findings and qualifications. |
| Operational persistence/recovery | SQLite remains the durable store; interrupted running work fails terminally rather than automatically repeating paid calls. Queued work remains claimable. | Durable disk and live restart checks still required. |

## Public pilot limits

All POST routes share a 30/hour client admission limit. Assistant requests have a separate
12/day global ceiling, six/hour per client and six/day per review. Counters are SQLite-backed
with hashed client addresses and survive deleting reviews or restarting. `TRUST_RENDER_PROXY`
is disabled by default and enabled only in the Render blueprint. Render documents that its
Cloudflare edge overwrites caller-supplied `CF-Connecting-IP`; arbitrary X-Forwarded-For is ignored.
Reference: https://render.com/articles/host-pocketbase-on-render

Failed admitted assessments conservatively use the daily allowance. Internal existing schema
and repair limits remain unchanged. Configure provider-account spending controls separately;
an admission ceiling cannot enforce an exact dollar budget.

## Durable deployment and backup procedure

The reviewed `render.yaml` specifies one starter web service, one gthread worker, 16 request
threads, a 1GB disk at `/var/data`, `/var/data/reviews.sqlite3`, and the volatile exception disabled.
These are candidate settings, not an assertion about the current live dashboard.

Use the native SQLite backup utility while the application is live:

```sh
python -m cpf_fcv_reviewer.database_backup /var/data/reviews.sqlite3 /var/data/backups/DATE-reviews.sqlite3
```

The destination must be new. The utility uses SQLite's backup API and validates integrity;
copying the main database file alone can lose committed WAL state. Backups include review
inputs and admission quotas and must remain outside Git. For restoration, stop the service,
preserve the current database/WAL/SHM as a separate recovery set, restore the verified backup,
and restart. Do not restore over a running database. Confirm health reports persistent storage,
queued jobs remain claimable, interrupted jobs are terminal, and quota counters remain enforced.
Choose backup retention and off-disk recovery storage before operational launch; snapshots alone
are not a tested SQLite restore procedure.

## Verification

Engineering source commit `25437b3` passed [Linux CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/36730723644): **1,669 provider-free tests** in 22.04 seconds, including real Gunicorn saturation with eight viewers, rejection of the ninth viewer and responsive health checks. Python name/import checks also passed. Windows Application Control blocks local Ruff; no policy bypass was attempted.

Synthetic browser acceptance passed **12/12 checks** with public admission enabled and no provider key or model calls: upload/country confirmation, stage selection, result retrieval, summary and detailed views, target-document display, assistant/history restoration, page refresh, correction rerun, mobile/long-paragraph wrapping, and safe injected submission failure. Both Word downloads opened as valid DOCX packages. This checks export structure and content; it does not certify Word page layout. The single priority card fills the available desktop width, and recovery sits directly below the stopped-review message.

Artifacts remain local, outside Git, under `output/playwright/20260930_production_readiness_repairs/browser/synthetic-smoke-repairs-04/`: **12 PNGs, two DOCX downloads, two application-validated synthetic result JSON files and qa-status.json**. The coordinator directly inspected desktop, mobile, detailed and failure screenshots across the two successful flow runs. The final run had no JavaScript page errors. That run recorded one cosmetic missing-favicon console 404. The shared HTML head now suppresses that unused request; a subsequent no-submission Edge check passed with zero console or resource errors (`20260930_icon_preflight.json`). Earlier harness assertions were corrected to match the existing detailed target locator and safe failure copy; a subsequent local quota collision was avoided by assigning a fresh server port and verifying empty admission counters before starting.

The browser saved its passing checks and artifacts before cleanup stalled. Only the exact QA execution was interrupted after its PASS marker; its ephemeral HTTP port was confirmed closed. This is a Windows automation teardown limitation, not a successful runner exit. The separately identified earlier provider-free smoke server was stopped by its verified PID; its HTTP port was confirmed closed.

All **14 downloaded corpus files** matched their recorded SHA-256 and sizes; **seven primary PDFs** fully extracted within extraction bounds. The Gambia primary-only compact estimate is **155,350 input tokens**; this excludes registry, context and mapped diagnostic, so the complete request remains unverified. Oversized complete requests fail explicitly. Chad CEN Annex/page ownership remains unresolved from extraction alone and requires expert inspection of fresh output.

## Remaining launch acceptance

- Merge and deploy the reviewed candidate with the prepared 1GB persistent disk and fail-closed production persistence settings. The current live release is still `992c35a` with volatile storage; no deployment occurred during these repairs.
- Verify live persistent health, restart behavior, quota enforcement, and a real backup/restore. Choose backup retention and off-disk recovery storage. Local WAL/quota restoration and reopen/restart regressions passed; these do not establish a live operational restore.
- Set provider-account spending controls. The application admission ceilings bound starts and assistant use, rather than an exact dollar budget.
- Obtain a renewed paid-validation ceiling and review fresh country output for source ownership, existing CPF provisions, historical/current distinctions, research breadth and practical recommendations. The original four paid audit attempts exhausted the approved ceiling; **zero additional paid runs** were submitted. Synthetic checks cannot establish analytical accuracy.

The approved FCV Strategy registry v1.1.0 is embedded. No Strategy upload is needed. Production readiness remains conditional on the launch acceptance above.
