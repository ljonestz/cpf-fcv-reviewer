# Guided journey and Benin browser validation

Date: 2026-08-15  
Branch: `fix/research-resilience-guided-journey`  
Validation commit: `9736ed6`

This record covers local browser QA for the guided review journey. It is not a production-readiness assessment and does not authorize operational use, deployment, or connection to the stable FCV Project Screener.

## Test base and method

The deterministic local smoke server was tested at `http://127.0.0.1:58422/` using the Benin test base supplied for this task:

- primary: one `BOSIB` PDF;
- package: eight `BOSIB`/`SECBOS` PDFs;
- context: `Benin RRA September 2023.pdf`.

The browser flow used the `Finalization` review stage. No real-provider credentials or live model call were used. The resulting content was synthetic smoke output and was not assessed for substantive Benin findings.

## Browser results

| Check | Result |
|---|---|
| Country detection | Benin detected after upload |
| Guided progress | Documents, current-country evidence, and drafting/validation stages displayed in sequence |
| Desktop viewport | 1280px: passed; no horizontal overflow |
| Mobile viewport | 390px: passed; upload zones and progress cards stacked; no horizontal overflow |
| Completion state | Results displayed and progress panel computed as `display: none` |
| Evidence status | `Current evidence established` rendered in both result views |
| Detailed analysis | Tab activated; evidence-linked target and document coverage rendered |
| DOCX export | Browser download event triggered from `Download full detailed note` |

The browser check found and fixed a CSS regression in which the author rule `#progress { display: flex }` overrode the HTML `hidden` attribute after completion. The fix adds the repository-wide rule `[hidden] { display: none !important; }`, with a focused regression test.

## Automated checks

- Focused frontend suite: `46 passed`.
- JavaScript syntax: `node --check src\\cpf_fcv_reviewer\\static\\app.js` passed.
- Full suite attempt: `868 passed`, `22` setup errors caused by the known Windows `WinError 5` access failure while pytest scans the shared temporary root. No assertion failures were observed.
- Ruff: blocked by Windows Application Control `WinError 4551`.
- `git diff --check`: passed with expected line-ending warnings only.

## Deployment verification

The Render service `cpf-fcv-review-prototype` was manually deployed to the exact validated commit `9736ed656e9d65f4cecd93d2e5aa83567c284870`. Render reported a successful build and live service. The public checks returned:

- `/health`: HTTP 200, `status: ok`, `storage: volatile`, `release: 9736ed6`;
- `/`: HTTP 200 with the guided-progress markup present.

The service is configured against the existing `feat/mvp-review-run` branch, so this exact-commit deployment was intentionally targeted. Future release work should preserve that explicit deployment and release-label discipline.

No raw document contents, model output, secrets, or live assessment identifiers are included in this record. The public prototype remains non-production, volatile, and public-web-only for current context.
