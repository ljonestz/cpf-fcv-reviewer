# Review schema diagnostics validation

Date: 2026-09-02
Branch: `fix/guinea-production-fixes`
Code commit: `67ab97c`
Validation type: provider-free failure-diagnostics and schema-guidance validation

## Methodology

The investigation used the previous paid run's terminal event and Render log, then traced
the two-attempt review-generation path locally. The historical record establishes that
both model responses failed `ReviewDraft` validation, but the exact invalid field cannot
be recovered because the second Pydantic error was previously propagated without a safe
field-level record. No attempt was made to rerun the unchanged deployed build.

The fix was tested in layers:

1. Reproduce first- and second-attempt Pydantic failures with synthetic invalid payloads.
2. Preserve only bounded, allowlisted field/index paths and normalized issue types.
3. Reject raw validation messages, rejected inputs, model identifiers, document text, and
   unknown field names from emitted events and server logs.
4. Expose locally enforced narrative, assessment, evidence-ID, and locator requirements in
   both the provider-visible JSON schema and the versioned review prompt.
5. Run focused tests, the complete provider-free suite, Python compilation, and whitespace
   validation.

## Result

Commit `67ab97c` adds a terminal `review_schema_invalid` category after exactly one retry.
Its diagnostics retain the attempt number, total issue count, and a bounded list of
allowlisted locations plus normalized types. The browser receives only the existing
generic failure message, durable session state stores only the failure code, and no model
output or document content is retained.

Known model-level validators are normalized to `gap_locus_required`,
`assessment_evidence_required`, or `document_coordinate_required`. Unknown validators
remain the generic `value_error` type. The JSON schema and review prompt now tell the
provider about nonblank narrative and evidence strings, conditional gap/evidence
requirements, and valid target-locator coordinates before generation.

## Verification evidence

- Focused review-schema/contracts/prompt/failure suite: 250 passed.
- Final targeted locator and redaction regression: 4 passed.
- Complete provider-free suite: 1,177 passed in 106.46 seconds.
- Python `compileall`: passed.
- `git diff --check`: passed.
- Anthropic SDK schema-transform regression: passed as part of the suite; the installed
  SDK preserved the new descriptions in the provider-visible transformed schema.
- Independent code review: no critical findings; the remaining locator-guidance finding
  was resolved and covered by tests.
- Ruff and Black are not installed, so those optional checks were unavailable.
- Paid API calls: zero.

## Limitations and next gate

This change makes the next failure diagnosable without retaining sensitive model or
document content; it cannot reconstruct the exact field from the historical run. It also
reduces recurrence risk by moving hidden validation constraints into provider-visible
guidance, but provider acceptance is not established until the exact commit is deployed
and tested.

Next, deploy the exact code commit, verify `/health` reports that release, and perform
static page checks. A further paid Guinea quality run should occur only after those gates
pass and with explicit authorization. Do not rerun deployed commit `361fe8c`.
