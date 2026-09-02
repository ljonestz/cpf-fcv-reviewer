# Guinea production-quality validation on 361fe8c - 2026-09-02

## Scope and outcome

One explicitly authorized provider-backed Guinea assessment was submitted to the public
CPF FCV Reviewer on deployed commit `361fe8cab5914c44ad30e3408536a06712db512e`.
The run used only the approved public Guinea CPF and RRA PDFs, selected the finalization
stage, and did not include accompanying package documents.

Extraction, current-country public research, evidence building, full-RRA mapping, and
drafting completed. The assessment then failed closed before results with reader-safe text
`Review stopped: The review could not be completed.` The terminal safe event was
`run_failed: review_failed`. Render recorded `error_type=ValidationError`, no status code,
and no cause chain. No result, assistant exchange, correction interaction, mobile result,
or DOCX was produced. Provider acceptance for the role-aware redesign therefore remains
unestablished, and the unchanged deployment must not be rerun.

## Pre-submission gate and run control

- Render deployment status was `live` for exact commit `361fe8c`.
- `/health` returned HTTP 200 with `status=ok`, the exact full release SHA, in-process
  queueing, and volatile prototype storage.
- The root page returned HTTP 200 immediately before the submitted attempt.
- An earlier runner start encountered a non-200 landing response and exited before upload,
  screenshot creation, marker creation, or submission. After the no-cost gate passed, the
  same fresh attempt continued; this did not consume a paid assessment.
- The attempt runner wrote its unique submission marker before clicking submit and reported
  exactly one submission.
- The original review page remained open throughout the active run. Three separate fresh
  keep-awake pages returned HTTP 200 at approximately four-minute intervals. No recurring
  traffic was created after the run ended.

## Safe failure and resource evidence

Render logs for the run window contained one current terminal record:

`review_run_failed error_type=ValidationError status_code=none cause_chain=none failure_code=review_failed`

No matching provider, timeout, OOM, or HTTP 5xx event was present in the run window.
Memory rose to approximately 171 MB against a 536.9 MB limit. CPU remained well below its
0.15 CPU limit. The failure is therefore not attributable to Render resource pressure.

No safe `repair_start` or `repair_failed` event was available from the retained evidence.
The validation record does not speculate about schema fields or model content that were not
exposed through the approved safe categories.

## External artifacts

Artifacts are stored outside the repository in:

`C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\20260902_role_aware_quality_361fe8c\`

The folder contains a fresh runner, one submission marker, and six unique full-page PNGs:

- intake: `20260902_roleaware_quality_361fe8c_01_intake_full.png`
- initial holding: `20260902_roleaware_quality_361fe8c_02_holding_initial_full.png`
- research: `20260902_roleaware_quality_361fe8c_03_progress_research_full.png`
- mapping: `20260902_roleaware_quality_361fe8c_05_progress_mapping_full.png`
- drafting: `20260902_roleaware_quality_361fe8c_06_progress_drafting_full.png`
- failure: `20260902_roleaware_quality_361fe8c_failure_full.png`

Pillow opened all six PNGs successfully. They are nonempty, RGB, and byte-distinct. The
intake image is 1440 by 1443 pixels; holding and progress images are 1440 by 1199 pixels;
the failure image is 1440 by 1304 pixels. The local image-viewer helper was blocked by
Windows Application Control, so human visual inspection could not be completed and is not
claimed. No DOCX was produced, so structural or rendered DOCX inspection was not possible.

No uploaded document, raw model output, assistant conversation, secret, live assessment
identifier, screenshot, marker, or DOCX is tracked in the repository.

## Acceptance implications

The run establishes that the deployed implementation can complete full-RRA mapping and
reach drafting without a diagnostic-coverage failure. It does not establish narrative
quality, thematic citation quality in the final result, CPF primacy in the final narrative,
source traceability in a completed result, assistant streaming/persistence, secondary
correction placement in a completed review, mobile result behavior, or DOCX quality.

Do not rerun commit `361fe8c`. A further paid attempt requires root-cause evidence, a new
deployed fix cycle, provider-free regression and smoke validation, exact-release health
checks, and separate user authorization.
