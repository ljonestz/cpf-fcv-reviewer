# Production readiness

## Deployed pilot - 2026-09-10

Application release **3904935** (PR 33) is live and health-verified. Diagnostic-date,
priority-repair, extraction and worker fixes are deployed; the dashboard now uses
16 gthread threads. Candidate tests and merged-release CI passed, including real
Gunicorn. No provider-backed quality run was performed for this release.

The owner wants the site open without passwords or institutional sign-in. The paid
instance still uses volatile storage. Readiness remains supervised expert use with
public or approved non-sensitive documents; proposal feasibility and research breadth
require expert judgment. See the [release record](validation/2026-09-10-pilot-release.md).
The observations below describe earlier checkpoints.

## Current follow-up - 2026-09-10

The owner continues a small supervised public-document pilot and has deferred access
protection. Render now uses a paid 0.5 CPU / 512 MB instance, but the live health check
still reports volatile storage and an in-process queue. Live commit is 2fc2b77; its
explicit start command still selects four request threads. The upgrade alone has not
deployed the review fixes or enabled restart-safe storage.

The candidate review branch contains diagnostic-date provenance and priority-preserving
repair, plus Claude's operational changes under focused review. Its gthread mitigation
uses 16 threads; the dashboard start command must also be updated at release. Do not
interpret render.yaml's disk, SQLite path or auto-deploy setting as observed live state.

See the [operational follow-up](validation/2026-09-10-operational-followup.md) for verified
hosting, checks and remaining release steps, and the
[review-quality validation](validation/2026-09-10-review-quality-followup.md).
Proposal feasibility and cross-country research breadth still need expert acceptance.
No new paid assessment, merge or deployment is recorded by this follow-up.

## Historical readiness assessment - 2026-09-08

## Decision
Suitable for a supervised expert pilot with public or approved non-sensitive documents.
Not yet accepted for routine operational production. This is a quality and service
readiness assessment, not a request for additional policy safeguards.

## What has passed
- Current application release `27ef3aa` (PR30); Render and health verified.
- 1,527 provider-free tests passed.
- Live Guinea review completed with source-backed current context, assistant restoration,
  eight screenshots and both Word downloads.
- Five observations from two URLs, one originating publisher; reduced coverage disclosed.
- Recommendations connect political reporting to CPF adaptive management, PAGL2/local
  governance delivery and staffing/tools. Word limits no longer block useful output.
- Native Word verified the final top-edge running banner across all 12 pages of the
  three-page short readout and nine-page detailed report, using one editable header paragraph.

## Remaining work, in priority order
1. Correct RRA date provenance: the output says September 2022, but the uploaded cover
   says June 2023. Establish whether identification or generation introduces the error,
   add a local regression, and preserve the verified date through the review.
2. Check proposal wording against evidence: proposed PAGL2, IFC/MIGA and third-party
   delivery changes must be framed as options for expert validation, not established
   feasible arrangements or agreed commitments.
3. Broaden quality acceptance across countries and source types. One successful Guinea
   run with one publisher does not establish consistent research breadth or parity with
   research-enabled native LLM review. Use local/replayed checks before paid validation.
4. Before operational hosting, use the existing durable session-store configuration and
   verify restart recovery. The current public free-tier service explicitly uses volatile
   storage; its nominal 24-hour review lifetime does not survive service restart.

Keep this proportionate: no major redesign is established as necessary. The date issue
and proposal framing are bounded quality fixes; source coverage needs observed acceptance,
and durable hosting uses the existing configuration path. Do not add more fatal checks
for presentation preferences. No additional model runs are authorized by this document.

## Evidence and artifacts
See [live acceptance](validation/2026-09-07-live-release-acceptance.md) and
[project status](PROJECT_STATUS.md). Earlier failure records remain historical evidence.

The full readout and screenshots are saved locally under
`.worktrees/current-source-finalization/output/20260907_guinea_quality_live_9f787f4_202609072036/`:
- `08-quality-full-detailed-note.docx`
- `08-quality-five-minute-readout.docx`
- `03-quality-summary-desktop-full.png`
- `04-quality-detailed-desktop-full.png`
- assistant, refresh and mobile PNGs from the same run.

These artifacts contain model-generated analysis, including the known date error. They
are not committed to Git. The full readout has 89 paragraphs and both Word files passed
ZIP/OOXML checks. Native-chat parity remains unmeasured.
