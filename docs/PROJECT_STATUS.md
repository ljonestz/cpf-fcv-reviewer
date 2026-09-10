# Project status

## Current position — 2026-09-08

Application PR30 is on main and deployed as `27ef3aa`. Render and `/health` confirm the
exact release. Live execution and exports passed on the preceding PR24 acceptance run.
Readiness is **supervised public-document pilot**, not routine operational production.
The remaining RRA date error, proposal wording, source breadth and volatile storage are
tracked in [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md). Documentation below is a
chronological record; older pending-deployment statements refer to earlier checkpoints.
The latest full readout and screenshots are indexed in the readiness record.

## 2026-09-10 Production readiness review and availability fixes

A full-application review on branch `claude/production-readiness-review-6evrz7` found five
blocking defects. All five are fixed here, provider-free; **no model API was called, no paid
quality run was performed and nothing was deployed.** The full findings inventory, including
the items left open, is in
[the 2026-09-10 review record](validation/2026-09-10-production-readiness-review.md).

Fixed:
- The primary CPF/CEN was extracted with every safety budget disabled (`runtime.py`), so a
  479 KB DOCX inflating to 200 MB was accepted at 841 MB peak RSS — an OOM kill of the single
  512 MB instance from one anonymous request. The primary now uses the same bounds as full RRA
  extraction and fails closed as `document_unreadable`.
- An unhandled exception in `background.py` killed the only worker thread, leaving every later
  review queued forever while `/health` still reported `ok`. The loop now records and
  continues, and `/health` reports `worker` state, returning 503 when the worker is gone.
- An SSE stream held a gunicorn thread for a whole multi-minute run; four viewers could starve
  the four-thread pool including `/health`. Streams now end at `EVENT_STREAM_MAX_SECONDS`
  (default 90) and resume losslessly via `Last-Event-ID`; `app.js` resets its error counter on
  reconnect so a capped close is not mistaken for a failure.
- The website rendered no evidence, sources, dates or verification status at all — the
  renderers existed but nothing called them, so the "evidence-linked" promise held only in the
  Word export. Priority areas now carry their Traceability panel, and the detailed view carries
  evidence status and coverage.
- The failure screen reused the running-progress presentation with a reset timer, so a failed
  run read as restarted. It now presents as stopped.

Three tests were asserting the wrong thing and are corrected: a frontend test that matched
app.js source text rather than rendered DOM (and a sibling that asserted the missing-evidence
bug as correct), a blueprint test pinning a deploy branch 148 commits behind `main`, and a
registry test frozen at 2026-08-23 that could never catch the bundle's 2027-08-22 expiry.
`render.yaml` now targets `main`, and the registry hash is derived from the bundle rather than
duplicated as a literal.

Provider-free suite: **1,553 passed** (1,527 before). Ruff is unchanged at pre-existing debt;
the changed lines are clean.

Still open and unchanged by this work: the public URL has no authentication or rate limiting,
the RRA date remains model-authored (root cause diagnosed in the review record), the bounded
repair can still drop priority areas for non-allowlisted issue codes, and the live service's
storage posture still needs reconciling with `render.yaml`.

## 2026-09-08 Top-edge Word running banner

The approved treatment uses one native default-header paragraph with white text and a
teal rule. Negative one-inch horizontal indents extend its shading to both page edges;
zero header distance places it at the top edge while one-inch body margins remain
unchanged. The 42.5-point exact line height reproduces the user-edited banner's 65-pixel
depth in native Word on all 12 pages (3-page short and 9-page full). The header contains
no floating or positioned objects. PR30 deployed this implementation as `27ef3aa`;
Render and `/health` confirmed the exact release. No paid assessment was performed. See the
[Word presentation validation](validation/2026-09-08-word-export-presentation.md).

## 2026-09-08 Word presentation update

Both Word exports now use an opening language-model caution and omit the final
basis/limitations section; the website disclosure is unchanged. Native Word styles,
one-inch margins, left alignment and subtle heading/action shading keep reports editable.
Existing Guinea exports were restyled locally: three-page short note and nine-page
full note. All 1,527 provider-free tests passed; no new assessment was run. The final Word
presentation is deployed as `72743f5`. See
[Word presentation validation](validation/2026-09-08-word-export-presentation.md).

## 2026-09-07 Deployed: live Guinea flow passes with qualified evidence

PR24 is deployed as `9f787f4`; Render and /health confirm the exact release.
Luna max completed the authorized live Guinea flow: eight screenshots, assistant
restored after refresh, and both Word exports. Five dated current observations from
two Africa Center articles entered the assessment. Coverage is explicitly reduced.
The coordinating agent independently inspected the short Word note and summary PNG.

Remaining factual issue: the generated review says September 2022 for the RRA, whereas
the approved PDF cover says June 2023. Some proposed delivery changes need expert
validation. Execution/source integration passed; native-chat parity and blanket factual
accuracy are not established. See `docs/validation/2026-09-07-live-release-acceptance.md`.

## 2026-09-07 Recommendation length is advisory

