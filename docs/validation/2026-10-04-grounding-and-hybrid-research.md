# Provider-free grounding diagnosis and hybrid research - 4 October 2026

Repair code: `723645a`. Hybrid research code: `3514826`.
Branch: `fix/mai-grounding-diagnostics-20261004`, based on handover `0c757ba`.
The owner selected reuse of Render's Anthropic research route while keeping
assessment generation on local mAI. No live model call was authorized or made.

## Method and grounding findings

Read the handover, project instructions and shared mAI/Posit guides; verified a
clean handover worktree before creating the repair branch. Used saved allowlisted
failure diagnostics and synthetic fixtures. Did not retrieve rejected model
output, prompts, whole session payloads, credentials or the assessment identifier.

The synthetic six-error fixture reproduces two unsupported quotations, two unknown
assessment references and two target excerpt mismatches. An unchanged repair keeps
all six errors blocking. A repair supplying own-cited source selections and exact
target passages clears those six checks while preserving identity, analytical
fields, status and confidence. The existing merge path therefore works for this
controlled case. This is not a reconstruction of the rejected Guinea draft and
does not establish its precise cause or real-model reliability.

A separate regression established that `unknown_evidence` alone did not include
document passages in the repair payload. The repair now receives the existing
source-grounding context for that code too. This omission does not explain the
mixed-code Guinea failure: its other codes already enabled that context.
No quotation, locator, policy, date or evidence-reference validator was weakened.
No prompt change was made in the absence of a reproduced generation defect.

## Institutional research diagnosis and narrow repair

The [Guinea Crisis Group feed](https://www.crisisgroup.org/rss/23) was reachable.
It contained seven items: three dates parsed, one English item was inside the
two-year window, and four French date strings did not parse. Before correction,
the eligible English item was rejected because its nonempty teaser omitted the
country and the adapter's FCV keywords, masking a substantive country headline.

Synthetic positive cases failed before the repair. The adapter now selects one
literal source field: a substantive summary, or a substantive/assertive headline
under the already established title rule. It uses the existing title-grounding
helper for an unambiguous country article. It never joins title and teaser into
a manufactured quotation. Generic headings and contradictory geography remain
rejected. A related helper defect was also reproduced: deleting "Guinea" before
checking other countries hid Guinea-Bissau, Equatorial Guinea and Papua New Guinea.
The helper now uses the ordinary compound-country matcher and rejects all three.

A subsequent single public-feed fetch, replayed through the real institutional
controller without models, retained one observation from one URL/publisher, dated
2025-10-03. The controller correctly returned **reduced**, with explicit limits on
present conditions and breadth. This verifies retrieval, not current country
conditions or full research coverage. French date/language support remains limited.

ReliefWeb was not configured in the probe environment; this does not establish
the earlier server process's configuration. No new app name was provisioned or
ReliefWeb call made. No World Bank indicator or intranet adapter was added.
The old saved `source_candidates: 0` counter covers the primary search gateway,
not feed items: it cannot establish that the institutional feed returned no items.
The historical zero-accepted-source result remains unchanged.

Safe local probe record (ignored):
`output/20261004_provider_free_diagnosis/20261004_institutional_probe.json`.

## Explicit broader-research option

The owner chose the existing Anthropic public-web research route with separate
API costs. The candidate now supports this without moving generation off mAI:

- `MODEL_PROVIDER=mai_desktop` retains Sonnet 4.6 for review, mapping, repair and
  assistant responses, with the existing Desktop local-only access checks.
- `RESEARCH_PROVIDER=anthropic` explicitly selects the existing Render research
  gateway/controller, including its source filters, evidence checks, research
  budgets and institutional recovery. There is no new search implementation.
- `ANTHROPIC_API_KEY` is required for this option outside tests/smoke. A missing
  key fails configuration before Desktop sign-in. Store the key only in the
  environment or approved secret storage; never in source or instructions.
- `RESEARCH_MODEL_ID` is separate from the mAI model metadata. The local launcher
  defaults it to `claude-sonnet-4-5`, the repository's existing direct-provider
  default. This is not a new verification of the running Render model setting.
- Default mAI research remains `institutional`; default direct-provider behavior
  remains Anthropic. No silent provider fallback was introduced for generation.
- The intake identifies Anthropic research and its separate API charges while
  retaining the local mAI/DEV explanation and admission-limit notice.

The option was **not activated in the existing mAI server**. No key was retrieved,
no live Anthropic search was submitted, and no assessment was started. Current
API entitlement, live research breadth and combined-provider output quality remain
unverified. Existing four-per-day admissions and all retained reservations remain
unchanged. The research option does not solve the document-grounding failure.

## Verification

- Before fixes: one missing-repair-context test, two feed-selection cases and
  three compound-country controls failed for the expected reasons.
- **504 provider-free checks passed** across grounding/reference/selection,
  curated/public research and research-controller modules.
- The smoke/engine/runtime/orchestrator batch had 295 passes, one payload-contract
  expectation needing its new empty selection index, and two Windows pytest temp
  access errors. The affected checks passed in an isolated approved test directory;
  that recheck plus controller controls passed eight tests.
- All eight new hybrid config/routing/UI cases failed before implementation.
  Final hybrid/Desktop/config/runtime/smoke/frontend batch: **301 passed**.
- Four changed hybrid Python files parsed successfully; `git diff --check` passed.
  Local Ruff remains blocked by workstation policy; no local lint success claimed.
- Existing Edge acceptance runner: **11/11 synthetic checks**, exit 0, no console,
  JavaScript or resource errors, both Word downloads, assistant history, refresh
  and mobile views. The new desktop intake screenshot was visually inspected; the task-owned smoke
  server was stopped after verification.
  This used a separate provider-free smoke server with synthetic services and the
  hybrid intake labels, not a live combined-provider assessment.
- Full Linux suite and Python name/import lint are tracked by the new stacked
  draft PR's CI checks; the local counts above are not a full Linux-suite claim.

Browser artifacts (ignored):
`output/playwright/20261004_mai_acceptance/browser/20261004-hybrid-provider-free-01/`.

## Remaining gates

Production readiness remains unachieved. Fresh explicit approval is needed before
any model-backed research probe or further full assessment. A future accepted run
must still verify each quotation, reference, attribution, date, number and target,
plus rendered exports and the real assistant. Broader search is a separate research
improvement, not proof that the six grounding defects have been fixed.

Cross-country quality, hosted Application/ACN approval, runtime compatibility,
durable hosting/restart/restore, backups and provider spending controls remain open.
Nothing was merged or deployed; Desktop credentials were not moved, quotas were
not reset, and the separate stable FCV Project Screener was not touched.
