# CPF FCV Reviewer: production-readiness continuation

Prepared 6 October 2026 at the owner's request. This is the current navigation
and decision record, superseding the [4 October handover](20261004_cpf-mai-full-handover.md).
Individual test outcomes remain in the [mAI research validation record](../validation/2026-10-04-mai-grounded-research.md).
This handover authorizes no new model call, merge or deployment.

## 1. Start here

The owner wants detailed, accurate country-informed CPF/RRA review comparable to
the Render version, while avoiding a separate external Anthropic research API.
The chosen route is research and generation through mAI Factory. It works locally,
but **the app is not production-ready and factual equivalence is not established**.

All three newly authorized full Guinea assessments are consumed. Two failed;
the third completed without repair, but manual source checks found material
analytical errors and inadequate current-country breadth. Follow-up code repaired
date consistency and the observed assistant advisory-boundary failure using
provider-free regressions. Those fixes have no new live acceptance.

The next substantive work is provider-free diagnosis and focused repair of table
interpretation, research coverage and report/assistant consistency. Do not start
a fourth assessment or another live research/schema/assistant probe. Request a
fresh bounded allowance only after the free diagnosis and verification are complete.

## 2. Workspace, reading order and Git state

Main repository:
`C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer`

Active worktree:
`C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer\.worktrees\production-readiness-20260930`

Always set this worktree explicitly for repository commands. The chat's default
cwd may be the separate `Claude_Outputs\cpf_screener`; never modify the stable
FCV Project Screener or mistake that folder for this repository.

Read in order:

1. Global AGENTS.md and current `C:/Users/wb559324/.claude/codex_skills.prompt.md`.
2. This file, repository `CLAUDE.md`, `README.md`, [project status](../PROJECT_STATUS.md)
   and [production readiness](../PRODUCTION_READINESS.md).
3. [Completed mAI-only cycle and Render comparison](../validation/2026-10-04-mai-grounded-research.md).
4. `C:/Users/wb559324/.claude/20261004_mai-factory-guide.md`, especially section 8.
5. Before any Posit work, `C:/Users/wb559324/.claude/20261004_posit-connect-guide.md`.
6. Earlier validation only as needed: [initial local failure](../validation/2026-10-04-mai-local-assessment.md),
   [provider-free grounding diagnosis](../validation/2026-10-04-grounding-and-hybrid-research.md),
   [research privacy boundary](../validation/2026-10-04-local-research-privacy.md), and
   [same-input direct-provider quality defects](../validation/2026-10-03-quote-selection-paid-acceptance.md).

Verified before this documentation update: clean branch
`feat/mai-grounded-research-20261004`, HEAD/upstream
`feb7f4c2f60d55adf6012af8147747606d2b9104`. Its
[CI passed](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37243875900).
The documentation-only continuation branch is `docs/session-handover-20261006`,
created from that candidate. Read Git status, current branch, HEAD and upstream
afresh; the handover commit necessarily follows the hashes recorded here.

Application code remains `529807080e01c75d486a0928d2bd33f891c26456`, which passed
**1,881 Linux tests and Python name/import lint**
([CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37243473492)).
The third live run used the earlier application `14f32d9`, not this follow-up.