User approved treating excess recommendation length as advisory. The validator still
reports the word-limit issue, but it no longer blocks completion or causes paid repair.
The bounded repair follow-up now filters advisory issues before deciding whether another
model call is warranted. Evidence/citation errors retain fatal validation.

Three new orchestrator cases and the expanded runtime regression failed before the fixes.
Final provider-free suite: **1,524 passed**, including smoke tests. No paid calls or deployment.
The all-country research candidate remains on PR24 pending successful live quality acceptance.

## 2026-09-07 Luna max retry: word-limit blocker remains

One further explicitly authorized paid quality assessment on `6fb6869` was delegated to
Luna max. It failed after bounded correction with one residual `stage_length_overreach`.
The missing-registry-support residual did not recur. No successful result, assistant call,
or Word export was produced. The coordinating agent inspected the failure screenshot.
No further paid run, merge or deployment. See
`docs/validation/2026-09-07-luna-max-quality-retry.md`. The next local issue is the word-limit
rule blocking the entire assessment; live content quality remains unaccepted.

## 2026-09-07 Candidate quality run: correction failure, local fix validated

The user explicitly authorized one full public Guinea CPF+RRA assessment and one
assistant follow-up. The local candidate on `03b4601` retained dated current evidence
(`research_reduced`, not model-only fallback), but failed final validation after repair.
Safe codes: initial `unknown_institutional_referral` and `stage_length_overreach`;
terminal `missing_registry_support` (three issues), then `review_failed`.
No successful review, assistant request, or Word export was produced.

A local regression reproduced loss of valid priority evidence during unrelated mechanical
repair. The correction now preserves the original assessment, source links and unaffected
content when only action length and institutional-reference corrections are requested.
All three new regressions failed before the fix; the full provider-free suite now passes
**1,520 tests**. The bounded registry-link follow-up also preserves already grounded
priorities and only adds supplied registry evidence to an unsupported priority. This establishes the local failure-class fix, not the exact content of the
rejected live draft, which was not retrieved. A second paid assessment requires explicit
authorization under the repository's one-run rule. PR24 remains draft; no merge or deployment.
See `docs/validation/2026-09-07-model-led-evidence.md`.

## 2026-09-07 Live probes block release

The three authorized research-only probes on `0b65e0f` accepted zero current-context
claims for Guinea, Kenya, and Haiti. Guinea/Kenya lost all cited passages to publisher
acceptance; Haiti retained sources but lost its claims at the FCV-relevance stage.
No full review or deployment followed. Diagnostic source capture is prepared to
identify exact rejection causes before further changes. See
`docs/validation/2026-09-07-paid-source-probes.md`.

## 2026-09-07 All-country live-research finalization (branch validation)

Current work removes narrow discovery restrictions, fixes approved-publisher date
fetching, and allows exact quotes to inherit unambiguous article-country context.
CPF context and review focus now inform search, and substantive political events and
mixed FCV/economic reporting are retained. Fallback guidance separates historical
knowledge from current hypotheses and
qualifies their use in recommendations. The goal is useful source-backed CPF analysis
for all countries, not a Guinea-specific recovery route. All 1,501 tests pass;
live research quality and deployment remain pending. See
`docs/validation/2026-09-07-all-country-live-research.md`.

## 2026-09-07 Five-minute readout refinement (deployment pending)

Priority overviews combine up to two assessment sentences with one FCV-relevance
sentence in a plain-text paragraph. Recommended responses retain the full detailed
action. The separate FCV-relevance label is removed from the short view.
A five-minute Word download joins the existing detailed note and new-review actions;
it preserves the same three summary priorities, full actions, and important limitations.
The detailed assessment is unchanged. No model calls are required for either export.

Validation: 74 targeted tests and the provider-free browser smoke passed, including
both actual Word downloads and the link to the detailed recommendation. Across the
full suite and temporary-directory reruns, 1,479 tests passed. Four existing
article-metadata tests also fail against main: their AP News fixtures are excluded
by the crawler allow-list reused in the metadata fetcher. This separate research
issue remains open; no live run or deployment was performed for the readout change.

## 2026-09-07 PR #21 deployed; Guinea end-to-end completion passed

Release `63b16da` is live, verified through Render and `/health`. One authorized
Guinea CPF+RRA run completed in full RRA-alignment mode with five driver assessments,
four Strategy assessments, four priority areas, and a valid 48,924-byte DOCX.
Summary/detailed browser views and refresh restoration passed. The six-theme
AI-context fallback ran because zero independent current-context sources were
accepted. One bounded repair completed; the prior limited-mode blocker did not recur.

Production readiness remains limited by current-evidence quality: fallback caveats
are disclosed, but some main-narrative trends and recommendations are too confident
for unverified model knowledge. Execution success is not factual validation.
See `docs/validation/2026-09-07-guinea-acceptance.md` for checks, limits, and next work.

Entries below are retained as dated historical evidence. Where they say a deployment,
acceptance run, or fallback was pending, the current snapshot above supersedes that status.

## 2026-09-07 Guinea map-only probe passed (historical pre-deployment record)

