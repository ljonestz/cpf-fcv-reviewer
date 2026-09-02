# Role-aware source coverage validation — 2026-09-02

## Scope and outcome

Provider-free validation passed for the role-aware source-coverage correction on
`fix/guinea-production-fixes` through code commit `24a8d22`. No deployment or paid model
run was performed. The stable FCV Project Screener was not changed.

The implementation uses the existing extraction, diagnostic-map, evidence, review, and
failure-handling components. It adds no dependency, provider stage, retrieval service,
account system, vector database, or frontend framework.

## Verified behavior

- The primary CPF/CEN remains the principal assessment lens.
- Up to ten accompanying package documents are fully re-extracted. Every retained package
  segment is supplied to the review within limits of 400 segments, 300,000 characters,
  and 160,000 estimated serialized-input tokens. The review fails closed with the safe
  package-coverage category if complete bounded processing is unavailable.
- A recognized RRA or equivalent diagnostic is fully extracted within its safety bounds
  and is never silently sampled. The diagnostic map uses known, nonempty representative
  citations to synthesize drivers, resilience sources, and key risks. It no longer must
  assign every page exactly once. One sanitized retry remains for schema-invalid output.
- Other contextual material is supporting input and may be summarized at a higher level.
- Structured evidence remains internal while reader-facing HTML and DOCX omit technical
  evidence registers. The streamed assistant and 20-message, 24-hour retention behavior
  are unchanged; correction/rerun remains secondary.

## Test evidence

- Focused nine-module source-coverage set: 341 passed in 15.19 seconds.
- Provider-free smoke suite: 36 passed in 3.23 seconds.
- Complete local suite: 1,170 passed in 54.07 seconds.
- Python compilation: passed.
- JavaScript syntax check: passed.
- `git diff --check`: passed before documentation update and is repeated at the final
  checkpoint.
- Ruff was unavailable in the existing environment and was not installed for this cycle.
  The implementation-plan marker command selected no tests because the repository has no
  smoke marker; the authoritative `tests/test_smoke_mode.py` suite above passed.

## Browser and DOCX evidence

A deterministic, provider-free smoke server was started from current code commit
`24a8d22`. Nine unique full-page PNGs were saved and visually inspected: multiple-package
intake, holding/progress, Five-minute readout, Detailed analysis, streamed assistant,
refresh-restored four-message conversation, secondary correction/rerun, safe package
coverage failure, and mobile summary. Live DOM checks confirmed two assistant requests,
four restored messages, and the exact safe package-failure text. The mobile view had no
horizontal overflow. Full-page capture stitching introduced repeated bands at some image
joins; live DOM counts confirmed these were capture artifacts rather than duplicate page
content.

Accepted artifacts are in the external validation folder:

`C:\Users\wb559324\.codex\visualizations\2026\08\31\01a05887-3e91-72e2-8c8a-16ed5312d691\20260902_task5_role_aware_source_coverage_smoke\`

The accepted PNG filenames begin `20260902-r6-01` through `20260902-r6-09`. A fresh
current-HEAD DOCX, `20260902-r6-10-smoke-full-detailed-note.docx`, was exported from the
deterministic application. It is a valid OOXML ZIP with 19 parts, 35 paragraphs, 12
headings, no tables, and one section. Expected review content was present; technical
evidence-register labels, sample raw evidence IDs, and assistant transcript labels were
absent. LibreOffice was unavailable, so DOCX page rendering and visual acceptance were not
claimed. The workspace-dependency discovery call also failed to return and was stopped;
the repository's installed `python-docx` support was used for structural inspection.

No uploaded documents, raw provider output, assistant conversation, secret, live
assessment identifier, PNG, or DOCX is tracked in the repository.

## Commit checkpoints

- `20adf15`, `bdaa38e`: thematic representative RRA references and smoke correction.
- `93b7666`, `f538434`: full bounded package extraction and warning synchronization.
- `087b3cc`: complete retained package evidence in review input.
- `568d4f4`, `24a8d22`: role-aware prompt, input budget, safe failure mapping, and retry
  budget guard.

Each implementation checkpoint passed independent specification and code-quality review.

## Deployment checkpoint

Deployment and provider validation have not run for this correction. The next authorized
step is to push the final documentation commit, then stop for separate approval. After
approval, verify the exact deployed release with health/static checks before at most one
paid Guinea assessment. Never rerun unchanged code.