Draft [PR 44](https://github.com/ljonestz/cpf-fcv-reviewer/pull/44) is stacked on
`fix/mai-grounding-diagnostics-20261004` / [PR 43](https://github.com/ljonestz/cpf-fcv-reviewer/pull/43),
above `docs/mai-session-handover` / [PR 42](https://github.com/ljonestz/cpf-fcv-reviewer/pull/42),
handover commit `0c757ba`. Earlier repair, Posit and Desktop work remains in the
stack described by the old handover. No candidate branch was merged or deployed.
Do not flatten the stack or start repairs from old main. Use a repair branch from
the current candidate after inspecting the actual Git state.

## 3. Decisions and boundaries to preserve

- Keep research on mAI; a separate Anthropic research key is not the chosen route.
  That optional earlier route remains in code but was not used in this cycle.
- Assessment/normalization uses approved Sonnet 4.6 through mAI. Public discovery
  uses mAI Gemini Google Search. This still calls public Google Search through mAI
  and incurs mAI usage; it is not offline or cost-free. Exact provider cost was not measured.
- Search receives only canonical country, review date and fixed public FCV topics.
  Uploaded CPF/RRA documents and user notes are excluded. Fetch public originals
  without bearer tokens; Google synthesis is not an original-page quotation.
- Preserve quotation/reference/target grounding, source dates, full readable package
  and RRA coverage, registry integrity, loopback guards and advisory boundaries.
  Do not use country-specific substitutions to mask an analytical error.
- Preserve all reservations and admission counters. No quota reset, cap increase,
  provider fallback or silent extra model retry is authorized.
- All three new full-run permissions are consumed; the older one-run mAI attempt
  and historical direct-provider reservations remain separate. At final inspection,
  SQLite recorded four daily mAI assessments including that older attempt, and one
  assistant admission. These are historical counts, not a fresh spending allowance.
- Desktop DEV identity is for local testing only. No credential deployment, merge,
  deployment or change to the stable FCV Project Screener is authorized.
- Reuse setup, successful checks and original evidence. Never commit tokens, private
  identifiers, raw source PDFs, model narratives or assistant conversations.

## 4. What was implemented and verified

| Area | Verified state | Limit of the evidence |
| --- | --- | --- |
| mAI discovery | Authenticated Google route works; bounded original-page fetches and scriptless attribution are implemented | Final full run retained reduced country coverage |
| Source selections | Model chooses CPF quotation/target passage IDs; app copies original text and reconstructs locators | Exact presence does not prove surrounding analytical claims or suitable edit locations |
| Transport schema | Full nested schema reproduced HTTP 400 grammar overflow; compact target-ID schema passed a synthetic probe with 260 choices | Compatibility alone is not assessment quality |
| Error classification | `MaiUnavailable` maps to model-output unavailability rather than evidence failure | Does not make a failed response usable |
| UTC date | Research date now agrees with UTC review metadata | Provider-free regression only after the last live run |
| Assistant boundary | mAI response is checked before its first chunk; observed policy-determination class is blocked | Synthetic coverage only; not a comprehensive semantic-accuracy guarantee |

Review prompt is 3.0.12, repair 3.0.13, diagnostic 1.2.0 and follow-on 1.1.3.
Verify current files before changing them; version assertions require updates when
prompts change. The mAI assistant returns one complete answer chunk.

### Newly authorized full runs

| Saved run label | Candidate | Outcome |
| --- | --- | --- |
| `mai-grounded-01-guinea` | `d5027ef` | Failed bounded repair: three quotation and three target-excerpt mismatches remained |
| `mai-grounded-02-guinea` | `671af40` | Research and mapping completed; review generation failed with transport/schema unavailability |
| `mai-grounded-03-guinea` | `14f32d9` | Completed without repair; execution passed but analytical acceptance held |

The third run started 4 October at 23:01 UTC after the normal hourly window opened.
It retained seven primary pages, five package pages and 101 readable RRA pages out
of 102 attempted. Five RRA drivers, four Strategy shifts and four priorities appear.
Four CPF quotations and four target excerpts matched their own cited PDF pages;
the fifth response row used the explicit absence sentinel. Assessment wait was
225.3 seconds; full browser flow was 295.11 seconds.

The original browser report remains 11/12 checks: its literal whitespace caveat
assertion failed. An independent GET-only check confirmed the complete caveat is
visible after normalization. Zero console/page/resource errors were reported.
Assistant/restoration and both DOCX downloads executed. All nine rendered Word
pages were inspected (two summary, seven detailed); original DOCX hashes were preserved.

## 5. Open analytical findings: do not mark these repaired

1. Framework physical page 5 specifies private-capital baseline **0 (2025)** and
   target **US$1 billion (2033)**. Report and assistant instead say TBC and propose
   adding the existing target. The adjacent jobs row is TBC; its women disaggregation
   and IDA ISR / IFC-MIGA reporting footnote are also overlooked.
2. The 2,260,022 electricity-beneficiary target is **people**, but the readout calls
   it connections. A correct quotation elsewhere does not validate this unit claim.
3. Accepted dated research concentrates on civic space: Amnesty July 2026 and HRW
   December 2024, plus an undated World Bank safety-net observation. Three dated
   observations from two dated publishers are not thorough current-country research.
   Economic/mining, land, security and resilience coverage needs investigation.
4. The report extrapolates transition risks from the June 2023 RRA and omits a
   contemporary election update. One priority changes 53 dissolved and 54 suspended
   parties into over 100 dissolved parties. Publication date and event date need
   separate treatment.
5. It asserts contents of an unprovided risk annex, inconsistently treats historical
   RRA-described GRM infrastructure as a current CPF provision, and gives unsuitable
   recommendation anchors (including a generic `Baseline: TBC.` passage).
6. The cached assistant amplified the table error, exceeded the requested summary
   length and triggered safe category `unsupported_policy_determination`. The narrow
   policy-language guard was repaired after the run; the analytical errors remain.

Research-local/metadata-UTC date mismatch was the other observed defect; code now
fixes it, but the saved output remains unchanged. Preserve the original report as
evidence, not as a cleared or production-quality assessment.

### Comparison limitations

Saved deployed Render release `3904935` has 3,546 detailed words and 1,461 summary
words, versus 2,717 and 770 for the new mAI result. Both cover five drivers and four
shifts. mAI better acknowledges some existing CPF provisions and avoids earlier
invented numerical commitments, but creates a false private-capital gap.
Historical Render also has known defects and different input coverage/date/model;
it is not a gold standard or a controlled provider comparison. The later local
direct-Anthropic candidate uses the same three PDFs and correctly reads the
US$1 billion target, but has other documented defects. Judge accuracy against the
original sources, and judge detail by coverage and usefulness rather than word count.

## 6. Evidence locations: local, ignored and preserved

Paths are relative to the active worktree unless stated otherwise. Never stage
their contents. Existing QA helpers may create output exclusively or call live
providers; inspect their code before use. Do not rerun successful probes or overwrite
historical reports merely to regenerate evidence.

- `output/playwright/20261004_mai_grounded_acceptance/`: exact runner, smoke preflight,
  three exclusive-create reservations and `runs/mai-grounded-01-guinea/` through
  `runs/mai-grounded-03-guinea/`.
- Final run folder: `validated-result.json`, original `qa-status.json`, `safe-events.json`,
  both DOCX files, screenshots, `20261005_independent_checks.json`,
  `20261005_readonly_browser_checks.json` and `20261005_mobile_capture_checks.json`.
- `output/20261005_mai_accepted_word/run03/`: nine inspected page PNGs, two rendered
  PDFs and `20261005_replay_word_layout.json`.
- `output/20261004_mai_grounding/`: cached discovery/research replays, sanitized
  schema compatibility results and ignored QA helpers. Synthetic schema probes in
  this folder were live gateway calls; do not execute them under exhausted authorization.
- `output/mai-desktop/sessions.sqlite3`: preserved state/counters; sessions have a
  24-hour lifetime and may now have expired. Do not dump payloads or reset the database.
  Pre-cycle backup: `output/20261004_mai_grounding/20261004_before_three_runs.sqlite3`.
- Frozen approved public test PDFs: main checkout `20260930_production-stress-test/sources/`.
  Their hashes match the saved final independent check. Use these exact three inputs
  for a subsequent controlled comparison rather than silently changing coverage.
- Same-input local direct-provider baseline:
  `output/playwright/20260930_renewed_acceptance/runs/quality-13-guinea-quote-selection/`.
- Historical deployed Render baseline in sibling worktree:
  `../review-quality/output/playwright/20260910_guinea_quality_3904935_1041/`.
- OS-temp task folder `cpf-fcv-renewed-acceptance-20260930/`: CA bundle and private
  session handoffs/logs. Live identifiers are intentionally absent from this document.
  Prefer existing sanitized evidence; never print tokens, rejected drafts or whole logs.

## 7. Resume workflow: planned, not yet implemented

1. Inspect Git and the safe saved findings. Trace `extraction.py`, `evidence_builder.py`,
   `source_grounding.py` and `review_engine.py`. Reproduce adjacent-table baseline,
   target, unit and footnote association errors with synthetic rows before changing
   behavior. Preserve source identity and page coordinates. Prefer the smallest
   generic source-preserving repair; do not patch Guinea's numbers into the app.
2. Investigate `mai_research.py`, `public_research.py` and `research_controller.py`
   separately using cached public originals. Test topical coverage, publisher/date
   diversity, historical versus current events and packing loss. Determine whether
   retrieval, selection or retained-budget packing causes missing topics. Existing
   caps are not to be raised automatically. Surface incomplete coverage accurately.
3. Check `validators.py`, `follow_on.py`, recommendation targeting and the prompts
   for unsupported absence/annex claims, source attribution and assistant amplification.
   Prove each targeted mechanical repair with a failing synthetic fixture; do not
   label prompt instructions alone as a verified semantic fix.
4. Run only relevant provider-free tests, then required CI/smoke verification for
   changed behavior. Useful entry points are `test_extraction.py`,
   `test_source_grounding.py`, `test_reference_resolution.py`, `test_mai_research.py`,
   `test_mai_failure_reproduction.py`, `test_mai_desktop.py`, `test_follow_on.py`,
   `test_runtime_wiring.py`, `test_prompt_guardrails.py` and `test_smoke_mode.py`.
   Choose the subset justified by the actual change, not every test by default.
5. Build a source-verified acceptance checklist covering table facts/units, existing
   provisions, historical/current attribution, research breadth, suitable edit
   targets, all drivers/shifts and assistant consistency. Reuse saved benchmarks.
6. Only after provider-free repairs and exact-runner smoke preflight pass, request
   a fresh bounded live allowance. The current handover does not approve it. Compare
   exact frozen inputs and verify both analytical claims and rendered exports. A
   completed assessment, longer prose or passing CI does not establish accuracy.

Country-general reliability, hosted restart/restore and operational acceptance
remain additional requirements after Guinea factual acceptance.

## 8. Runtime, workstation and hosting

The two verified temporary local service processes were stopped on 5 October;
SQLite and all evidence were preserved. No server was started during this handover.
Do not reuse old process IDs, browser tab indexes or tool-session IDs. Check actual
process/listener state before any future startup or cleanup.

Reuse existing runtimes: mAI app/auth environment
`C:\Users\wb559324\mAI_Factory\.venv\Scripts\python.exe`, and provider-free test/QA
runtime `C:\WBG\Python313\python.exe`. The mAI venv lacks pytest. Standalone QA
scripts must prepend this worktree's `src`; an installed editable package may point
elsewhere. Pytest already uses `src` via `pyproject.toml`.

`rg.exe` and local Ruff are blocked by Windows Application Control. Use scoped
`git ls-files`, `git grep`, Get-ChildItem and Select-String; rely on CI for lint.
PowerShell is constrained; use supported cmdlets or Python with `-X utf8` for Unicode.
Temporary-directory permissions affected two registry tests; both passed in a fresh
repository-local base directory. Do not rerun passed tests without new reason.

Before a future authorized startup, verify the existing task CA bundle and read
the shared mAI guide. From this worktree, the local configuration is:

```powershell
$env:MAI_TEAM_NAME = 'GTFS1'
$env:RESEARCH_PROVIDER = 'mai_google'
$env:SSL_CERT_FILE = Join-Path $env:TEMP 'cpf-fcv-renewed-acceptance-20260930\20260930_trusted_ca.pem'
& 'C:\Users\wb559324\mAI_Factory\.venv\Scripts\python.exe' -u scripts/20261004_run_mai_desktop.py
```

The runner authenticates and starts loopback port 58423; it does not submit an
assessment. Its default research provider is institutional, so set `mai_google`
explicitly. Do not use startup as permission for an API-backed review or assistant
request. Tokens stay in the existing Desktop auth flow, never in source/instructions.

No CPF app is hosted on Posit and no Posit CPF viewing link exists. Both publishing
accounts were verified in the shared setup guide, but server Python maximum 3.11.9
versus app >=3.13, mAI Application/ACN approval, durable single-instance storage,
worker lifecycle, backups/recovery and actual access acceptance remain unresolved.
Do not lower runtime requirements without testing or host Desktop credentials.
Internal mAI search entitlement/endpoints are still unverified; no intranet search
API call or internal-document retrieval occurred. Public Google research does not
resolve permission-aware internal retrieval.

Public Render remains a separate historical deployed version; its last verified
release in project records is `992c35a`, not rechecked during this handover. No new
deployment, policy approval or spending approval follows from updating these files.

## 9. Suggested next-session prompt

Continue CPF FCV Reviewer production readiness in the worktree above. First read
this 6 October handover, then follow its reading order and verify Git state. Use
provider-free diagnosis and synthetic reproductions for table interpretation,
research breadth and report/assistant consistency. Preserve strict evidence checks,
quotas, original outputs and the separate stable Screener. All three full runs are
used; do not make another live model/research/assistant call without fresh approval.
Do not merge or deploy. Reuse completed setup and successful checks.
