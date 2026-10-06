# Country detection repair implementation plan

**Goal:** Implement the owner's approved title-alias and 10 MiB preflight repair.
**Architecture:** Extend the existing deterministic registry and keep frontend and
backend admission limits synchronized. Preserve all extraction and confidence gates.
**Stack:** Existing Python/Flask/pypdf, frontend JavaScript and pytest.

- [x] Add two synthetic cover-title cases in `tests/test_country_detection.py`:
  `COUNTRY PARTNERSHIP FRAMEWORK FOR THE FEDERAL DEMOCRATIC REPUBLIC OF ETHIOPIA
  FOR THE PERIOD FY27-FY32` -> Ethiopia and the same title with
  `REPUBLIQUE OF GUINEA` -> Guinea, both high confidence.
- [x] Add a route regression in `tests/test_routes.py`: the existing pypdf-only
  `make_pdf` cover copied through `PdfWriter`, padded with 3 MiB metadata, must
  return HTTP 200 / Somalia from `/api/detect-country` and create no session.
- [x] Update the existing frontend upload harness in
  `tests/test_frontend_upload_contract.py`: 10 MiB + 1 skips detection and accepts
  manual entry; 3 MiB, exactly 10 MiB and 2 MiB use detection. Check the 10 MiB message.
- [x] Run these regressions before implementation and confirm semantic failures.
  Command: `python -m pytest tests/test_country_detection.py tests/test_routes.py
  tests/test_frontend_upload_contract.py -k country -q` (also run the frontend file).
- [x] In `src/cpf_fcv_reviewer/country_detection.py`, change upload bytes to
  `10 * 1024 * 1024` and add the exact aliases to Ethiopia and Guinea.
- [x] In `src/cpf_fcv_reviewer/static/app.js`, change the matching byte constant
  and oversized-file message to 10 MiB. No other behavior changes.
- [x] Run focused tests and the complete provider-free suite, then local detector
  route checks against all six original CPF files. Keep outputs ignored.
- [x] Review the diff independently, resolve material findings, lint changed Python
  and check whitespace. Commit/push the feature and create a focused PR using `gh`.
- [ ] Require Linux CI before merging; allow normal Render auto-deploy and verify
  its exact commit, health and detector-only synthetic title/size checks. Test the
  browser intake and manual fallback without creating a real assessment.
- [ ] Record sanitized validation and the actual release; push documentation with
  `[skip render]`. Do not claim every country/title layout is automatically detected.

The user already approved this design and execution. Review is read-only; source
changes remain with the coordinating agent. No additional approval is needed for
the agreed correction or its reversible verification steps.
