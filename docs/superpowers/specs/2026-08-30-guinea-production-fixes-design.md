# Guinea Production Fixes Design

## Goal

Fix the defects found during the live Guinea finalization run without changing the review architecture or adding dependencies.

## Design

- DOCX export will pass no hydrated referrals because `build_docx` does not render them. This removes the failing lookup from the export path while preserving the validated result and evidence checks.
- Review validation will reject institutional referral IDs that are not present in the loaded registry bundle, allowing the existing single repair attempt to remove or correct them before a result is accepted.
- Review validation will reject supplied evidence IDs embedded in user-facing narrative. Evidence references remain in the structured `evidence_ids` fields and render through the existing evidence components.
- The policy guardrail will treat assertions that a country is or is not on an FCV list as an unsupported official classification.
- Review and repair prompts will require calibrated trend language when current evidence does not directly establish a direction of change.
- The research limitation will use singular/plural agreement, and the holding estimate will use a singular label when its lower and upper bounds are both one minute.

## Error handling

The export route retains its existing safe 409/500 responses. It will log unexpected DOCX construction failures with the assessment ID so future production-only failures are diagnosable without exposing details to the browser.

## Verification

Each behavior receives a focused regression test that is observed failing before production changes. After focused tests pass, run Ruff and the complete pytest suite. Deploy the branch commit to Render and repeat the Guinea export and visible-result checks.
