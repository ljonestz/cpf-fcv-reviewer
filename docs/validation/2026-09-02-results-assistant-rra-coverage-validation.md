# Results, assistant, and full-RRA provider-free validation

Date: 2026-09-02

## Scope

This record covers provider-free validation of the approved results presentation,
persistent follow-on assistant, and full-RRA diagnostic coverage redesign on
`fix/guinea-production-fixes` through code commit `4d73d46`. It contains no uploaded
documents, raw model output, assistant conversation export, credentials, or live
assessment identifier. No deployment or paid model assessment was run during this phase.

## Implementation acceptance

- The Five-minute readout presents a short overall assessment, separate RRA/current-
  dynamics and FCV Strategy synthesis, and up to three linked priority measures.
- Detailed HTML and DOCX keep substantive driver, strategy, recommendation, target, and
  limitation content while omitting reader-facing internal evidence and reproducibility
  disclosures. Structured evidence remains in the validated result/session context.
- The follow-on assistant uses the real streamed provider boundary in normal runtime,
  passes only the completed review and referenced evidence, retains at most 20 messages
  for the review's existing 24-hour lifetime, and restores after refresh. Correction
  children do not inherit parent assistant history.
- A recognized uploaded RRA or equivalent diagnostic is re-extracted in full within
  explicit page, character, byte, and estimated-input bounds. Every extractable page ID
  must be mapped exactly once. Unsafe extraction, over-budget input, unknown IDs, missing
  IDs, or duplicate IDs fail closed as `diagnostic_coverage_unavailable`; there is no
  silent RRA sampling fallback.
- The stable FCV Project Screener was not modified. No vector database, account system,
  frontend framework, or new persistence layer was introduced.

## Automated verification

| Check | Outcome |
|---|---|
| Consolidated results/RRA/assistant regression set | 557 passed in 10.58 seconds |
| Provider-free smoke suite | 36 passed in 3.18 seconds |
| Focused frontend contract/readability set after browser finding | 50 passed in 6.38 seconds |
| Complete pytest suite | 1,142 passed in 35.72 seconds |
| Python compilation | Passed: `python -m compileall -q src tests` |
| JavaScript syntax | Passed: `node --check src/cpf_fcv_reviewer/static/app.js` |
| Static whitespace | Passed: `git diff --check` |
| Ruff | Not run; the module is not installed in this Windows environment |

The first consolidated run exposed a stale JavaScript DOM test double that lacked the
standard `setAttribute` method. The harness was corrected without changing production DOM
behavior. Browser inspection later exposed a separate refresh defect: the restored title
dropped the country because the intake field was empty after reload. Commit `4d73d46`
stores only the country label alongside the existing session ID and clears both together;
the focused tests and full browser flow then passed.

## Provider-free browser QA

The deterministic smoke service ran locally at `127.0.0.1`. The preferred Playwright CLI
could not be downloaded because the npm request ended with `ECONNRESET`; the already-
installed Python Playwright runtime executed the same flow without adding a dependency.
The flow completed with no page or console errors, two streamed assistant requests, four
restored conversation messages after refresh, a closed-by-default correction control,
and a successful DOCX download.

Final visually inspected full-page PNGs are saved locally under
`output/playwright/2026-09-02-results-assistant-rra-coverage-smoke/` and are gitignored:

- `20260902-r4-01-smoke-intake-desktop-full.png`;
- `20260902-r4-02-smoke-holding-desktop-full.png`;
- `20260902-r4-03-smoke-summary-desktop-full.png`;
- `20260902-r4-04-smoke-detailed-desktop-full.png`;
- `20260902-r4-05-smoke-assistant-streamed-desktop-full.png`;
- `20260902-r4-06-smoke-assistant-restored-desktop-full.png`;
- `20260902-r4-07-smoke-secondary-correction-desktop-full.png`; and
- `20260902-r4-09-smoke-summary-mobile-full.png`.

The final screenshots showed no visible clipping, overlap, broken controls, or horizontal
overflow. The restored result retained the `Benin CPF FCV review` title and all four
assistant messages. All content is explicitly labelled synthetic smoke output.

## DOCX inspection

The downloaded `20260902-r4-08-smoke-full-detailed-note.docx` is saved in the same ignored
local artifact folder. It passed ZIP integrity, required OOXML-part checks, and
`python-docx` inspection: 40 paragraphs, 13 headings, no tables, and one section. The
expected redesigned headings are present, technical metadata fields and assistant content
are absent, and the package size is 39,397 bytes.

LibreOffice/`soffice` is not installed in the bundled runtime, standard Program Files
locations, or PATH. DOCX-to-PNG rendering therefore could not be completed, and no claim
of rendered DOCX visual acceptance is made. The final deployed Guinea run must save and
inspect its DOCX, using Word or an available renderer if LibreOffice remains unavailable.

## Remaining deployment gate

Provider-free acceptance is complete. Before any paid call, push and deploy the exact
verified commit, confirm Render reports it live, and complete health/static checks. Then
run at most one Guinea quality assessment for that deployed fix cycle. The quality run
must verify 102-page RRA accounting and deep-page use, final HTML hierarchy, two genuine
assistant turns plus refresh restoration, and the saved DOCX. Never rerun unchanged code.
