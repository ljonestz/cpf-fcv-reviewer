# CPF reviewer and mAI Factory session handover

**Superseded for continuation on 6 October 2026:** start with
[the current production-readiness handover](20261006_cpf-mai-production-readiness-handover.md).
The record below preserves the state before the subsequent three-run mAI-only
cycle. Its branch, research and running-service descriptions are historical;
do not use its startup or run allowance as current authorization.

Prepared 4 October 2026 at the owner's request to continue in a fresh LLM session.
This is the navigation and decision record. Dated validation records remain the
authority for individual test results. No model call or deployment is authorized
merely by reading this file.

## 1. Immediate state and next task

The owner wants the CPF FCV Reviewer production-ready, with reliable evidence,
usable output and strict spending controls. Repeated paid failures have been
frustrating. Do provider-free diagnosis and repairs before another full run.

The local mAI integration connects successfully and uses Sonnet 4.6. Its first
full Guinea CPF/RRA assessment on 4 October failed evidence validation after
bounded repair. Six grounding issues remained. No accepted findings, exports or
assistant response were released. The app is NOT production-ready, and the local
version is NOT yet proven equivalent to the Render version.

Next: investigate the source quotation, evidence-reference and recommendation
target failures using safe diagnostics and synthetic fixtures. Establish a
reproducible cause before changing code. Research coverage is a separate gap:
the institutional path accepted zero current sources in this assessment.
Do not start another full assessment under the completed one-run authorization.

## 2. Workspace and reading order

Main repository:
`C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer`

Active worktree, containing all candidate application changes:
`C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer\.worktrees\production-readiness-20260930`

The chat's default cwd can still be `Claude_Outputs\cpf_screener`; explicitly set
the active worktree for repository commands. Do not confuse it with the main
checkout or the separate stable FCV Project Screener.

Read in this order:

1. Global AGENTS.md and current `.claude/codex_skills.prompt.md`.
2. This file, repository `CLAUDE.md`, `README.md`, `docs/PROJECT_STATUS.md` and
   `docs/PRODUCTION_READINESS.md`.
3. `docs/validation/2026-10-04-mai-local-assessment.md` and
   `docs/validation/2026-10-04-mai-desktop.md`.
4. For mAI work: `C:/Users/wb559324/.claude/20261004_mai-factory-guide.md`.
5. For hosting work: `C:/Users/wb559324/.claude/20261004_posit-connect-guide.md`.
6. Earlier evidence only as needed; start with the 3 October quality follow-up
   and paid acceptance records listed below.

Check branch, worktree status and HEAD yourself before editing. This handover
was written on `docs/mai-session-handover`, based on `c3f9b64`; the handover commit
necessarily comes after the hashes recorded here. Create a repair branch from
this candidate, not from old main. Source application code remains `05772b7`.

## 3. Branches, commits and deployment separation

| Track | State at handover |
| --- | --- |
| Public Render app | https://cpf-fcv-review-prototype.onrender.com/ ; historical verified release `992c35a`, not rechecked during this handover |
| Production repair candidate | Draft PR 39, `fix/production-readiness-20260930` against main; source-faithfulness/presentation code `9914483` |
| Posit URL-prefix compatibility | Draft PR 40, `feat/posit-connect-compatibility` against repair branch; code `e196b3d`, final test adjustment `7e88c41` |
| Local mAI provider | Draft PR 41, `feat/mai-desktop-preflight` against Posit branch; integration `3a3ff8c`, final UI code `05772b7`, evidence docs `cea43aa` |
| Full local acceptance record | `test/mai-local-acceptance`, pushed commit `c3f9b64`; documentation only, no repair after the failure |
| Handover | `docs/mai-session-handover`, based on the acceptance branch |

PRs: https://github.com/ljonestz/cpf-fcv-reviewer/pull/39,
https://github.com/ljonestz/cpf-fcv-reviewer/pull/40,
https://github.com/ljonestz/cpf-fcv-reviewer/pull/41.
They are stacked drafts. None of these candidate changes has been merged or
deployed in this work. Do not flatten the stack or silently deploy all branches.

## 4. Decisions already made by the owner

- Render should remain public, with strict limits: four new assessment admissions
  per UTC day globally, plus existing per-client/assistant limits. An admission
  ceiling is not a provider dollar-budget control.
- Avoid new hosting cost for now. Local mAI testing is the current development
  path. No new production spending approval should be inferred.
- Use verified CPF/package quotations for the RRA table's CPF response. Keep
  interpretation in separate analytical fields. Do not relax grounding to get a pass.
- The core FCV Strategy is embedded in the approved, versioned public registry;
  it does not need uploading. Preserve its integrity check and four strategy shifts.
