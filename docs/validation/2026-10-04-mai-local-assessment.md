# Local mAI assessment acceptance - 2026-10-04

One owner-authorized local Guinea CPF/RRA assessment used mAI Desktop DEV and
Sonnet 4.6. Application code was `05772b7`, with documentation HEAD `cea43aa`.
The assessment **failed evidence validation**. No accepted findings, Word exports
or follow-on assistant response were released. No second assessment was started.

## Method and result

Reused the existing Edge acceptance runner, with a separate exclusive-create
reservation for this single local assessment. The previous direct-provider ledger
was not changed. The exact runner first exercised synthetic uploads, results,
assistant, refresh, both Word downloads and mobile views: **11/11 checks passed**,
with no JavaScript, console or resource errors. Its synthetic mobile screenshot
was inspected. Browser cleanup was unusually slow, but the runner subsequently
returned normally with exit 0. The task-owned smoke server was then stopped.

The real run used the existing public `guineacpf.pdf` and `guinearra.pdf`, decision
review stage, and the loopback service on port 58423. Health reported a live worker
and persistent SQLite storage. The runner exited 1 after about 367 seconds.
The failure screenshot was saved and visually inspected.

Authentication, model requests and structured-response parsing worked far enough
to produce a draft and attempt the bounded repair. No authentication, HTTP or
schema-parsing failure is recorded in the terminal diagnostics. The initial
validation reported 17 issues. Repair reduced these to six but could not clear
the grounding checks:

| Diagnostic | Before repair | After repair |
| --- | --- | --- |
| CPF response not grounded in its cited text | Present; two quote mismatches | Present; two quote mismatches |
| Unknown assessment evidence reference | Present | Present |
| Unknown evidence reference | Present | Cleared |
| Recommendation target excerpt mismatch | Two mismatches | Two mismatches |

These are safe diagnostic categories and counts, not a reconstruction of the
rejected narrative. Raw failed model output was not retrieved. The evidence gate
withheld the assessment as designed; this does **not** establish acceptable
end-to-end reliability or factual quality.

The institutional research path produced zero candidate/accepted sources and
used the document-led fallback. It therefore did not establish current-context
coverage comparable to the direct-provider search route. This is a separate
limitation from the quotation/reference validation failure.

## Evidence and usage

Ignored local evidence:
`output/playwright/20261004_mai_acceptance/`.

- `browser/20261004-smoke-01/`: synthetic status, screenshots, accepted fixture
  JSON and two Word downloads.
- `runs/20261004-mai-guinea-01/`: intake/progress/failure screenshots, health,
  browser status and `20261004-safe-diagnostics.json` with source hashes.
- `20261004-mai-assessment-reservation.json`: one local assessment reservation.

SQLite counters independently show one review admission and no assistant
admission. No direct Anthropic call, deployment, quota reset or internal-document
retrieval occurred. Full-run token usage was not captured by this adapter; no
exact token or dollar cost is claimed. The private assessment handoff remains in
the OS temporary directory, outside Git.

## Next gate

Investigate and reproduce quote selection, evidence references and target locator
generation with synthetic fixtures before another model-backed run. The code
offers optional source-selection tokens but still accepts model-authored literal
quotations; the safe diagnostics establish mismatches, not their exact cause.
Do not weaken the validation gate or claim a fix from prompt changes alone.
Research coverage needs a separately verified retrieval path. Hosted Application
access and the earlier production-readiness prerequisites remain open.