One authorized model request using the Render service's configured model
`claude-sonnet-4-5` mapped all 101 extractable RRA pages to 16 valid thematic
entries; schema and representative evidence-reference validation passed. No retry
was needed. The earlier schema failure was not reproduced, so no schema loosening
is justified. The correction subsequently shipped in PR #21 and release `63b16da`; the full Guinea
acceptance and DOCX verification are recorded above and in `docs/validation/2026-09-07-guinea-acceptance.md`.
Safe details are in `docs/validation/2026-09-07-limited-mode-validation.md`.

## 2026-09-07 Limited-mode validation correction (historical pre-deployment record)

Based on verified GitHub main `3bf4f08`. A provider-free regression proves that
runtime's own downgrade warning, "without RRA alignment", triggers
`limited_mode_overclaim`. The warning is restored after repair, making the failure
unrepairable even when model-authored text is valid. The warning now explicitly
states "RRA alignment was not assessed"; the validator and its safety boundary
are unchanged. Final diagnostic-map schema failure now logs sanitized field paths
and issue types using the existing bounded sanitizer.

Runtime, validator, and smoke coverage: 308 tests passed initially; two temporary-
directory setup errors passed on isolated rerun outside the Windows sandbox.
Both new regression assertions were observed failing before their fixes.
The changed files retain three pre-existing lint findings (two import-order issues
and one long line). At the time of this record no paid API call, merge, or deployment
had been performed. The correction and its sanitized diagnostics subsequently shipped
in PR #21; the authorized map probe and end-to-end acceptance are recorded above.
Production readiness remains limited by current-evidence quality.
See `docs/validation/2026-09-07-limited-mode-validation.md`.


## 2026-09-07 FCV model-readout fallback (historical pre-confirmation record; superseded)

When external current-source research comes back empty (Guinea returns only neighbour-country
hits from the narrow institutional `allowed_domains`), the app now falls back to a bounded,
knowledge-based Claude readout of current FCV conditions, injected into the review as
context-only and clearly caveated ("AI-generated; no external current sources; verify before
use"), plus a provenance limitation. PRs #17 (feature) + #18 (fix). A paid readout run
(`f31e3c6`) exposed a one-line defect — `load_prompt` rejected the new `fcv_readout` name
(not in `PROMPT_NAMES`) → `fcv_readout_unavailable`; #18 fixes it (provider-free verified,
full suite 1477 passed). The confirming paid Guinea run was not executed at the time of this record. It was
subsequently completed on release `63b16da`; see `docs/validation/2026-09-07-guinea-acceptance.md`.
Recommended higher-value follow-up:
broaden the search (one unrestricted `web_search` retry filtered by the existing publisher
allowlist) so real wire reporting surfaces instead of relying on the readout.

## 2026-09-06 Option B DEPLOYED + paid Guinea acceptance run PASSED (historical)

PR #15 merged to `main` and manually deployed to Render (`srv-d9tju52jobas73d6jvk0`,
`release: 4dd0f69`). One authorized paid Guinea CPF+RRA run reached **`run_complete`** (a
first for Guinea) with a valid 46 KB DOCX — the previously-blocking
`missing_current_context_support` → `review_failed` is resolved: at `validate` the app
emitted `advisory_notice` for the two current-context issues (non-fatal) and repaired only
the separate genuine fatal issue (`unknown_institutional_referral`). The run correctly
degraded to `document_led` with honest current-context limitations. The grade-and-keep /
confidence-chip path was NOT exercised live (the Guinea search returned only Guinea-Bissau
content, all floored on country-match) — it remains covered by the 1468-test suite. Full
record: `docs/validation/2026-09-06-option-b-paid-guinea-acceptance.md`. Follow-up:
strengthen Guinea search-side disambiguation so genuine Guinea reporting surfaces.

## 2026-09-06 Option B: current-context claim grading implemented + provider-free verified (historical)

**What changed.** The current-context (live-news) path no longer deletes claims that fail
soft checks or fails the review solely because machine-verified current evidence was thin.
Instead:

- **Claims are graded** at the research boundary: `verified` (recent, FCV-substantive,
  passes all checks), `partially_verified` (recent and substantive but some soft checks
  failed), or `unverified` (not recent, or failed a hard check). Unverified and
  non-recent claims are excluded from coverage calculation and do not elevate the evidence
  tier; they remain in the research result as context-only items.
- **`missing_current_context_support` is now an advisory validation issue** via a new
  `severity` field on `ValidationIssue`. The orchestrator only repairs or fails on
  `fatal`-severity issues; advisory issues are surfaced in metadata but do not block the
  run. A review will never fail solely because current-context claims could not be
  machine-verified — the worst case is a clearly labelled, thin current-context section.
- **Ambiguous country names** (Guinea / Congo / Niger and compound neighbours) are
  disambiguated in the research prompt, preventing the country-scope filter from dropping
  valid claims.
- **Tiered influence in the review prompt:** verified claims may support ratings and
  recommendations; partially verified claims are corroboration only; unverified claims
  are background context only. The LLM is instructed not to draw conclusions from
  unverified claims alone.
- **Exports** (DOCX and HTML) show an "AI-generated from trusted sources — verify before
  use" banner and per-claim confidence chips indicating the verification grade of each
  current-context item.

