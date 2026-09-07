# Limited-mode validation diagnosis - 2026-09-07

Base release: `3bf4f08`, verified against GitHub main. No deployment or paid calls at the time of this record.

## Later outcome

The correction described here subsequently shipped in PR #21 and release `63b16da`.
The authorized map-only probe passed, and the full Guinea acceptance reached
`run_complete` without `limited_mode_overclaim`; see `docs/validation/2026-09-07-guinea-acceptance.md`.

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

## Authorized map-only probe preparation

`20260907_diagnose_diagnostic_map.py` defaults to dry-run and reuses runtime page
items, extraction limits, schema, and sanitized retry details. Explicit execution
is capped at two calls with SDK transport retries disabled. Provider-free fake-
gateway verification confirmed the two-call cap and sanitized retry payload;
Ruff passed. Real Guinea preflight extracted 101 text pages and estimated 112,867
input tokens, within the 160,000-token runtime bound. No provider calls occurred:
the local process and checked local configuration had no Anthropic API key.
Paid execution is authorized but awaits the maintainer's credential location.

## Authorized map-only result

The authorized provider probe completed with `claude-sonnet-4-5`: all 101
extractable RRA pages were supplied, yielding 16 valid thematic entries on the
first request. `validate_diagnostic_references` passed. One actual model request
was used, with transport retries disabled; no schema retry was needed. The probe
used the existing Render service settings in process memory, without saving or
printing credentials. Local SDK versions: anthropic 0.84.0, pydantic 2.12.5.

An earlier local attempt failed during SDK construction because of an invalid
inherited SSL_CERT_FILE, before any model request. A provider-free boundary test
confirmed this; the successful attempt used a valid CA bundle plus Windows trust
roots and an additional hard one-call guard.

The previous provider schema rejection was not reproduced. Do not infer that the
Guinea RRA is inherently unmappable, or relax its schema based on this result.
No full assessment, merge, or deployment occurred. Next acceptance step requires
approval: deploy the reviewed validation correction, verify the exact live commit,
and run one full Guinea review including rendered output and DOCX checks.
