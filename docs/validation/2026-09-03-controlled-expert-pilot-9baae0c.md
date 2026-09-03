# Controlled expert pilot hardening validation on 9baae0c - 2026-09-03

## Scope and methodology

This record covers the provider-free pilot gate for code commit `9baae0c` on the
`fix/guinea-production-fixes` branch. The implementation activates curated research
recovery, gives document-led fallback a privacy-safe terminal reason, requires explicit
FCV relevance and priority ordering, narrows finalization-stage overreach, and shows the
existing FCV rationale on summary cards.

Only synthetic smoke inputs were used. No provider-backed assessment, paid API call,
deployment, or push was performed for this commit. The stable FCV Project Screener was
not modified. The dated Guinea validation record remains unchanged.

## Environment and limitations

- The worktree has no `.venv`; equivalent commands used `C:\WBG\Python313\python.exe`
  (Python 3.13.7) with `SSL_CERT_FILE` cleared only for each command because the
  inherited value pointed to a missing Downloads certificate file.
- Ruff was unavailable: the requested `.venv` interpreter is absent and the configured
  Python runtime has no `ruff` module.
- The first full and focused runs used workspace-local basetemp directories. They executed
  1,208 and 476 tests respectively but encountered Windows ACL setup errors when pytest
  created temporary files inside the OneDrive worktree. A fresh complete run used a
  unique base temp directory under the existing Windows local-temp parent and passed all
  1,237 tests with no failures or setup errors.
- LibreOffice is not installed, so DOCX page-image rendering was not available. DOCX
  ZIP/OOXML and structural inspection were completed.

## Automated verification

| Check | Outcome |
|---|---|
| Python compilation | Passed: `python -m compileall -q src tests` |
| JavaScript syntax | Passed: `node --check src/cpf_fcv_reviewer/static/app.js` |
| Provider-free smoke suite | 36 passed |
| Focused pilot gate | 476 passed; 2 OneDrive temporary-directory ACL setup errors on the initial run |
| Complete pytest suite | 1,237 passed using a non-OneDrive base temp directory |
| Ruff | Unavailable in this environment; no `.venv`, no installed module |
| Static whitespace | Passed: `git diff --check` |

## Provider-free browser QA

The existing external QA runner was imported dynamically from
`output/playwright/2026-09-02-results-assistant-rra-coverage-smoke/run_browser_qa.py`,
its `OUT` was overridden to a new attempt folder, and its `main()` was called against
the local smoke service started by `scripts/run_smoke.py` at `127.0.0.1:58422`.

The runner completed with:

`BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`

The flow covered programmatic CPF/RRA upload, result and detailed views, two streamed
assistant turns, refresh restoration of all four assistant messages, correction
disclosure, mobile summary, and DOCX download. It recorded no console or page errors.
The 390-pixel mobile capture had no horizontal overflow. The desktop summary, detailed
view, and mobile summary PNGs were visually inspected and showed no obvious clipping,
overlap, or broken controls. The summary visibly includes `FCV relevance.` and the
existing rationale text above the response.

Canonical artifacts are gitignored and stored under:

`output/playwright/2026-09-03-controlled-pilot-smoke-9baae0c/`

The folder contains these eight full-page PNGs:

- `20260902-r4-01-smoke-intake-desktop-full.png`
- `20260902-r4-02-smoke-holding-desktop-full.png`
- `20260902-r4-03-smoke-summary-desktop-full.png`
- `20260902-r4-04-smoke-detailed-desktop-full.png`
- `20260902-r4-05-smoke-assistant-streamed-desktop-full.png`
- `20260902-r4-06-smoke-assistant-restored-desktop-full.png`
- `20260902-r4-07-smoke-secondary-correction-desktop-full.png`
- `20260902-r4-09-smoke-summary-mobile-full.png`

## DOCX inspection

`20260902-r4-08-smoke-full-detailed-note.docx` is 39,400 bytes. It passed ZIP integrity
(`testzip() is None`), contains `word/document.xml` and `[Content_Types].xml`, and has
19 ZIP entries. OOXML parsing found 40 nonempty paragraphs; `python-docx` found 40
paragraphs, zero tables, and one section. No file content was modified during
inspection.

## Acceptance conclusion

The provider-free controlled pilot gate passed for the application behavior exercised by
the smoke runner, including the new summary FCV-relevance presentation. The last
deployed baseline remains `a52505c74d72bc08d4f973436f8b8204c76b1d0b`; `9baae0c` remains
undeployed and provider-free only. Deployment, push, and any paid Guinea run remain
out of scope and intentionally unchecked.
