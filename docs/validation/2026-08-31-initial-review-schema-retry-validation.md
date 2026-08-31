# Initial review schema retry validation

Date: 2026-08-31

## Scope

This record covers the bounded recovery for an initial provider-generated `ReviewDraft`
that fails local Pydantic validation. It contains no raw provider output, document text,
credentials, corrections, or live assessment identifiers.

## Failure evidence

The authorized Guinea run on deployed commit `9816de4` completed extraction, source
resolution, current-country research, evidence building, and mapping. Initial review
generation then raised `ValidationError` and emitted safe failure code `review_failed`.
Application validation and repair were not reached.

The provider-facing JSON Schema does not encode every custom or cross-field Pydantic
validator in `ReviewDraft`. The exact failed field was not safely logged, so the fix does
not assume truncation or relax any field requirement.

## Implementation

| Item | Verified state |
|---|---|
| Initial retry | At most one additional model call after the first `ValidationError` |
| Scope | Initial `ReviewEngine.review()` generation only |
| Reused context | Existing bounded evidence, stage, detail, and review-focus payload |
| Diagnostics | At most 25 issues and 8 location parts per issue; known schema fields, bounded numeric indices, and constrained error types only |
| Untrusted locations | Unknown string keys become `unrecognized_field` |
| Fail-closed boundary | A second validation failure propagates; non-validation errors are not retried |
| Prompt boundary | Diagnostics are explicitly untrusted and cannot be echoed into user-facing content |
| Code commits | `003acfb` and `1ba44bf` |

## Test-first evidence

- RED: initial validation-recovery tests failed because the first error propagated and the
  prompt lacked the retry contract; unrelated-error tests already passed.
- GREEN: focused review-engine and prompt tests passed, 99 tests before security review.
- Security RED: a malicious extra-field key appeared verbatim in retry diagnostics.
- Security GREEN: the key was replaced by `unrecognized_field`; 100 focused tests passed.
- Provider-free smoke: 34 passed in 1.25 seconds.
- Complete pytest suite: 1,069 passed in 15.51 seconds.
- Python compilation: 75 files compiled successfully without writing bytecode.
- `git diff --check`: passed.
- Ruff: unavailable because the module is not installed in this environment.

The first sandboxed full-suite attempt produced only Windows temporary-directory
`PermissionError` setup failures. Re-running the identical provider-free suite with a
normal local pytest temporary directory produced the clean 1,069-test result above.

## Review

The spec-compliance review approved the bounded implementation. Code-quality review
identified arbitrary Pydantic location keys as untrusted input; commit `1ba44bf` added
schema allowlisting, bounds, prompt hardening, and a malicious-key regression test. The
subsequent code-quality re-review approved the complete implementation.

## Deployment

The Render-configured deployment branch points to tested code commit `1ba44bf`, and
Render reported that exact commit live. The feature branch and `main` additionally include
subsequent documentation-only commits. `/health` returned HTTP 200 with release `1ba44bf`,
and the public page returned HTTP 200 with the assessment form present.

No paid or provider-backed assessment was run after deployment.

## Remaining acceptance limitation

One separately authorized Guinea quality run is still required to establish provider
acceptance. It must capture full-page browser screenshots, inspect the rendered summary
and detailed output, and download and inspect the DOCX. Until that succeeds, the
prototype is not production-ready.
