# Initial review schema retry design

Date: 2026-08-30

## Problem and cause

The authorized Guinea run reached initial review generation, where Pydantic rejected the
provider response before application validation or repair. The provider-facing JSON
Schema does not encode every custom or cross-field `ReviewDraft` validator, so a response
can satisfy the exposed shape and still fail local validation.

## Approved design

- Retry initial review generation once, only after a first `ValidationError`.
- Reuse the existing bounded evidence, stage, detail, and review-focus payload.
- Pass only safe error locations and types; exclude messages, inputs, context, raw output,
  document text copied from errors, and assessment identifiers.
- Do not relax the schema, restart research, or retry unrelated errors.
- Propagate a second failure through the existing fail-closed `review_failed` path.

## Verification

- Test first-call failure followed by one successful retry.
- Test safe diagnostic shape, second-failure propagation, and no unrelated-error retry.
- Add a prompt contract test for the bounded `schema_retry` payload.
- Run focused tests, provider-free smoke, full pytest, compilation, and diff checks.
- Do not perform another paid quality run without separate authorization after deployment.

## Rejected alternatives

- Prompt-only reinforcement is less reliable for validators absent from JSON Schema.
- Schema relaxation or output normalization would weaken guardrails.
