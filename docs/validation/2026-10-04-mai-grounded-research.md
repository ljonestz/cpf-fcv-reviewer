# mAI country research and three-run acceptance

## Authorization and scope

The owner chose to avoid the separate Anthropic API and authorized up to three
new full local assessments, with repairs between attempts. This supersedes the
earlier one-run limit for this testing cycle only. Existing quota counters,
evidence validators and historical records remain intact. No merge, deployment,
hosted Desktop credentials or change to the stable FCV Project Screener is authorized.

## Research design

The authenticated [mAI Google Search guide](https://ai.worldbankgroup.org/maifactory/google-search/)
documents Desktop access through the mAI Gemini gateway. Gemini 3.8 Flash uses
Google Search to discover public sources; Sonnet 4.6 through mAI selects substantive
passages from independently fetched original pages. The application copies those
passages and verifies source ownership, country, date and source suitability.
Google's generated synthesis is never treated as a literal source quotation.

The search request contains only a canonical country, review date and fixed public
FCV topics. Uploaded documents and review notes remain outside search requests.
Original-page retrieval uses a separate unauthenticated client, HTTPS, checked
redirects, bounded reads and the existing public-publisher catalogue. Catalogue
coverage limits retrieval; it is not a claim that other publishers are unreliable.
Provider search suggestions are displayed in an isolated, scriptless frame.

Local setup: reuse the existing mAI environment and Desktop sign-in. Set
`MAI_TEAM_NAME` to the approved team and `RESEARCH_PROVIDER=mai_google`, then run
`scripts/20261004_run_mai_desktop.py`. No separate Anthropic key is required.
`APP_RELEASE` can identify the exact checked-out commit for acceptance. Preserve
the workstation's verified certificate configuration; never disable TLS checks.
Costs accrue through mAI model/search usage. This is not a free or offline route.
Desktop remains local DEV only; hosted use still needs Application/ACN approval.

## Failures reproduced before repairs

- First discovery probe exhausted its output budget; incomplete responses are rejected.
- A subsequent research check found 17 leads but only one parsed original among
  the first eight. Four of six model-transcribed quotations failed exact matching.
- Passage-ID selection now copies original text instead of asking the model to
  transcribe quotations. Invented IDs and model-authored quotations are rejected.
- Public fetches inspect up to 16 leads with four concurrent readers and a shared
  deadline. Every redirect retains the same URL and credential boundary.
- Conflicting World Bank article-path and metadata dates remain undated.
- Country-incompatible passages are excluded before selection using the same
  country check that validates the final observation; the validator is unchanged.

## Acceptance method fixed before full runs

Use the frozen Guinea strategic overview, results framework and June 2023 RRA
from the [earlier acceptance specification](2026-10-01-provider-free-release-gates.md),
Decision Review, with no focus instruction steering around known defects.
Run the exact browser runner against synthetic inputs first, then identify the
live local service by its exact commit. Reserve each of the three attempts in a
separate non-overwriting ledger file. Failed attempts count; no quota resets.

Inspect all accepted priority references, target excerpts and RRA response quotes;
all five RRA drivers and four Strategy shifts; date/projection fidelity; feasibility
and numerical recommendations; current research coverage; summary/detail agreement;
assistant grounding; persistence and both Word exports. On failure retrieve only
allowlisted safe diagnostics, reproduce synthetically, and repair before another run.

Compare with the saved direct-Anthropic Guinea candidate using the same frozen
three-document corpus and the historical deployed Render assessment. These differ
in release, model and date; the comparison is a factual/coverage benchmark, not a
controlled claim of provider equivalence. Neither baseline is error-free. Specifically
check the eight issues recorded in the
[3 October accepted-output review](2026-10-03-quote-selection-paid-acceptance.md).

## Evidence and status

Ignored preparation records: `output/20261004_mai_grounding/`. Browser/assessment
artifacts and the new three-run reservation ledger:
`output/playwright/20261004_mai_grounded_acceptance/`. Live identifiers remain in
the existing OS-temporary handoff directory, outside the repository.

Preparation has established mAI-native search connectivity and exact passage
copying, but research breadth and end-to-end acceptance remain under test.
Production readiness is not established by these preparation probes. Final test
counts, full-run outcomes and comparison findings will be recorded after inspection.
