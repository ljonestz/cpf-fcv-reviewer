# Paid-result follow-up implementation plan

**Goal:** Correct the reproducible source-qualification and presentation defects
identified in the October 3 accepted Guinea result without a further paid run.

**Architecture:** Reuse the existing research limitation, policy validator, review/
repair prompts and rendering functions. Preserve schema, source verification,
provider-call ceilings, quotas and historical output. No country-specific rewriting
of model text or new semantic-checking service.

**Acceptance basis:** The owner approved proceeding from the findings and next steps
in `docs/validation/2026-10-03-quote-selection-paid-acceptance.md`. This continues the
existing isolated repair branch; deployment and paid calls are outside this step.

- [ ] Reproduce the unsupported recency wording and missed list-status construction
  with focused tests in the existing research/validator suites.
- [ ] Make the reduced-evidence notice name source dates and assessment date without
  claiming that a two-year admission window establishes current conditions.
- [ ] Close the observed classification-pattern gap using the existing validator.
  Preserve verification grade and reduced-evidence qualification in repair support.
- [ ] Put a compact source-faithfulness check near the start of review/repair prompts:
  projections versus actuals, source ownership, existing provisions, conditional
  proposals, and consistency of summary with detailed analysis. Test prompt contracts
  and payload transport; these tests cannot prove future model compliance.
- [ ] Correct neutral driver labels, duplicate page coordinates and paragraph grouping
  in existing browser/Word functions. Presentation agent owns those files and tests.
- [ ] Run targeted tests, provider-free smoke, then the required full CI. Render the
  saved accepted result into new ignored files and inspect screenshots/Word pages.
  Retain its original factual defects visibly as a historical layout fixture.
- [ ] Inspect diffs, record exact results and remaining limits, commit/push to draft
  PR 39. No paid retry, merge, quota reset or hosting change.
