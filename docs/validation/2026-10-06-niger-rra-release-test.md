# Niger CPF plus RRA release test - 6 October 2026

## Outcome

One explicitly requested provider-backed Niger CPF plus June 2022 RRA assessment
was submitted at early drafting with in-depth detail on application release
`c525c9e384d00e76782f96fbc601a1ba0fc8c7df`. It failed after bounded repair.
The sanitized sequence was `repair_start` (`unknown_institutional_referral`,
issue count 1), `repair_failed` (same code/count), then `run_failed`
(`review_failed`). No second assessment or follow-on assistant call was made.
No successful result or Word export exists for this case.

This differs from ITS's original no-RRA `limited_mode_overclaim` failure and
from the successful no-RRA Niger run recorded separately. It exposes a distinct
referral-reference reliability issue; it does not establish that the limited-mode
hotfix regressed. Do not describe this CPF plus RRA case as passing or infer
blanket country/output acceptance from the earlier no-RRA success.

## Checks before submission

- Render deployment `dep-db2bpmeq1p3s73egfu8g` was live at the exact application commit.
- TLS-verified health, homepage and JavaScript checks returned HTTP 200.
- Local extraction through the application's actual diagnostic bounds read all
  81 RRA pages, 311,589 characters, without warnings. The publication month was
  June 2022. This proves local extraction, not successful server-side mapping.
- Provider-free smoke tests: 38 passed.
- The adapted early-drafting/in-depth Edge runner passed the complete synthetic
  result, assistant, refresh, mobile and two-Word-download flow, exit 0. Smoke
  screenshots were explicitly synthetic and are not Niger quality evidence.

## Browser-runner limitation and recovery

After the real POST returned 201, an added settings assertion failed because
Playwright's multipart request `post_data` was None for the larger real upload.
This was a local QA runner defect, separate from the application validation failure.
The active session was recovered using its scoped server request log and persisted
outside Git. No assessment was resubmitted. Browser recovery blocked all new review
submissions and captured the stopped screen. An initial recovery navigation waited
for network idle while a review stream was active; the next recovery used DOM-ready
navigation. The original session reached the same safe terminal failure.

Local ignored artifacts: `output/playwright/20261006-niger-rra-quality-1`
(intake/initial recovery), `output/playwright/20261006-niger-rra-recovery-2`
(recovered progress and `99-quality-failure-full.png`), and
`output/playwright/20261006-niger-rra-preflight-2` (synthetic browser evidence).
The intake, recovered progress and terminal PNGs were visually inspected.
Raw source documents, model output and live session identifiers are not in this record.

## Follow-up boundary

Current repair instructions already tell the model to remove unknown referral IDs
and preserve known ones. Repair accepts the model's referral tuple without a trusted
registry filter, so this mechanical correction is not guaranteed. A synthetic local
probe reproduces retained unknown IDs and loss of an approved original reference.
That probe does not reveal the real run's rejected values or establish its exact
model response. The recommended follow-up is registry-controlled removal of unknown
structured referrals while preserving approved original IDs and all unrelated content.
Implementation/design approval is pending; no application change or new deployment
was made in this validation session. A new paid trial is not automatically authorized
by this record.
