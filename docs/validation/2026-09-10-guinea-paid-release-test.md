# Guinea paid release test - 2026-09-10

## Outcome

Technical end-to-end pass on deployed application `39049356713df8928edaf1434d812c2c58c0b95d`; substantive acceptance remains qualified. One user-authorized paid assessment and one assistant follow-up were submitted using the approved Guinea CPF and RRA PDFs. No second assessment was submitted.

## Verification

- Existing release CI: 1,610 provider-free tests passed, including real Gunicorn.
- Immediately preceding synthetic runner preflight passed: eight screenshots, assistant restoration and both DOCX downloads.
- Verified TLS health check confirmed the exact deployed release, volatile storage and in-process queue. Process-local trust combined certifi with Windows trusted certificates; certificate verification remained enabled for upload.
- Paid runner exited 0: `BROWSER_QA_PASS mode=quality screenshots=8 assistant_messages_restored=2 docx=2`.
- Pipeline emitted `run_complete` with one repair. Repair codes: `unknown_institutional_referral`, `prohibited_policy_language`. Advisory codes: `missing_current_context_support`, `stage_length_overreach`.
- Result metadata: diagnostic publication June 2023, cover provenance on physical page 1. The month is encoded as `2023-06-01`; this does not establish the first day as publication day.
- Final result contains three priorities and three matching summary links, five RRA driver assessments and four strategy assessments. This final-state check alone does not establish the pre-repair priority count; preservation is separately covered by regression tests.
- Current evidence tier is reduced: two evidence items across Africa Center and International IDEA.
- PNG contact sheet and enlarged summary inspected; report text read directly from DOCX. Automated runner checks cover downloads, assistant restoration, mobile overflow and browser errors. No claim of exhaustive Word pagination review.

## Remaining quality concerns

The output uses the correct RRA publication month, but recommendations still present detailed numerical targets and institutional actions as proposed firm commitments without clear feasibility qualification. Examples include TVET and SME jobs targets and specified IFC/MIGA actions. These require source checking and expert confirmation, not acceptance merely because structural validation passed.

A read-only source comparison found the proposed 50,000 TVET graduates by FY30 and 30,000 direct SME jobs by FY31 in neither supplied input. Their location under recommended action makes them proposals, but the firm wording and unexplained precision need correction. The report also overstates missing institutional roles: CPF physical pages 4, 6 and 7 already describe IFC/MIGA roles. The defensible gap is their connection to measurable, disaggregated youth outcomes and joint accountability. No RRA consultation/publication conflation or misapplication of the Sudan third-party example was found.

Research breadth remains limited. Historical reporting is used to characterize the present governance trajectory; this run does not establish a comprehensive September 2026 current-context assessment. Recommendation length remains an advisory issue. The test supports supervised expert use, not blanket factual acceptance.

## Local artifacts

Ignored directory: `output/playwright/20260910_guinea_quality_3904935_1041/` in the `review-quality` worktree. Contains eight PNGs and `08-quality-five-minute-readout.docx` / `08-quality-full-detailed-note.docx`.

Synthetic preflight: `output/playwright/20260910_paid_preflight_1036/`.

Source documents, generated report text, assistant conversations and live identifiers are not committed. Live identifier handoff remains outside the repository. No measured monetary cost is available. Storage is volatile; a restart loses the live review. Documentation follow-up should use `[skip render]` to avoid an unnecessary restart.
