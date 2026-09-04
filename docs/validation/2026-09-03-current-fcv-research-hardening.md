# Current FCV research hardening validation - 2026-09-03

## Scope and diagnosis

The paid Guinea pilot exposed two independent provider-free defects. Primary research
required normalized title and publication date to exactly reproduce the provider's
grounded citation metadata, so harmless normalization drift could discard an otherwise
grounded allowlisted source. Curated recovery always queried World Bank indicators while
ReliefWeb was disabled when its optional application name was blank. This explains the
indicator-only recovery result. The later paid attempt still retained no primary claims
after metadata canonicalization; because rejected provider content is intentionally not
stored, the exact remaining primary-search gate cannot be proven from safe artifacts.

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


## Controlled paid validation and final diagnosis - 2026-09-04

Exactly one authorized paid Guinea assessment was submitted against deployed commit
`0b5315c4e802ff7306904a9c9854eea8b56ee182`. No provider-backed assistant call was
made and the assessment was not retried. It reached `run_complete` and produced:

- 60 evidence records: 52 document facts and 8 approved registry-language records;
- 5 RRA driver assessments, 4 FCV Strategy assessments, and 3 priority areas;
- one bounded repair, with no residual validation outcome;
- a valid 46,228-byte DOCX with 86 paragraphs; and
- 3 of 3 priorities with an explicit direct or indirect FCV causal pathway.

The result correctly used the `document_led` tier. It contained no current-context
evidence, no World Bank indicator API evidence, and no current-context citation attached
to an unrelated recommendation. The strongest direct conflict-sensitivity priority ranked
first. The limitation accurately stated that independent current-country research could
not be established.

A provider-free request then established the recovery cause: ReliefWeb returns HTTP 403
for the arbitrary application name because application names have required prior approval
since 1 November 2025. The previous default was therefore not usable. It has been removed;
a future ReliefWeb value must be supplied only after approval.

## Trusted think-tank fallback and final verification - 2026-09-04

Follow-up commit `b40ee4e38366ecb47453fe299d888946657707b3` adds one bounded,
credential-free country feed from International Crisis Group for Guinea. The adapter
accepts only the official HTTPS host, valid RSS content, an explicit English publication
date within two years, and an FCV-relevant title. A live provider-free probe retained one
October 2025 item about Guinea's military-led electoral transition. One such item produces
the existing reduced tier; it does not promote the review to full coverage.

Verification passed:

- focused research/configuration suite: **343 passed**;
- complete provider-free suite: **1,263 passed**;
- Python compilation, JavaScript syntax, and `git diff --check`: passed;
- external smoke browser:
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`; and
- independent code review: approved with no findings.

Render reported the exact follow-up commit live, and `/health` returned `ok`. The root
page returned HTTP 200. The public prototype remains deliberately volatile; this is not
operational persistence.

The Crisis Group deterministic mapping is intentionally limited to Guinea. Primary
research still permits the approved UN/humanitarian, Reuters/AP/BBC, and named think-tank
sources. ReliefWeb can be re-enabled with a genuinely approved application name. No
second paid assessment was submitted, so the new think-tank recovery was verified
provider-free rather than through another paid cycle.

No assessment identifier is recorded in this file or in `run-state.json`.
