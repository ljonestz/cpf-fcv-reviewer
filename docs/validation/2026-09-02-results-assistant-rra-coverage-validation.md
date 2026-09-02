# Results, assistant, and full-RRA validation

Date: 2026-09-02

## Scope

This record covers provider-free and deployed validation of the approved results
presentation, persistent follow-on assistant, and full-RRA diagnostic coverage redesign
on `fix/guinea-production-fixes` through code commit `0aa6d3d`. It contains no uploaded
documents, raw model output, assistant conversation export, credentials, or live
assessment identifier.

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
| Diagnostic schema-retry focused suite | 139 passed in 1.09 seconds |
| Schema-retry complete pytest suite | 1,147 passed in 35.15 seconds |
| Diagnostic coverage-retry focused suite | 143 passed in 0.97 seconds |
| Coverage-retry complete pytest suite | 1,151 passed in 46.54 seconds |
| Post-cycle diagnostic retry/failure suite | 168 passed in 1.78 seconds |
| Post-cycle complete pytest suite | 1,152 passed in 26.06 seconds |
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
of rendered DOCX visual acceptance is made. Any future successful deployed Guinea run
must save and inspect its DOCX, using Word or an available renderer if LibreOffice remains
unavailable.

## Deployed Guinea quality cycles

Three explicitly authorized paid cycles were run with the 7-page Guinea CPF and 102-page
Guinea RRA. Each deployed commit received exactly one assessment; unchanged code was not
rerun.

| Deployed commit | No-cost gate | Paid outcome |
|---|---|---|
| `cd2c57d` | Render live; health and static page passed | Stopped during diagnostic mapping with safe category `review_failed`; Render logged `ValidationError` |
| `894ebe5` | Render live; health reported the exact commit; root, review form, and assistant shell passed | A schema-valid map reached exact-once coverage validation, which failed closed as `diagnostic_coverage_unavailable` |
| `0aa6d3d` | Render live; health reported the exact commit; root, review form, and assistant shell passed | Stopped during diagnostic mapping after the one correction slot; Render logged `ValidationError` with safe category `review_failed` |

The second cycle established that structural parsing succeeded but the returned map did
not account for every extractable page exactly once. The third cycle exercised the shared
schema-or-coverage correction slot and then returned a schema-invalid map; because the UI
never advanced beyond diagnostic mapping, the error is not attributed to final review
drafting. No result, assistant conversation, or DOCX was produced in any cycle. The visual
intake, holding, mapping, and failure states were saved as full-page PNGs and inspected
without visible clipping, overlap, or broken controls under:

- `output/playwright/2026-09-02-guinea-production-cd2c57d/`; and
- `output/playwright/2026-09-02-guinea-production-894ebe5/`; and
- `output/playwright/2026-09-02-guinea-production-0aa6d3d/`.

Commit `0aa6d3d` added a provider-free verified correction for the exact second-cycle
failure. Diagnostic mapping still has at most two total model calls: the single correction
slot is used for either a schema error or a coverage error. Coverage diagnostics expose
only authoritative missing/duplicated material IDs and numeric counts for model-controlled
unknown IDs and duplicate entry IDs. A second invalid map fails closed, and no sampling or
deterministic fallback is used. Independent spec and code/security reviews approved the
change.

After the third cycle, commit `bce5bb3` added one narrow safe-failure regression fix.
If either allowed correction response is schema-invalid, it is now wrapped as
`diagnostic_coverage_unavailable` while preserving the `ValidationError` only as an
internal cause. Both retry paths still stop after exactly two map calls. The change does
not add a provider call, retry, sample, fallback, dependency, or abstraction. It passed
168 focused tests, 36 provider-free smoke tests, and all 1,152 local tests. This commit
has not been deployed or provider-tested, and another paid run is not justified solely
to observe its safer error category.

## Current acceptance status

Results presentation, assistant persistence/streaming, DOCX structure, and the full-RRA
fail-closed implementation are provider-free accepted. Deployed Guinea acceptance for the
redesign is not established because all three authorized cycles stopped before review
drafting. Commit `0aa6d3d` is live and received exactly one paid assessment; post-cycle
commit `bce5bb3` is provider-free verified only. Any further deployment and paid Guinea
run is a new fix cycle and requires an evidence-backed reliability change plus explicit
authorization after the provider-free and no-cost deployed checks.
