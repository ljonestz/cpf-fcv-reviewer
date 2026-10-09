# Large-package local quality run (2026-10-08)

## Attempt 1: failed before drafting

- Build: `feat/large-package-coverage` at `ea6f51a`, served locally with the existing
  quality runner and live service configuration (review model `claude-opus-5-5`).
- Input: the public Guinea CPF FY18-23 (primary), BOSIB and the Performance and
  Learning Review (package), and the Guinea RRA (context); `decision_review`.
- Outcome: `run_failed` with `review_failed` after 196 seconds. Safe event history:
  extract, resolve_sources and research completed (research `reduced`, zero accepted
  claims); `package_plan` reported 2 package documents supplied in full and 1 context
  document summarised; map completed without a diagnostic; review failed with
  `BadRequestError` (HTTP 400).

## Diagnosis (no further quality run)

1. A minimal schema probe returned "The compiled grammar is too large": constrained
   decoding on `claude-opus-5-5` rejects the `ReviewDraft` schema that
   `claude-sonnet-4-5` accepted. `DiagnosticMap` and `DocumentDigest` were accepted.
   Fix: the gateway falls back to a schema-in-prompt request for that output type and
   validates the reply locally; invalid replies raise `ValidationError` and use the
   existing single schema retry.
2. A provider-free check showed the PLR also matches the RRA detector, so the combined
   search found two candidates and dropped RRA alignment (pre-existing behaviour). Fix:
   prefer a single match among the RRA and supporting-analytics uploads.
3. Research returned no accepted claims within seconds. The research path is unchanged
   on this branch; the cause was not established without a further paid call.

Provider-free suite after the fixes: 1,716 passed, one Windows Gunicorn skip. A second
quality run requires explicit authorization.

## Attempt 2 (2026-10-09, authorized): failed at validation

- Build: `3baeb0a`, same inputs and runner.
- Safe event history: research ran curated recovery (7 accepted) but ended
  `document_led` for insufficient coverage, and the knowledge-based readout was
  generated (6 themes); `package_plan` reported 2 package documents in full and the
  RRA identified as the diagnostic (no context documents left to summarise); map,
  review (schema-in-prompt fallback) and validate completed; `advisory_notice` 3 x
  `missing_current_context_support`; `repair_start` with `diagnostic_date_conflict`
  and `unknown_institutional_referral`; `repair_failed` with
  `diagnostic_date_conflict`; `run_failed` `review_failed` after 540 seconds.
- Provider-free diagnosis: the uploaded RRA's provenance is June 2023 (cover). The
  supplied documents legitimately cite the earlier May 2017 RRA (CPF 3, PLR 6, and
  the 2023 RRA itself 17 dated mentions). With the full CPF and PLR now supplied, the
  review cited "the 2017 RRA", which the validator treated as a conflict with the
  June 2023 provenance; repair could not resolve it without mislabelling the 2017 RRA.
- Fix: dated diagnostic mentions are allowed when the same year (and month, where
  given) is stated verbatim in supplied document evidence. Digest paraphrases cannot
  attest a date; day precision and unattested dates remain conflicts.

Provider-free suite after the fix: 1,719 passed, one Windows Gunicorn skip.

## Attempt 3 (2026-10-09, authorized): interrupted during review

- Build: `cb5e092`, same inputs and runner.
- Safe event history: research `reduced` immediately after its first attempt;
  `package_plan` 2 package documents in full, RRA identified; map completed; review
  failed after 220 seconds with `APIStatusError` reporting HTTP status 200, which is an
  error event received mid-stream after the request was accepted (a provider-side
  interruption such as `overloaded_error`). The SDK does not retry these.
- Fix: the gateway retries transient failures, including mid-stream errors, up to two
  times with 15- and 45-second backoff, and logs the safe API error type. Invalid
  requests (HTTP 400) are not retried.

Provider-free suite after the fix: 1,722 passed, one Windows Gunicorn skip.
