# Full-RRA map reliability fix validation

Date: 2026-09-02

## Scope

This record covers the bounded diagnostic-map reliability correction implemented on
`fix/guinea-production-fixes` at code commit `095873b`. It does not contain uploaded
documents, raw model output, assistant conversations, credentials, secrets, or live
assessment identifiers.

## Diagnosis and correction

The configured structured-output path validates the returned JSON locally with Pydantic.
The Anthropic SDK version in this environment does not structurally enforce every local
schema keyword, including the diagnostic map's `maxItems` constraint; unsupported
constraints are represented as schema descriptions. The safe production record did not
expose the rejected output, so the exact field-level cause of the final Guinea
`ValidationError` is intentionally unknown.

The correction remains within the approved diagnostic-map design:

- the prompt targets 8-12 thematic entries, prohibits page-per-entry output, and permits
  up to 20 entries when needed to keep distinct material drivers separate;
- each returned entry is instructed to use exactly the six existing contract fields;
- a coverage retry receives a sanitized scaffold derived from the first schema-valid map;
- scaffold slots are application-generated, categories are already enum-validated, and
  source IDs are filtered against the authoritative page IDs and globally de-duplicated
  in first-seen order; and
- model-authored entry IDs, names, rationales, unknown IDs, duplicate IDs, and raw text
  are not placed in the correction scaffold.

The application still sends the complete bounded page-labelled diagnostic, validates
every extractable page ID exactly once, makes at most the initial map call plus one
correction, and never falls back to sampling.

## Test-first and review evidence

The focused regression was written before implementation. The red run produced two
expected failures and one pass: the prompt lacked the bounded thematic contract and the
coverage retry lacked the safe scaffold. After implementation, the integrated checks
were:

| Check | Outcome |
|---|---|
| Focused prompt/runtime suite | 145 passed in 1.37 seconds |
| Provider-free smoke suite | 36 passed in 1.61 seconds |
| Complete pytest suite | 1,153 passed in 25.73 seconds |
| Python compilation | Passed: `python -m compileall -q src tests` |
| JavaScript syntax | Passed: `node --check src/cpf_fcv_reviewer/static/app.js` |
| Static whitespace | Passed: `git diff --check` |
| Ruff | Not run; the module is not installed in this Windows environment |

A separate specification review passed. Code/security review identified one semantic
risk in treating 8-12 entries as a hard ceiling; the prompt and regression were revised
to make that range a compact target, permit up to 20 entries, and prohibit merging
unrelated drivers. Re-review approved the correction.

## Provider-free browser and DOCX QA

The deterministic smoke service ran locally without provider calls. Eight selected,
unique full-page PNGs were saved under the existing gitignored browser-QA directory for
intake, the genuine holding state, Five-minute readout, Detailed analysis, streamed
assistant output, four-message restoration after refresh, secondary correction, and the
mobile summary. All selected screenshots were visually inspected; no clipping, overlap,
horizontal overflow, missing state, or console/page error was found.

The downloaded `20260902-r5-08-smoke-full-detailed-note.docx` is 39,398 bytes. ZIP/OOXML
and structural inspection passed: 40 paragraphs, 13 headings, no tables, and one section;
the expected reader-facing sections were present and prohibited technical metadata and
assistant transcript labels were absent. The packaged renderer could not run because
LibreOffice is not installed, so no DOCX page-render acceptance is claimed.

## Deployment and provider status

The deployment branch was fast-forwarded to `00d3a64`, which includes code commit
`095873b` and this validation record. Render deployment `dep-dabusi7avr4c73aslkjg`
reached `live`; `/health` returned `ok` with the exact full SHA, the root page returned
HTTP 200, the review form and assistant shell were present, and no error logs appeared
after deployment.

No paid assessment has been submitted on this build. Uploading the local Guinea CPF and
RRA to the public prototype, where the configured external model provider processes them,
requires explicit confirmation of that disclosure. If confirmed, limit this deployed
cycle to one Guinea assessment, save unique full-page states and the DOCX on success, and
never rerun unchanged code.
