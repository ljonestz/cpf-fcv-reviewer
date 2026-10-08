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