**Scope.** The change is confined to the current-context research and grading path.
Uploaded-document analysis, the registry, schema validation, and policy-language checks
remain fully fail-closed and are unchanged.

**Regression fix (Task 10).** The `SmokeResearchGateway._claim` method did not set
`verification` explicitly, so it inherited the new `"unverified"` default introduced by
Task 3. Since `_missing_coverage` excludes unverified claims, all 8 smoke mode tests
failed with `current_evidence_tier == "reduced"` instead of `"full"`. Fixed by setting
`verification="verified"` in the smoke fixture — synthetic fixtures are always trusted by
construction. This was the only Option B regression; all other failures matched the 4
known pre-existing `test_public_research.py` failures.

**Provider-free verification (2026-09-06).** Full suite: **1,466 passed, 4 failed**. The 4
failures are the pre-existing `test_bounded_article_metadata_reads_publication_fields_only`,
`test_gateway_performs_at_most_one_metadata_get_for_opaque_sources`,
`test_missing_date_is_recorded_before_metadata_client_failure`, and
`test_article_metadata_stream_stops_at_shared_attempt_deadline` — all in
`tests/test_public_research.py`, all predating Option B, and all unrelated to this work.
The browser smoke runner (`scripts/run_smoke_browser.py`) requires a running local server
and was not run.

**Historical status at the time of this entry:** branch `feat/option-b-current-context` had
not yet been merged or deployed, and the paid acceptance gate had not yet been run.
It was subsequently merged, deployed, and verified; see the current snapshot above.

Design spec: `docs/superpowers/specs/2026-09-06-option-b-current-context-design.md`
Implementation plan: `docs/superpowers/plans/2026-09-06-option-b-current-context.md`

---

## 2026-09-06 live-news pipeline fixed + deployed; review still gated on current-context (historical)

- **Three root-cause bugs in the current-context (live-news) pipeline found, fixed, merged (PRs #11,
  #12, #13), deployed to Render, and verified on live runs.** All were hidden for 6–7 sessions because
  every test mocks the provider and the real errors were swallowed. Full detail:
  `docs/validation/2026-09-06-live-news-pipeline-fixes-and-verification.md`.
  1. web_search sent Reuters/AP/BBC in `allowed_domains`; those block Anthropic's crawler → HTTP 400 on
     every run. Fixed by excluding crawler-blocked wires (kept as publishers) + self-heal retry. Live:
     `source_candidates: 20`.
  2. `_source_mentions_country` rejected sources naming both the country and a compound neighbour
     (Guinea + Guinea-Bissau). Fixed by strip-compound-then-require-standalone. Live: Benin mismatch 12–14 → 2.
  3. `_source_metadata` read `published_at`; Anthropic's `web_search_result` uses **`page_age`** (verified
     against the web-search docs). Fixed by reading `page_age`. Live: real Guinea `missing_publication_date: 0`.
  - PR #12 (`MAX_NORMALIZATION_OUTPUT_TOKENS=8000`) was a mis-diagnosis caught by verification; harmless,
    left in. New WARNING log `research_provider_exception` now makes research failures diagnosable in Render.
- **Verified live:** Benin synthetic reached `research_reduced` (claims accepted); real Guinea CPF+RRA
  dated all sources but returned 0 accepted (search returns mostly Guinea-Bissau; the few Guinea claims
  fail normalization). **Both still end `review_failed`.**
- **Remaining (handed to a fresh session — Option B):** the app cannot complete a review with zero
  accepted current-context claims (`missing_current_context_support` is repairable but unfixable without
  evidence → `review_failed`). Next step is to make current-context behave like a trusted-source-guided
  LLM synthesis with soft-flags + graceful degradation instead of a delete-and-fail gauntlet. See
  `docs/handover/2026-09-06-option-b-current-context-synthesis.md`.
- **Test assets:** real Guinea CPF/RRA at
  `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\{guineacpf,guinearra}.pdf`;
  synthetic Benin fixture `tests/fixtures/synthetic_en.txt`.

## 2026-09-05 selected-country current-FCV hardening (`6ac2d57`)

- Each assessment sends one confirmed country to one bounded live-web research route.
  The route is not limited by FCV classification and never loops over other countries.
- Source selection now prefers trusted current reporting from ICG, Reuters/AP/BBC,
  approved UN/humanitarian publishers, IRC, public ACLED analysis, and approved think
  tanks. Optional mapped ICG and ReliefWeb recovery does not determine whether primary
  research is available.
- One recent substantive trusted finding can produce a reduced current update. Generic
  macro or demographic indicators remain document-limited and cannot support unrelated
  present-day FCV assertions.
- Source-bound quotes, selected-country relevance, publisher, title, URL, publication
  date, and date basis survive into review and repair. Deterministic checks reject known
  topic, direction, country, geographic-scope, modal, and negation mismatches.
- Evidence caps are applied after recency and substantive qualification, and terminal
  tier/limitation language describes the retained observations, URLs, and publishers.
- Provider-free validation passed all 1,438 tests, Python compilation, JavaScript syntax,
  and `git diff --check`. Astra and three independent Luna reviews report PASS.
