# Output quality revision - 13 October 2026

## Acceptance state

The owner rejected the earlier Guinea outputs for poor narrative flow, missing
four-question coverage in the summary, shallow core findings and cluttered query
presentation. This record supersedes the editorial readiness conclusion in the
earlier same-day acceptance record. No additional paid assessment was run here.
The revision is not deployed and generated-content acceptance remains pending.

## Changes

- Four developed, evidence-linked findings carry the argument; each has a distinct
  concise summary. Schema 2.1 requires summaries; older saved results remain readable.
- The If/Then lens first identifies conditional adaptation wherever it appears in
  the CPF. Where materially missing, the prompt asks for a few relevant proposed
  conditions and corresponding adjustments, recognising existing provisions and
  preserving stage, evidence and sensitive-destination limits.
- Concise opening and diagnostic/Strategy connections; recommendations explain one
  principal concern and a feasible request rather than repeating the diagnostic.
- Intentional paragraphs and safe emphasis replace arbitrary four-sentence chunks
  and automatic bold leads. Summary recommendations occupy full-width sections.
- Word includes the four summaries and sources for detailed recommendations.
- Unsigned comments use plain headings/paragraphs, preserve material priorities and
  qualifications, and expand to fit the text. A query revision updates the comments
  without duplicating the draft. The input directly follows a short introduction;
  example links are removed and explanatory answers appear below the input.

## Verification

The initial focused regression set passed 85 tests. The broad local run found
outdated presentation/prompt assertions and an inherited invalid SSL_CERT_FILE;
1768 tests passed, 34 failed and one Windows Gunicorn test was skipped. Assertions
were updated to the approved behavior, not weakened safety rules. Rechecking the
seven affected test modules with a valid certificate bundle for that process passed
378 tests. Subsequent targeted schema/presentation checks and exact-head CI are
recorded in the PR. The final schema/coordinator checks passed 26 tests. The first
Linux CI run passed 1799 tests and caught seven old schema-version assertions in
two integration tests; these now check version 2.1 and nonblank summaries. No TLS verification was disabled or deployment configuration changed.

Provider-free Edge browser QA passed intake, all output tabs, comments refinement,
refresh restoration, explicit corrections/stale wording, mobile overflow checks
and two DOCX downloads. Desktop and mobile PNGs were inspected. Saved artifacts:
`output/playwright/20261013-output-quality-smoke3/` (ignored; synthetic content only).
The earlier browser launch imported an older installed checkout; the successful
server explicitly inserted this worktree's `src` and printed its module path.

A local check of the public Guinea CPF confirmed seven PDF pages. The text refers
to Annexes 1-4, but those annexes are not included in the supplied PDF. This supports
qualifying annex-dependent findings; it was not evidence of an extraction failure.

## Remaining acceptance

Synthetic screenshots demonstrate presentation and workflow, not analytical depth.
Inspect a fresh generated Guinea assessment before rollout, especially all four
questions, conditional scenario quality, concise summary, evidence qualifications
and practical ROC/OC recommendations. The second authorized paid assessment remains
unused. Real-run Word pagination is still unverified after the previously documented
Word COM startup failure. Internal hosting and public-prototype storage constraints
are unchanged. Do not describe this revision as production-ready until output
acceptance is complete.
