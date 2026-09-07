# Limited-mode validation diagnosis - 2026-09-07

Base release: `3bf4f08`, verified against GitHub main. No deployment or paid calls.

## Findings

- `_downgrade_to_limited_framing` adds an application-owned warning containing
  "without RRA alignment". `result_text` scans limitations; the abstention pattern
  does not exempt this wording. `_preserve_research_limitation` restores it after
  repair. This deterministically causes `limited_mode_overclaim`, independently
  of any model-authored overclaim.
- Contrary to the earlier handover, both review and repair prompts already contain
  explicit limited-framing instructions. The failed-run artifacts do not establish
  the exact model-authored wording.
- The schema retry catches and discards the final Pydantic details. The actual
  Guinea mapping failure cannot be inferred from its generic failure category.

## Change

Use the explicit abstention "RRA alignment was not assessed" in the runtime-owned
warning. Preserve the downgrade, limitation, validator, schema, and retry budget.
Log final mapping schema failure via the existing bounded sanitizer: allowlisted
field/index paths and normalized issue types only, without exception text,
rejected values, raw model output, or tracebacks.

## Verification

- Extended mapping-downgrade test through caveat restoration and validation:
  failed with `limited_mode_overclaim` before the wording fix, then passed.
- Extended second-schema-failure test to require sanitized diagnostics and prove
  secret values, unknown field names, and tracebacks are absent: failed before
  logging was added, then passed.
- `python -m pytest tests/test_runtime_wiring.py tests/test_validators.py
  tests/test_smoke_mode.py -q -p no:cacheprovider`: 308 passed, two Windows
  temporary-directory setup errors. The two affected tests passed on an isolated
  unsandboxed rerun: 310 relevant tests passed in total.
- Test process used certifi's CA bundle because inherited SSL_CERT_FILE was invalid;
  no TLS verification was disabled and no provider calls were made.
- Ruff reports pre-existing import sorting in runtime and tests, and a pre-existing
  long assertion in the runtime tests. No unrelated formatting changes made.

## Assessment of handover options

A (diagnose mapping) remains appropriate, using sanitized errors rather than raw
output. Do not loosen schema constraints without evidence. B (global replacement
of alignment language) is unnecessary for the proven failure and could change the
meaning of findings. C (advisory overclaims) would weaken a real safety check.
The narrower correction fixes the application's contradictory caveat.

## Remaining acceptance work

Obtain authorization for a bounded map-only Guinea diagnosis; reuse exact runtime
page payload construction and inspect only sanitized Pydantic details. A subsequent
approved deployment needs a full Guinea completion, rendered readout, and DOCX
check. These local tests do not establish live completion or production readiness.
The original handover remains uncommitted because it includes live assessment IDs.