- Local mAI uses Sonnet 4.6, explicitly approved by the owner.
- Send `GTFS1` as the mAI team header. The gateway accepted it; its formal ITSAI
  reporting/allocation registration has not been confirmed.
- Existing institutional-source research, with reduced/document-led notices, was
  approved for initial local testing instead of building broad search immediately.
- Save screenshots and safe JSON/Word evidence. Never overwrite historical results.
- Prefer Edge. Reuse the dedicated authenticated session; do not ask for login
  again without evidence that it is needed.
- Continue authorized provider-free diagnosis/repair; ask about material design
  choices when unresolved. The latest request was handover, not another model run.

## 5. mAI access and implementation

The owner has Desktop DEV access only, historically approved under eServices
RITM00009678465. It is for local proof-of-concept/development/testing, not a hosted
service used by colleagues. Desktop quota is 50M tokens/user/month per the portal.
Application access, ACN/use-case approval and chargeback arrangements remain separate.
Never move Desktop bearer tokens, WAM caches or laptop identity to a server.

Existing workspace stays outside OneDrive:
`C:\Users\wb559324\mAI_Factory`.
Use its existing `.venv\Scripts\python.exe`. Python is 3.13.7; SDK
`itsai-platform` is 0.1.2. Do not run `uv sync` against its empty dependency list,
recreate the environment, patch site-packages or rerun Activate.ps1. Original
example scripts remain unchanged and still include a retired endpoint.

Implemented files:

- `src/cpf_fcv_reviewer/mai_desktop.py`: fixed DEV Sonnet 4.6 Bedrock Converse
  route; WAM token refresh through `get_token` per request; serialized auth;
  verified TLS, 300-second request timeout, no automatic transport retry or direct
  paid-provider fallback. Native Converse `outputConfig.textFormat` carries the
  transformed JSON schema, followed by Pydantic and application validation.
- `config.py` / `runtime.py`: opt-in `MODEL_PROVIDER=mai_desktop`, development only,
  required team header, actual model metadata, explicit institutional recovery.
- `app.py`: loopback peer/Host enforcement, same-origin browser checks, forwarded
  header rejection. Do not remove these checks to make Desktop mode shareable.
- `templates/index.html`: local-mode, quota and research limitation notices.
- `scripts/20261004_run_mai_desktop.py`: authenticates before starting the worker,
  uses approved registry, SQLite under ignored `output/mai-desktop`, no direct key.
- `tests/test_mai_desktop.py`: transport, schema, failures, auth/config, research
  qualification, no direct-provider construction and local-access checks.

The assistant adapter returns one complete answer chunk, not native streamed
tokens. Real-provider assistant behavior has not yet been accepted end to end.
Curated recovery uses Crisis Group feeds and optionally ReliefWeb with an approved
app name. A World Bank indicators adapter exists but is not part of this recovery
path; do not claim all three sources are active. Broad web search is absent here.

Eleven missing app dependencies were added to the mAI venv without changing any
pre-existing package version; `pip check` passed. The package inventory is ignored
at `output/mai-desktop/20261004_environment_before.json`.

## 6. Verification and failed local run

| Check | Verified outcome |
| --- | --- |
| Four tiny live mAI probes | 385 tokens total; basic connection and exact adapter succeeded; the Anthropic-style schema body was silently ignored, so native Converse shape was used |
| Final local integration code `05772b7` | 1,796 Linux tests and Python name/import lint passed: https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37212892960 |
| Posit mount preparation | 1,773 Linux tests and 11 synthetic mounted browser checks passed; no hosting deployment |
| Exact 4 October browser runner smoke | 11/11 checks, upload/results/assistant/refresh/two downloads/mobile, no browser errors; slow cleanup eventually exited 0 |
| One real local Guinea run | Model generation and repair occurred; failed evidence validation, runner exited 1 after 367.27 seconds overall |

The real run began at 15:52:30 UTC on 4 October. Initial validation: 17 issues,
codes `unsupported_cpf_response`, `unknown_assessment_evidence`, `unknown_evidence`,
`target_locator_mismatch`. After bounded repair: six issues remained, with the same
codes except `unknown_evidence` cleared. Diagnostics show two quote-not-in-cited-text
mismatches and two target excerpt mismatches both before and after repair.

Current research returned zero candidates/accepted sources and used the document-led
fallback. The failure is not an observed authentication, gateway HTTP or JSON parsing
failure. Its exact generation/repair cause is not yet established. Do not claim that
all six defects are hallucinations, or that a specific prompt change will fix them.