- The complete synthetic browser runner passed upload, summary and detailed results, two
  assistant turns, four restored messages after refresh, mobile, and DOCX. It reported
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`; the DOCX was
  39,464 bytes with 19 valid ZIP entries.
- This checkpoint is not yet deployed and has not used the separately authorized paid
  Guinea run. Live source selection and unrestricted semantic quality remain the final
  deployed acceptance gate; a failed paid run must not be retried automatically.

## 2026-09-04 current-FCV research release (`b40ee4e`)

- Render reports exact commit `b40ee4e38366ecb47453fe299d888946657707b3` live;
  `/health` is `ok` and the root page returns HTTP 200.
- Primary research now recognizes the approved UN/humanitarian, Reuters/AP/BBC, and
  named think-tank sources while retaining strict grounded URLs and explicit dates.
- Curated recovery no longer uses World Bank macro/demographic indicators. Guinea has a
  bounded, credential-free International Crisis Group country feed; one recent
  FCV-relevant item is enough for the truthful reduced tier.
- ReliefWeb has required pre-approved application names since 1 November 2025. The
  unusable arbitrary default was removed; ReliefWeb remains optional until an approved
  value is supplied.
- Exactly one authorized paid Guinea assessment ran on the preceding deployed commit
  `0b5315c`. It completed with 60 evidence records, 5 RRA rows, 4 FCV Strategy rows,
  3 priorities with explicit FCV pathways, one repair, and a valid 46,228-byte DOCX.
  It correctly remained document-led: no current claims were accepted, no indicator API
  evidence appeared, and no unrelated present-day claim received a current citation.
  No paid assistant call or retry was made.
- The follow-up passed 343 focused tests, all 1,263 provider-free tests, syntax/diff
  checks, independent review, and the complete external browser smoke including upload,
  both result views, two assistant turns, four-message refresh restoration, mobile, and
  DOCX.
- The new Crisis Group deterministic mapping is Guinea-specific and was verified
  provider-free after the paid cycle. No second paid assessment was submitted.
- The public prototype still reports volatile storage. It remains a non-operational test
  service and must not receive confidential material.

See `docs/validation/2026-09-03-current-fcv-research-hardening.md`.

## 2026-09-03 paid-run reliability release (`3ab6020`)

- `main` and Render now include the minimal cost-control change: one default paid
  recent-news attempt, followed by the existing curated institutional recovery path.
- Final repair normalization now retains model-cleaned prohibited-policy narrative text
  while preserving application-owned assessment structure and evidence references.
- Verification passed: 1,252 provider-free tests; 147 final targeted/smoke tests; complete
  external browser smoke with eight screenshots, restored two-turn assistant history, and
  a valid DOCX; deployed health reports exact release `3ab6020`.
- One explicitly authorized paid Guinea run remains the final controlled-pilot gate. It
  must assess recent-news recovery, final repair, FCV linkage and prioritization of
  recommendations, and export quality. No paid run was made for this release.
- See `docs/validation/2026-09-03-paid-run-reliability-3ab6020.md`.

Updated 2026-09-03. Controlled pilot hardening through post-review code commit
`1fd53d7` is the latest provider-free verified local head and supersedes `9baae0c` for
current local pilot acceptance. It closes five finalization phrasing bypasses and ensures
all-enabled curated institutional timeout/provider failures propagate to
`ResearchController` safe categories rather than insufficiency. The earlier hardening
also activates curated recovery, requires explicit FCV relevance and priority ordering,
and surfaces the existing FCV rationale on summary cards. Commit `1fd53d7` has not been
deployed or provider-tested, and no paid assessment was submitted for it. The last
deployed and paid baseline remains `a52505c74d72bc08d4f973436f8b8204c76b1d0b`.
Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Render reported
`a52505c74d72bc08d4f973436f8b8204c76b1d0b` live on 2026-09-03; `/health` returned `ok`
with that exact release. The successful Guinea result contains 58 evidence records, four
priority areas, five RRA rows, and citations reaching RRA page 56. Current public research
exhausted its attempts, so the result truthfully uses the `document_led` tier and discloses
its reliance on the submitted CPF and dated 2022 RRA. The service remains the free,
volatile public test site. This is a current-evidence limitation, not a document-extraction
or schema defect. Operational
production still fails closed without SQLite persistence; the public test site can run
without a disk only through the explicit `ALLOW_VOLATILE_PROTOTYPE=true` exception.

The Five-minute readout now leads with a concise overall assessment, separate RRA/current-
dynamics and FCV Strategy readouts, and up to three linked priority measures. Detailed
analysis retains the structured driver, strategy, recommendation, target, and limitations
content while removing technical evidence disclosures from reader-facing HTML and DOCX.
Structured evidence remains available internally for validation and the follow-on assistant.

Latest local gate on 2026-09-03: post-review commit `1fd53d7` passed the complete
provider-free suite, 1,250 tests in 45.94 seconds, using a unique non-OneDrive pytest
basetemp. Python compilation, JavaScript syntax, and `git diff --check` passed. The
repository `.venv` is absent and Ruff is not installed in the configured Python 3.13
runtime, so Ruff was unavailable. The post-fix external smoke QA runner also passed end
to end with no console/page errors, two assistant turns restored across refresh, and a
successful DOCX download. The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, dedicated Project Screener-aligned holding workspace, dedicated results view, question-led note sections, collapsible evidence/coverage disclosures, correction reruns, reset, and navigation-safe DOCX download.
- Concise Five-minute readout with separate RRA and FCV Strategy synthesis, linked
  priority cards, consolidated detailed analysis, and one basis/limitations disclosure.
- Genuine streamed follow-on assistant grounded in the completed review and referenced
  evidence. It keeps at most 20 messages in the existing session store, restores after
  refresh, rejects concurrent requests, and clears history for correction children.
- Recognized uploaded RRAs/equivalent diagnostics are fully extracted within explicit
  bounds and never silently sampled. The existing diagnostic-map concept synthesizes
  drivers, resilience sources, and key risks with known, nonempty representative
  citations. Uncited pages and cross-theme citation reuse are permitted; duplicate IDs
  within an entry and unknown IDs are rejected.
- Full-diagnostic map generation targets 8-12 thematic entries while permitting up to
  20 when distinct material drivers require it. One sanitized correction call is retained
  for schema-invalid output only. The former exact-once coverage correction and requirement
  to assign every RRA page to an output entry have been removed.
- The primary CPF/CEN is the principal assessment lens. Up to ten accompanying package
  documents are reviewed in detail: they are fully re-extracted, and all retained segments
  reach the model within the 400-segment, 300,000-character, and 160,000 estimated-token
  input budgets. Exceeding a bound fails closed with the safe package-coverage category.
  The RRA and other contextual inputs provide higher-level thematic support.
- Three document buckets, country inference with confirmation fallback, explicit review stage and detail controls, safe source precedence, and detailed HTML/DOCX scope parity.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, safe failure codes,
  prohibited-language validation, thematic summary-title validation, and one bounded
  repair phase. A single internal follow-up model call is allowed only when every
  residual issue is an allowlisted mechanical guardrail violation; all other residual
  issues remain fail-closed.
- Initial `ReviewDraft` Pydantic failures receive one bounded retry without restarting
  research. The retry reuses the existing bounded payload, exposes only allowlisted and
  bounded schema locations/types, treats those diagnostics as untrusted, and propagates
  a second failure through the existing fail-closed path. Non-validation errors are not
  retried. Spec and code-quality reviews approved the implementation after a malicious
  extra-field regression was added.
- Narrative validation rejects raw evidence IDs, unsupported country FCV-list
  classifications, directional claims without current evidence, and unknown
  institutional referrals. Final repair applies an exact-boundary narrative-only raw-ID
  sanitizer while preserving structured evidence links, locators, IDs, and metadata.
- DOCX export no longer depends on an unused referral-registry hydration lookup and
  remains independently testable as a valid Word ZIP package.
- PDF extraction is text-first and bounded. Package PDFs use complete extraction within
  the package limits; contextual non-diagnostic PDFs may use deterministic full-range
  sampling with true page locators and explicit incomplete-coverage warnings. Long
  TXT/Markdown inputs are chunked across the full document.
- SQLite-backed jobs, replayable events, restart recovery, 24-hour production retention, and persistence-before-completion event ordering are implemented.
- Deterministic synthetic early-drafting, decision-review, and finalization quality cases passed as part of the automated suite. These are not a substitute for approved-material reference evaluation.
- The dedicated holding view passed browser QA at 1280px and 390px. It preserves the existing stage/timer/guidance lifecycle, has no horizontal overflow, and moves focus correctly into holding and results views.
- The controlled pilot gate on code commit `9baae0c` passed provider-free browser QA. The
  existing external runner injected the synthetic CPF and RRA, completed the result and
  detailed views, exercised two streamed assistant turns with four-message refresh
  restoration, opened the secondary correction disclosure, and downloaded the DOCX.
  It reported `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1` with
  no console or page errors. Eight full-page PNGs and one DOCX are under the unique,
  gitignored folder `output/playwright/2026-09-03-controlled-pilot-smoke-9baae0c/`.
  Visual inspection of the desktop summary, detailed view, and 390-pixel mobile summary
  found no obvious clipping, overlap, or horizontal overflow; `FCV relevance.` is
  visible on the summary card. The DOCX is a valid 39,400-byte Word ZIP/OOXML package
  with 40 paragraphs, no tables, and one section. No deployment, push, or paid API run
  was performed for this commit.
- Post-review commit `1fd53d7` supersedes `9baae0c` for current local pilot
  acceptance. It closes five finalization phrasing bypasses and routes all-enabled
  curated institutional timeout/provider failures to `ResearchController` safe
  categories rather than insufficiency. The completed provider-free external runner
  reported `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1` with no
  console/page errors; the local server was stopped. Its eight PNGs and DOCX are under
  `output/playwright/2026-09-03-controlled-pilot-smoke-1fd53d7/`. README identifies
  `a52505c` as the deployed baseline only. No deployment, push, or paid API run was
  performed for `1fd53d7`.
- The public Guinea RRA structural check confirmed that the bounded review evidence includes deep pages supporting natural-resource, legitimacy, inclusion, jobs, and conflict analysis. This is not a provider-quality result.
- The live Guinea holding view uses the Project Screener-aligned ticker, compact timer,
  singular/plural time copy, rotating phrases, and separate Render keep-awake pages
  during active quality runs. Full-page PNGs were saved for every browser attempt.
- The paid Guinea run on `90f962b` reduced six initial validation issues to one residual
  raw evidence ID and then failed closed. Commit `9816de4` deterministically fixed that
  exact residual and was deployed.
- The explicitly authorized Guinea quality run on deployed commit `9816de4` completed
  extraction, source resolution, current-country research, evidence building, and
  mapping. The initial generated review then failed schema validation with safe failure
  code `review_failed`; application validation and repair did not run. Intake, holding,
  research, drafting, and failure screenshots were saved. No result or DOCX was
  produced, and Guinea provider acceptance is not established.
- Commits `003acfb` and `1ba44bf` implement and harden the initial schema retry. The
  configured Render deployment branch points to `1ba44bf`, which Render reports live.
  The feature branch and `main` additionally include subsequent documentation-only
  commits.
- The explicitly authorized Guinea production quality run on `1ba44bf` completed on
  2026-08-31. The production API accepted the review, the result endpoint returned HTTP
  200 after approximately 11 minutes, and the DOCX export returned HTTP 200 with 49,830
  bytes. Local checks passed for the core `ReviewResult`, all 32 evidence records,
  reproducibility metadata, and application validation with zero issues. Three priority
  areas and five explicit limitations were produced. The result correctly disclosed a
  `reduced` current-evidence tier because only two recent public sources were established.
- Full browser-viewport screenshots were saved for the completed intake, initial and
  drafting holding states, Five-minute readout, and selected Detailed analysis. The
  screenshot exporter produced 800-pixel-wide PNGs while preserving the desktop layout. The
  79 KB JSON response and DOCX were also saved. The DOCX is a valid Word ZIP package with
  198 paragraphs and the expected priority and limitations sections. LibreOffice is not
  installed in the Windows environment, so DOCX-to-PNG visual QA was not available.
- The 2026-09-02 provider-free smoke-browser run passed desktop and mobile intake,
  holding, summary, detailed, streamed assistant, four-message refresh restoration,
  secondary correction, and DOCX download checks. Eight final full-page PNGs were
  visually inspected. Browser QA found and fixed one narrow issue where the country
  disappeared from the restored title. The smoke DOCX passed ZIP/OOXML and structural
  inspection (40 paragraphs, 13 headings, no tables, one section); LibreOffice remains
  unavailable for DOCX-to-PNG rendering.
- The paid Guinea cycle on deployed `cd2c57d` stopped during full-RRA diagnostic mapping
  with safe category `review_failed`; Render identified a `ValidationError`. Commit
  `894ebe5` added one sanitized schema correction attempt, passed 1,147 local tests, and
  was deployed after health/static checks.
- The single paid Guinea cycle on deployed `894ebe5` progressed through extraction and
  current-evidence research. Its schema-valid diagnostic map then failed exact-once page
  coverage and stopped as `diagnostic_coverage_unavailable`. Full-page intake, holding,
  mapping, and failure PNGs were saved and visually inspected. No result, assistant turns,
  or DOCX was produced.
- Commit `0aa6d3d` adds one coverage correction path without increasing the two-call map
  ceiling: schema correction or coverage correction consumes the same single retry slot.
  It passed 143 focused tests and the complete 1,151-test suite and was approved by spec
  and code/security review.
- The single paid Guinea cycle on deployed `0aa6d3d` passed the exact-release health and
  static-page gates, then remained in full-RRA diagnostic mapping until it failed closed.
  Render recorded `ValidationError` with safe code `review_failed`, consistent with a
  schema-invalid map after the one correction slot was exhausted. Full-page intake,
  holding, mapping, and failure PNGs were saved and the failure state was visually
  inspected. No result, assistant turns, or DOCX was produced.
- Commit `bce5bb3` adds the narrow post-cycle regression fix required by the safe-failure
  protocol. A schema-invalid second map response now fails as
  `diagnostic_coverage_unavailable` after exactly two calls, whether the correction slot
  was used for schema or coverage. It passed 168 focused tests, 36 smoke tests, and all
  1,152 local tests. It has not been deployed or provider-tested.
- Commit `095873b` makes the full-RRA map prompt compact without collapsing distinct
  drivers and gives the single coverage retry only a sanitized structural scaffold. It
  passed the complete 1,153-test suite, provider-free smoke and browser QA, and independent
  specification and code-quality review before deployment in `00d3a64`.
- The one explicitly authorized Guinea assessment on deployed `00d3a64` completed upload,
  extraction, current-country research, evidence building, and both allowed map attempts.
  It then failed closed with safe code `diagnostic_coverage_unavailable`; Render recorded
  `DiagnosticCoverageUnavailable` caused by `ValueError`. This establishes that the second
  response reached exact-once coverage validation, but the safe record does not identify
  which source IDs were missing or duplicated. Seven unique full-page PNGs were saved and
  visually inspected. No result, assistant turns, or DOCX was produced, and no retry was
  made. A local regression now covers two schema-valid but incomplete map responses and
  asserts the two-call ceiling and preserved `ValueError` cause. The post-run focused
  prompt/runtime gate passed 146 tests and the complete suite passed all 1,154 tests.
- Commits `20adf15` and `bdaa38e` replace exact-once RRA output coverage with thematic
  representative-reference validation while preserving full bounded extraction and a
  single schema retry. Commits `93b7666` and `f538434` fully extract bounded package
  documents and keep coverage warnings synchronized. Commit `087b3cc` supplies every
  retained package segment with stable evidence IDs. Commits `568d4f4` and `24a8d22`
  enforce the attention hierarchy, complete serialized-input budget, safe package failure,
  and schema-retry budget. All four task checkpoints passed independent specification and
  code-quality review.
- Commit `361fe8c` adds `missing_registry_support` to the existing one-extra-repair
  allowlist without increasing the repair-call ceiling. The single authorized Guinea
  quality assessment on that deployed commit saved intake, initial holding, research,
  mapping, drafting, and failure PNGs, then failed closed after drafting. The only current
  safe terminal event was `run_failed: review_failed`; Render classified the underlying
  error as `ValidationError`. No result, assistant exchange, correction interaction, mobile
  result, or DOCX was available for acceptance. The unchanged commit was not rerun.
- Commit `67ab97c` closes the review-schema diagnosability gap. It records only attempt
  number, issue count, allowlisted field/index paths, and normalized issue types after the
  two permitted generation attempts. It maps known model-level requirements to stable
  types, keeps the browser message generic, and stores no diagnostics in durable session
  state. Redaction tests exclude raw validation prose, rejected input, unknown field names,
  model identifiers, and document text from both events and logs. Provider-visible schema
  descriptions and review prompt version `3.0.1` now mirror the hidden narrative,
  conditional assessment, evidence-ID, and target-locator validators. The complete
  provider-free suite passed all 1,177 tests.
- Deployed commit `a52505c` passed exact-release health checks and one authorized Guinea
  quality assessment. The event stream ended in `run_complete`; one bounded application
  repair handled five allowlisted `raw_evidence_id_in_narrative` and
  `stage_length_overreach` issues, with no `repair_failed` or `run_failed` event. The
  result contract passed with 58 evidence records, four priorities, five RRA rows, and
  23 distinct RRA references. The 47,218-byte DOCX passed ZIP/OOXML and structural checks.
  Eleven unique production PNGs and the DOCX were saved outside Git. The external QA
  runner then stopped on a stale Playwright call signature and a stale locator-field
  assumption; these did not affect the application, but full two-turn production assistant
  acceptance was not completed and no second assessment was submitted.

## Validation cost protocol

Future sessions must follow the repository protocol in `CLAUDE.md`: targeted local
tests, provider-free smoke, deployed health/static checks, then at most one paid quality
run per deployed fix cycle. Do not rerun unchanged code. After a failure, use only safe
validation codes and, for `review_schema_invalid`, only the bounded sanitized attempt,
count, field/index path, and normalized-type diagnostics. Add a regression test and repeat
the no-cost ladder before another paid run is considered. Save full-page PNGs and a
successful DOCX with unique filenames; never substitute HTML for screenshots or relabel
smoke output as country-quality output.

Before any future paid submission, exercise the external runner end to end against the
deterministic smoke service, including its current Playwright keyword arguments and current
locator contract. Persist the transient assessment handle outside Git immediately after
creation so a completed run can be recovered without another provider invocation.

## Remaining considerations

1. Do not rerun deployed `a52505c`. The schema-generation path, result rendering,
   evidence integrity, and structural DOCX export are accepted for this build. Current-
   evidence richness remains limited by the disclosed `document_led` tier.
2. Use a provider-free design cycle to set an explicit Five-minute-readout concision budget
   and decide whether semantic finalization-stage calibration needs a narrower prompt or
   validator. The current three top readouts total 818 words, and some mechanically valid
   `fine_tuning` actions imply substantial delivery changes.
3. The provider-free external runner passes the two-turn assistant flow on `1fd53d7`.
   Complete full two-turn assistant production acceptance only during a later separately
   justified paid cycle; do not run another assessment solely to repair the external QA
   harness. Visual DOCX pagination also remains unverified because LibreOffice is absent.
4. Run Haiti and Benin provider acceptance only if broader cross-country readiness is needed:
   confirm Haiti's scattered jobs/IFC/MIGA treatment and Benin's multi-document coverage.
5. Keep the approved public registry current, versioned, checksummed, and
   non-confidential, and keep internal OPCS/ITS sources on a separately governed track.
6. ITS production use still requires separately approved identity, durable storage,
   authorization, audit/monitoring, authoritative source access, and
   information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Follow the API-cost validation ladder in `CLAUDE.md`; identify whether each run is
  provider-free smoke or a paid quality run.
- Run the smallest relevant tests and Ruff when available before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
