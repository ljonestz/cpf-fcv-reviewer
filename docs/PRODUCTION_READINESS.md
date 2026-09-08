# Production readiness — 2026-09-08

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