No failed model narrative was retrieved. No validated result, live Word output or
assistant call exists for this run. SQLite independently records one review admission
and no assistant admission. Full-run token usage was not captured; only the earlier
tiny probes have an exact token count. No direct Anthropic call occurred.

## 7. Evidence locations and safe inspection

All paths below are relative to the active worktree unless explicitly absolute.
They are ignored and must not be staged or uploaded as source bundles.

- `output/playwright/20261004_mai_acceptance/20261004_mai_browser_acceptance.py`:
  copied existing runner with a one-run local reservation; no change to old paid ledger.
- `output/playwright/20261004_mai_acceptance/20261004-mai-assessment-reservation.json`:
  exclusive-create reservation. Preserve it; do not remove it to rerun.
- `output/playwright/20261004_mai_acceptance/browser/20261004-smoke-01/`:
  nine screenshots, synthetic validated JSON, two synthetic DOCX files, QA status.
- `output/playwright/20261004_mai_acceptance/runs/20261004-mai-guinea-01/`:
  intake/progress/failure PNGs, health and QA JSON, `20261004-safe-diagnostics.json`.
- `output/mai-desktop/20261004_final_preflight.json` and
  `20261004_mai_desktop_intake.png`: earlier connectivity/UI evidence.
- `output/mai-desktop/sessions.sqlite3`: local state and admission counters;
  sessions expire after 24 hours. Do not dump it or commit it.
- Private failed-assessment handoff: OS temp directory,
  `cpf-fcv-renewed-acceptance-20260930/20261004-mai-guinea-01-handoff.json`.
  The identifier is deliberately absent from this handover.

Public source PDFs, already approved:
`C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\guineacpf.pdf`
and sibling `guinearra.pdf`. Do not open dated subfolders containing sensitive
handoffs. Hashes of both inputs are in the safe diagnostics record.

Read-only SQLite events use zlib-compressed JSON in `events.value`; status is in
`sessions.status`. Prefer the saved safe record. If further diagnosis is needed,
retrieve only allowlisted event codes/counts/reason-level diagnostics. Never print
rejected values, prompts, draft narrative, auth tokens or whole session payloads.

## 8. Earlier failures and repairs to preserve

Nine historical direct-provider full-run reservations predate this local mAI test;
that old ledger is unchanged. Do not pool or reset it with the new mAI reservation.

The 3 October direct-provider Guinea run completed, with five CPF quotations and
three recommendation anchors independently verified against source pages, but its
surrounding analysis overstated dates/projections, source attribution, institutional
mechanisms and proposed arrangements. Factual acceptance was held.

Provider-free follow-up `9914483` fixed date/qualification metadata and Word/browser
presentation and strengthened source-faithfulness instructions (review 3.0.10,
repair 3.0.11). It passed 1,769 tests. These tests are not proof of real-model compliance.
Do not rewrite the old accepted output as if its narrative had been repaired.

Read as needed:
- `docs/validation/2026-10-03-source-selection-recovery.md`
- `docs/validation/2026-10-03-quote-selection-paid-acceptance.md`
- `docs/validation/2026-10-03-provider-free-quality-follow-up.md`

Current code offers optional `CPF_QUOTE:<evidence-id>:<passage-number>` selections;
the application copies the source passage. Literal quotations remain a supported
fallback. Inspect `source_grounding.py`, `review_engine.py`, orchestrator repair
handling and `tests/test_reference_resolution.py`. The safe failure categories do not establish which
precise source text or reference went wrong. Use synthetic reproductions first.

## 9. Intranet retrieval question

The owner asked whether mAI Factory can find WBG internal documents like the mAI
assistant. Official documentation was read in authenticated Edge on 4 October:
https://ai.worldbankgroup.org/maifactory/documents-reports/.
It describes Operations Search against the Bank's internal database, supporting
query/filter/sort/facet operations. Its prerequisites name client credentials and
an APIM key, while its SDK example shows Desktop plus an APIM key. The rendered
page still shows a legacy `conversationalai` route.

Portal example assets also describe a mAI conversational API with Application
access and `WorldBankSearch`, `ExternalSearch`, `PeopleSearch`, `ProjectSearch`.
Those examples do not establish a current usable endpoint, permission enforcement,
full-document retrieval, all-SharePoint coverage or parity with the mAI assistant.

No internal search API was called, no internal document was retrieved, no search
integration was added and no message was sent to ITSAI. Next information needed:
current endpoint, entitlement, subscription-key provisioning, corpus/download
coverage, permitted processing and how caller-specific document permissions are
preserved. Detailed institutional setup belongs in the local shared mAI guide.

## 10. Posit and sharing constraints

No CPF app is deployed on Posit; no shareable Posit CPF link exists. The local
address `http://127.0.0.1:58423/` works only on this computer while the app is running.
The public Render URL above is a different version for public/non-sensitive inputs.

