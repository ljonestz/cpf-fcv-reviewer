# Coordinator review redesign: candidate validation

Date: 12 October 2026. Branch: `feat/coordinator-review-redesign`.
Base: refreshed `origin/main` at `a210b29`. Implementation: `9611181`, `8e11906`,
`7ea5885`. Review: [draft PR #55](https://github.com/ljonestz/cpf-fcv-reviewer/pull/55).

## Scope and method

The agreed design is implemented for CPF/CEN Country Coordinator drafting:
four qualitative findings, evidence-linked priorities and destinations, central
review-stage calibration, compact RRA/Strategy connections, separate prior-comment
follow-through and an unsigned email. Intake and feedback remain optional beyond
the draft, country confirmation when needed and review stage. PC14 and Envelope
observations remain qualitative; formal assessment stays with their established
processes. The Project Screener, provider setup and hosting are outside this change.

Verification used synthetic documents and deterministic gateways. Contract, source
isolation, stage, export, API-state and frontend regressions were checked before
browser and Word inspection. This establishes application behaviour, not the
quality of a real model's analytical judgment or country-specific prose.

## Automated evidence

- Final full suite: **1,777 passed, 1 skipped** in 128.78 seconds. The skip is the
  existing Gunicorn concurrency test on Windows.
- After the final Word paragraph-layout adjustment: **35 passed** in the export
  and coordinator-presentation suites. No analytical behaviour changed afterward.
- `git diff --check` passed. Ruff comparison against the base found **no new
  issues** across 23 changed Python files; six pre-existing issues remain there.
  Whole-repository lint is not clean, so this is not a claim of a clean global run.
- Existing large-package coverage, diagnostic provenance, bounded repair,
  reproducibility, legacy-session and frontend checks ran in the full suite.

An independent read-only review identified four defects. Provider-free regressions
reproduced them; fixes retain the original guardrails:

1. A fully extracted RRA containing earlier comments now supplies its partitioned
   current content to diagnostic mapping, research context and fresh review.
2. Correction reruns save unsaved wording first and stop if preservation fails.
3. The email opening now receives the same stage check as its comments.
4. New core findings receive the existing advisory current-context check. Newly
   introduced directional claims in email prose must have linked current support;
   verbatim inherited claims retain their reviewed status.

Repairs also preserve recommendation destinations and cannot invent a coordinator
framing override. Model-generated emails cannot add official classification,
eligibility or PC14 compliance determinations, named sign-offs, new numbers or
unknown priority links. These checks remain bounded pattern/evidence checks,
not a complete semantic proof of every statement.

## Edge and Word inspection

The installed Playwright control CLI opened a dedicated visible Edge session,
navigated successfully and performed a separate dialog interaction. Existing
unrelated browser sessions were left untouched. The exact Python smoke runner,
using headless Edge, finished with:

`BROWSER_QA_PASS mode=smoke assistant_messages_restored=2 docx=3`

It verified three tabs, four findings, email save and refresh restoration,
optional feedback and final-comments restoration, preservation of unsaved wording
before corrections, stale-edit warnings, adoption of the updated draft, framing
override, mobile overflow and three valid editable Word downloads. No page or
console errors occurred in this runner. The separate visible session requested a
favicon that the development server does not provide (404); review operation was
unaffected.

Initial browser attempts exposed an undersized synthetic feedback fixture, a
closed-disclosure text assertion and a missing wait for the corrected header.
Those QA issues were corrected without submitting any paid assessment.

Ignored local browser artifacts:
`output/playwright/20261012-coordinator-redesign-browser-verified/`.
Screenshots include desktop intake, holding, summary, detailed analysis, email,
assistant restoration, correction/stale email and mobile summary.

Final exports with readable synthetic prior comments:
`output/playwright/20261012-coordinator-final-word/`.
The detailed note has two pages; summary and email have one page each. All four
rendered pages were inspected. A source note stranded on a new page was fixed by
keeping it with its finding, then the final files were rendered again. The detailed
note includes the separate follow-through section.

The packaged `render_docx.py` could not run because this workstation lacks its
`pdf2image` dependency; no native LibreOffice executable was established. Conversion
instead used a separate hidden Microsoft Word COM instance, read-only opens of our
synthetic files and PDF export, followed by installed PyMuPDF page rendering.
Only that dedicated Word instance was closed. No user document was edited.

## Test environment and remaining acceptance

Windows sandbox temporary-file access required the normal elevated tool mechanism
for fixture-based tests. Each full run used a new asserted directory under ignored
`tmp/`. The inherited invalid `SSL_CERT_FILE` was replaced with certifi's existing
valid CA path in the test process only; TLS verification was not disabled and
application/provider settings were not changed.

The requested GPT-5.6 Luna delegate is unavailable. Implementation stayed inline;
the bounded read-only acceptance review used the available inherited model.

No paid model call, live country-quality run, merge or deployment was performed.
The public prototype's confidentiality boundary remains. Internal ITS hosting and
approved private Strategy/style references must be connected through the governed
internal route; this change does not claim that integration is complete. Feedback
uses the configured review lifetime, not a permanent evaluation archive.
