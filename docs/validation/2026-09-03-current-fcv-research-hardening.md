# Current FCV research hardening validation - 2026-09-03

## Scope and diagnosis

The paid Guinea pilot exposed two independent provider-free defects. Primary research
required normalized title and publication date to exactly reproduce the provider's
grounded citation metadata, so harmless normalization drift could discard an otherwise
grounded allowlisted source. Curated recovery always queried World Bank indicators while
ReliefWeb was disabled when its optional application name was blank. This explains the
zero retained primary claims and the indicator-only recovery result.

The review validator also required every actionable priority to cite some current-context
item whenever any was present, regardless of substantive fit. Reduced-tier wording called
distinct URLs "institutional sources", which obscured that the observations could all
come from one publisher.

## Narrow fix

- Canonical grounded citation metadata now wins after an exact grounded-URL match.
- The allowlist and research prompt cover the approved UN/humanitarian, Reuters/AP/BBC,
  and named think-tank sources.
- Deterministic recovery uses only recent FCV-relevant ReliefWeb report titles; World Bank
  indicator observations are no longer queried by the recovery gateway.
- One recent vetted ReliefWeb FCV report can complete the practical recovery path at the
  reduced tier. Generic institutional data alone remain reduced and are not promoted.
- Recommendations cite current context only when it substantively supports their
  present-day claim.
- Reduced limitations separately count observations, distinct URLs, and institutional
  publishers.
- The external smoke runner accepts the legitimate mode-controlled CPF, CEN, or CPF / CEN
  title label.

## Provider-free verification

- Focused current-research/review suite: **567 passed**.
- Complete provider-free suite: **1,258 passed**.
- Python compilation and JavaScript syntax checks: passed.
- Complete external smoke-browser runner:
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`.
- Browser flow covered upload, summary, detailed analysis, two assistant turns, four
  restored messages after refresh, correction disclosure, 390-pixel mobile layout, and
  DOCX download.
- Smoke DOCX: 39,400 bytes and valid ZIP/OOXML structure.
- `git diff --check`: passed.

No provider-backed call or deployment was made during this validation stage. Smoke
artifacts are gitignored under
`output/playwright/2026-09-03-current-fcv-research-smoke-cf7710f-r2/`.
No assessment identifier is recorded here.
