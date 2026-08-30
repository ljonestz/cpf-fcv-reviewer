# CPF pilot reliability validation — 2026-08-30

## Scope

Validation covers the pilot reliability and UX tranche on `fix/research-resilience-guided-journey`, through code commit `d9b991f`.

The tranche adds deterministic full-range sampling for optional PDFs, balanced package evidence, coverage-aware abstention and repair, stronger FCV review instructions, and a Project Screener-aligned holding/results experience. The stable FCV Project Screener was not modified.

## Method

- Ran focused extraction and runtime regressions after the final Guinea adjustment.
- Ran the complete automated suite with an isolated Windows temporary directory.
- Exercised the public Guinea CPF/RRA pair locally without sending documents to a provider.
- Inspected the holding and results interfaces at 1280px and 390px using the deterministic local smoke flow.
- Checked JavaScript syntax and whitespace integrity.

## Results

### Automated checks

- Focused extraction/runtime suite: **99 passed** in 3.53 seconds.
- Full suite: **1,046 passed**, zero failures/errors/skips, in 50.37 seconds.
- Frontend-related suite: **61 passed**.
- JavaScript syntax: passed with `node --check`.
- `git diff --check`: passed.
- Ruff could not execute because Windows Application Control blocked the executable with `WinError 4551`; this is an environment limitation, not a reported lint result.

### Guinea bounded evidence check

Inputs were the user-supplied public 7-page Guinea CPF and 102-page Guinea RRA. Source documents and provider output were not committed.

The RRA was recognized as an RRA dated 2023-06-01. The 16-page bounded distributed sample retained review-visible pages:

`1, 2, 3, 4, 5, 15, 24, 34, 43, 53, 63, 72, 82, 91, 102`

Supported material was available beyond the opening pages:

| Theme | Sampled pages containing the term |
|---|---|
| Natural resource | 4, 15 |
| Legitimacy | 63 |
| Inclusion | 72 |
| Jobs | 72 |
| Conflict | 3, 5, 34, 43 |

The retained document carries the standardized warning: `guinearra.pdf: sampled 16 of 102 PDF pages; conclusions about absence are limited.` The review evidence remains globally bounded at 16 context segments.

### UX check

At both 1280px and 390px, the dedicated holding view displayed the compact elapsed timer, estimate, rotating guidance, connected three-stage ticker, active-stage animation, and keep-open message without horizontal overflow. Focus moved to the holding title when assessment began and to the result title when results loaded. Completion stopped the timer before result loading and finalized the ticker at 100%. Reduced-motion rules disable nonessential movement.

The results view retained one results shell, semantic status text/classes, styled disclosures, tab behavior, and targeted wrapping at both widths.

## Limitations and acceptance status

- `ANTHROPIC_API_KEY` was unavailable. No current-prompt real-provider Guinea, Haiti, or Benin assessment was run, and no JSON, HTML, or DOCX provider artifacts were fabricated.
- Guinea deep-page availability is deterministically confirmed, but substantive RRA driver-response quality still requires a real-provider run and FCV specialist review.
- Haiti's scattered jobs/IFC/MIGA treatment and Benin's multi-document package coverage remain provider acceptance checks. Benin remains the external blocker for any claim of multi-document/RRA readiness.
- The public Render `/health` release could not be reverified from this environment. The branch has not been deployed, so prior deployment claims were not advanced.
- No new DOCX was produced; page-by-page Word inspection was therefore not applicable.

## Conclusion

The deterministic reliability and holding-screen tranche passes its automated, structural Guinea, and local browser checks. Real-provider country acceptance and deployment verification remain explicit preconditions for broader readiness claims.