The shared Posit guide was updated independently: both internal and external
publishing accounts are now verified. Preserve that newer fact; older CPF notes
that internal publishing was unverified are historical. Both servers were reported
as Connect 2026.08.0 with Python 3.8.18, 3.9.13 and 3.11.9 on 4 October. The CPF app
still requires Python >=3.13. Do not silently lower the requirement without testing.

Hosting still requires Application/ACN approval, compatible runtime, durable
single-instance storage, worker/idle lifecycle verification, backups and actual
access testing. Connect publishing permission does not grant mAI Application access.
Separate app copies have separate admission counters. Do not expose Desktop mode
through a tunnel or remove its loopback guards as a sharing workaround.

## 11. Workstation and browser runbook

- Global Python `C:\WBG\Python313\python.exe` has Playwright and worked for the
  current browser runner. The CPF test venv lacks Playwright; do not install again
  before checking the existing global runtime.
- CPF test venv: `C:\Users\wb559324\venvs\cpf-fcv-reviewer\Scripts\python.exe`.
- mAI app venv: `C:\Users\wb559324\mAI_Factory\.venv\Scripts\python.exe`.
- `rg.exe` and local Ruff are blocked by Application Control. Use `git ls-files`,
  `git grep`, Get-ChildItem and Select-String. Do not bypass policy. Linux CI lint passed.
- PowerShell uses constrained language mode. Use supported cmdlets or Python and
  `-X utf8`; no TLS disabling. Existing bad global CA paths can break unrelated tests.
- Valid task CA bundle was at OS temp
  `cpf-fcv-renewed-acceptance-20260930/20260930_trusted_ca.pem`; verify existence.
- Read the Playwright skill. Native connected browser inventory was empty;
  installed Playwright still works. Use the installed CLI and required escalation,
  not a fresh npm download. Browser commands can take several minutes; refresh
  state before concluding a timeout means app failure.

Dedicated persistent Edge session: `posit-edge`, browser cwd
`C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer\output\playwright`.
CLI: `C:\Users\wb559324\npm-cache\_npx\9833c18b2d85bc59\node_modules\playwright-core\lib\tools\cli-client\cli.js`
using `C:\Program Files\nodejs\node.exe`.
Check sessions/tabs afresh. Last tabs included local app at index 4 and DNR docs at
index 5; index 0 is Posit API-key settings, which must not be dumped or screenshotted.
Do not close unrelated windows or use the normal browser profile.

The local mAI service was healthy at the last check, with a failed retained review
and live persistent worker. Verify before using it. The task-owned synthetic server
on port 58422 was stopped; its PID must not be reused for future cleanup.
Tool session IDs from the old chat are not a reliable cross-session control mechanism.

If startup is needed, from the active worktree:

```powershell
$env:MAI_TEAM_NAME = 'GTFS1'
$env:SSL_CERT_FILE = Join-Path $env:TEMP 'cpf-fcv-renewed-acceptance-20260930\20260930_trusted_ca.pem'
& 'C:\Users\wb559324\mAI_Factory\.venv\Scripts\python.exe' -u scripts/20261004_run_mai_desktop.py
```

This signs in and starts the app, but does not itself submit an assessment. Do not
start a second server on the same port or restart an active review. Keep secrets
out of command output, source files and handovers.

## 12. Acceptance plan for the next session

1. Verify branch/worktree and consume the safe failure evidence. State what is
   known versus hypothesized; do not re-run broad passing suites to rediscover context.
2. Trace initial/repair grounding data flow. Reproduce a specific failure with
   synthetic evidence, then implement the smallest justified repair with regression
   coverage. Preserve full document coverage, source identity and policy/date guards.
3. Investigate the zero-source research result separately without model calls.
   Distinguish feed/network failure, filtering, missing configuration and actual
   corpus coverage; do not promise mAI intranet access as already available.
4. Run focused provider-free tests, then required CI/synthetic browser acceptance
   for any changed behavior. Preflight the exact runner before any authorized live run.
5. Report what is now established and what still requires one fresh model-backed
   acceptance. Obtain a new explicit allowance before submitting it. Do not raise
   quotas, delete reservations, weaken validation or silently switch providers/models.
6. On eventual success, inspect both source fidelity and rendered outputs, assistant,
   refresh and downloads. A successful HTTP result or test suite is not production
   acceptance. Cross-country, hosting persistence/restart/restore and spending controls
   remain additional gates.

No application behavior changed during handover preparation. Global setup guides
are local-only, outside Git; this repository handover and status updates are pushed
on the handover branch. Preserve the separate stable FCV Project Screener throughout.
