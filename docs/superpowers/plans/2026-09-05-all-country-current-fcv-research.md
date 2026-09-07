# Selected-Country Live FCV Research Implementation Plan

> **For agentic workers:** Use test-driven implementation task by task, following Ponytail: reuse existing code and add only what a failing behavior test requires. Steps use checkbox (`- [ ]`) syntax.

**Goal:** For one CPF/CEN review, obtain a small amount of recent trusted FCV reporting about its confirmed country and use it accurately in the review. The same pipeline must work for any supported country, particularly low- and middle-income countries.

**Architecture:** One selected-country research stage, with trusted media and ICG-style reporting preferred, short source-specific excerpts preserved, and optional institutional recovery. One substantive recent source is sufficient for limited current context. Country catalogues and broad country test matrices are offline coverage checks, never runtime search loops.

**Tech Stack:** Existing Python, Pydantic, httpx, pytest, Flask and Playwright; stdlib date, URL, JSON and HTML parsing. No new dependency, provider, crawler framework, model phase, or production country-classification system.

## Current status (2026-09-07)

The selected-country search and provenance improvements in this plan were implemented and
deployed through PRs #11/#12/#13 and the subsequent current-context releases. The plan
remains a historical implementation record. Genuine Guinea current-source coverage is
still incomplete: the deployed acceptance retrieved no independent current-context
evidence and used the bounded context-only readout fallback. See
`docs/validation/2026-09-07-guinea-acceptance.md` for the live outcome.

---

## Status and scope

Revised after Astra's review and the user's clarification. This replaces the earlier implementation recipe, including its invalid smoke command, invented test helper/file, title-only recovery, exact source-type indicator guard and mandatory ReliefWeb gate.

This document is an implementation specification, not evidence that the fix passes or retrieves useful live news. Implementation, provider-free replay tests and full smoke validation remain outstanding. Deployment and a further paid assessment require separate approval after the evidence is presented.

A Somalia review searches Somalia. It does not search Guinea, every FCV country, or every country in the catalogue. A regional source is usable only for the excerpt that explicitly concerns Somalia or a documented spillover affecting Somalia.

The practical target is one to three useful sources, with up to six short findings. This is not a requirement to find three sources, cover every theme, or corroborate one trusted report through other publishers. Prioritize the newest useful reporting; a 24-month eligibility ceiling is not a claim that a two-year-old report describes today's conditions.

## Files and responsibilities

- `src/cpf_fcv_reviewer/country_detection.py`, `tests/test_country_detection.py`: shared aliases, missing supported territories, country normalization.
- `src/cpf_fcv_reviewer/public_research.py`, `tests/test_public_research.py`: search restrictions, source-specific excerpts, date provenance, bounded metadata retrieval, normalization and safe rejection counts.
- `src/cpf_fcv_reviewer/curated_research.py`, `tests/test_curated_research.py`: optional ICG/ReliefWeb recovery, useful summary content, origin attribution and source-specific country identifiers.
- `src/cpf_fcv_reviewer/research_controller.py`, `tests/test_research_controller.py`: practical stop condition, recency, deadlines and disclosure.
- `src/cpf_fcv_reviewer/contracts.py`, `src/cpf_fcv_reviewer/validators.py`, `tests/test_contracts.py`, `tests/test_validators.py`: narrowly scoped source-support contract where existing evidence IDs cannot express the link.
- `prompts/public_research.md`, `prompts/review.md`, `prompts/repair.md`: preferred reporting, excerpt selection, recommendation support, preserved FCV pathways and ordering; version through existing repository conventions.
- `src/cpf_fcv_reviewer/runtime.py`, `tests/test_runtime_wiring.py`: carry source provenance into review evidence without flattening or losing it.
- `scripts/run_smoke_browser.py`, `tests/test_smoke_mode.py`: existing synthetic end-to-end flow; change only for demonstrated contract failures.
- `docs/PROJECT_STATUS.md` and a new dated record under `docs/validation/`: actual safe aggregate results and limitations.

Work on a `codex/` feature branch in an isolated local worktree based on the reviewed design branch or updated main. A documentation merge is not a prerequisite for starting implementation. Inspect local/remote state and preserve unrelated work first. Use apply_patch; if Windows Application Control blocks it, use the authorized GitHub contents workflow on the feature branch and fast-forward locally. Never use shell file-write workarounds.

## Task 1: Prove selected-country scope and broad input coverage

- [ ] Add parameterized tests using the existing country registry and its aliases, including Somalia, Guinea, DRC, Republic of Congo, West Bank and Gaza, Kosovo, Türkiye, Côte d'Ivoire and São Tomé and Príncipe. Include LMIC examples outside FCV classifications, such as India, Indonesia, Vietnam, Kenya and Brazil. Classification membership must not control whether research runs.
- [ ] For each input, use fake gateways and assert the request contains only that canonical country. For Somalia, assert one research-controller invocation, no loop over registry entries, and no calls for unrelated countries. Regional report fixtures must bind their retained excerpt to the selected country.
- [ ] Run the new tests and confirm failures identify missing aliases or request behavior, rather than missing invented helpers.
- [ ] Reuse the existing canonicalizer; expose it only if needed by other modules. Add missing names/aliases without duplicating the registry. Keep display names separate from provider-specific IDs or names.
- [ ] Add an offline source-coverage table showing primary search available for every supported country, optional ICG feed availability, and ReliefWeb mapping availability. Include all entries in the current publicly available FCV/fragility lists as regression cases, with provenance date. Those lists are test inputs, not application eligibility rules.
- [ ] Run country/runtime tests; commit only the scoped change.

## Task 2: Prefer useful reporting and bound actual cost

- [ ] Capture real request arguments through existing fake clients. Assert a selected-country query, explicit `allowed_domains`, and a preference for ICG, Reuters, AP and BBC reporting. UN and other approved think-tank/humanitarian reporting are supplementary choices, not mandatory searches.
- [ ] Keep one broad validation allowlist, but use an explicit compact preferred search-domain list. Preserve existing approved analytical publishers as secondary options within the same bounded research stage. Do not start with generic development indicators or require every theme.
- [ ] Include IRC and public ACLED analysis in the source-policy implementation after verifying their official public publication domains and accessible reporting routes. The user authorized considering their summaries; this does not authorize licensed event data, authenticated endpoints or bulk datasets. Verify host/publisher matching for each new public source.
- [ ] Make these ceilings explicit and test them: one research attempt; one initial search request plus at most one existing pause continuation; at most three search uses across both; one existing normalization request; at most three retained source records and six findings. Initial search uses should be limited to two, leaving at most one for continuation. Keep existing configured total time budget and propagate remaining time to every operation.
- [ ] Cap source excerpts at 1,500 characters each and the selected-country source bundle at 6,000 characters. Cap synthesis/normalization output to the amount needed for six findings (start at 2,000 output tokens per request). Fail or disclose truncation when a bound prevents a usable finding; never silently cut a sentence into stronger evidence.
- [ ] Add request-count tests for ordinary success, pause continuation, malformed normalization, primary failure and optional recovery. No SDK retries, extra assistant phase or country fan-out.
- [ ] Run red tests, implement the narrow request/prompt changes, run green tests and commit.

These are maximums, not targets to exhaust. Search metadata and trusted excerpts remain untrusted content: they supply facts, never instructions.

## Task 3: Preserve source-specific evidence and establish publication dates

- [ ] Add sanitized replay fixtures shaped like complete provider responses: web-search results, text blocks, citations and stop reasons. Use synthetic content with realistic structure, and label it synthetic. Reuse approved public fixtures where available; never retrieve rejected private model output.
- [ ] Cover Reuters-style `headline-2026-08-30/` URLs, `/2026/08/30/` paths, opaque AP/BBC URLs, ISO timestamps, explicit source publication dates, conflicting dates, missing dates and a fresh page_age on an old article. A title or date rewritten by normalization must not erase valid grounded metadata.
- [ ] Preserve each source's URL, canonical publisher, title, cited excerpt(s), publication date and date basis. Do not send only a concatenated narrative plus an unrelated URL list to normalization.
- [ ] Add a `supporting_quote` to normalized research claims if the existing contract cannot carry it. Verify normalized whitespace quote containment against the excerpt for that exact source URL. Bind the retained factual text to that quote/excerpt; do not accept an arbitrary model paraphrase just because the URL exists elsewhere in the bundle.
- [ ] Test swapped sources: a Reuters political-transition excerpt cannot support a land-conflict finding taken from another source; an excerpt with no selected-country connection cannot qualify. Test fabricated quotes, unknown URLs and missing excerpts.
- [ ] Resolve dates from verified source publication metadata or an explicit publication-labelled date in the source excerpt. Accept a canonical URL date only where the publisher's URL convention is verified; distinguish date-like IDs, mixed separators and dates merely mentioned in headlines. Never use page_age, retrieval time, event date or model guess as publication time.
- [ ] For an otherwise useful source with an opaque URL and no date in the cited material, perform at most one bounded HTTPS metadata request to that article, within the three-source and total deadline caps. Reuse httpx; allow only approved publisher hosts, reject redirects and credentials/private addresses, validate content type, stream-cap the response at 256 KiB, and parse only recognized article publication metadata (for example JSON-LD datePublished or article:published_time). Ignore dateModified. Do not fetch a full report or crawl links.
- [ ] If metadata retrieval is blocked, paywalled, malformed, conflicting or undated, skip that source for current-evidence qualification and record only a safe reason count. Other sources may still succeed.
- [ ] Make the same provenance checks apply to the salvage path. A source-linked assistant narrative alone is not a verbatim source excerpt.
- [ ] Run red replay tests, implement the smallest helpers inside the existing research module, rerun the replay suite and commit.

Quote containment establishes provenance, not semantic entailment. The next task must address what the evidence actually says.

## Task 4: Make optional recovery useful and truthful

- [ ] Add recovery fixtures for a specific dated finding, a generic title with a useful summary, a generic title without content, an old report newly uploaded to ReliefWeb, unknown origin, multi-origin report, wrong country, empty response, malformed feed, timeout and denied app name.
- [ ] For ICG, retain a bounded RSS description/summary when available, strip markup with stdlib handling and preserve its source URL/date. A title may qualify only for the narrow factual proposition it explicitly states; “Somalia humanitarian update” is a lead, not a finding.
- [ ] Expand the checked-in ICG feed catalogue using the verified official RSS index from the design review. Confirm each country/feed pairing, including combined regional feeds; do not invent feed IDs or scrape the index during assessment. Missing or inaccessible feeds are normal optional-source outcomes.
- [ ] For ReliefWeb, verify the API's country-filter contract and use structured country IDs or exact documented names, not the assumption that the application's canonical name always matches. Include DRC/Congo, Palestine and small-island fixtures. Query selected-country reports only; validate returned country fields.
- [ ] Request original publication date, source organization, title, URL and a bounded useful body/summary. Filter by original date; creation date cannot substitute. Remove any empty/invalid source filter found in the existing query.
- [ ] Set publisher to the approved originating organization and optional distributor to ReliefWeb. Multiple organizations on one report must not manufacture independent corroboration; use one deterministically selected approved origin for the current single-publisher contract and disclose joint attribution if needed.
- [ ] Keep the ReliefWeb host exception application-owned: provider normalization cannot mint distributor provenance. Strip model-supplied distributor values before validation; test this using a forged publisher/distributor on an unrelated host.
- [ ] Preserve existing network/security/time/size bounds and deterministic deduplication. No new model call for recovery. Retained content must state a finding; if its relevance cannot be established within the bounds, leave it as an unused lead.
- [ ] Run red recovery tests, implement, run green tests and commit.

ReliefWeb requires an approved app name only to enable ReliefWeb. Its absence cannot disable primary news search, ICG, other approved sources, or readiness of the independent route.

## Task 5: Enforce practical sufficiency, recency and recommendation support

- [ ] Add behavioral controller fixtures showing one recent relevant trusted finding produces reduced; generic GDP/population/life-expectancy data produce document_led even when labelled “news report”; irrelevant recent reporting cannot qualify; several URLs from one publisher remain one publisher.
- [ ] Derive topic/relevance from the grounded excerpt rather than source_type or publisher reputation alone. Use a small explicit set of material themes (political/governance, conflict/security, displacement/humanitarian, land/resource conflict, social cohesion, implementation/resilience). In the existing normalization call, require an excerpt-backed topic and selected-country relevance. Treat uncertain cases conservatively. Do not build a scoring framework or pretend keyword overlap proves support.
- [ ] For deterministic recovery, require a specific FCV finding in the retained title/summary, not just a keyword in a publication label. Add negative fixtures such as energy transition, population growth, generic protection announcements and report titles with no asserted condition.
- [ ] Apply the same current-evidence recency ceiling in holistic and RRA-update modes. Material since an old RRA may be historical context, but a 2023 report cannot count as a current update in September 2026. Prefer the newest useful reporting; preserve date and qualify time-sensitive assertions accordingly.
- [ ] Return reduced immediately when primary research provides one qualifying source but full coverage is absent. Do not run recovery or another provider search solely to chase diversity. If already retrieved sources satisfy full coverage, preserve full.
- [ ] Keep observations, URLs and originating publishers distinct in limitation text. Describe limited scope without implying a one-source update failed a mandatory corroboration requirement.
- [ ] Preserve source excerpts/provenance through build_evidence into the existing review-generation and repair payloads. Add an internal support record for each current citation only if necessary: evidence ID, supporting quote and the present-day assertion it supports. Validate IDs, quote provenance and known topic incompatibilities. Do not expose this internal verification record in reader-facing prose.
- [ ] In the existing review and repair calls, require the quoted finding to support the asserted condition, direction, geography and time. Do not infer land conflict from a political-transition report or worsening violence from generic population data. Require every priority's direct/indirect FCV pathway and materiality-first ordering as before.
- [ ] Add complete result fixtures for supported and unsupported current citations, including a valid quote attached to an unrelated assertion, reversed direction, wrong country, stale date and a claim broader than its excerpt. Assert the relevant existing validation/repair path rejects mechanically identifiable mismatches without increasing its call ceiling.
- [ ] Document the residual limit: deterministic checks cannot prove unrestricted natural-language entailment or optimal priority ordering. Use a small expert-reviewed fixture rubric and later approved live output review for those judgments. Prompt-string assertions and synthetic model stubs are not semantic validation.
- [ ] Run red tests, implement only demonstrated gaps, rerun the focused controller/contract/runtime/validator tests and commit.

Do not make up a “semantic validator” that always passes because topic words overlap. If a fixture exposes a mismatch beyond deterministic enforcement, explicitly identify it as a model-quality acceptance case rather than claiming the test proves it solved.

## Task 6: Add safe diagnosis for any remaining zero-evidence outcome

- [ ] Replay zero-result and rejected-result responses and assert safe aggregate counters for: source candidates, source-linked excerpts, missing publication date, untrusted host/publisher, country mismatch, non-FCV/background content, accepted sources and normalization failure.
- [ ] Preserve existing safe event/log patterns. Never log source prose, raw model response, document text, assessment identifier or arbitrary exception text. Counters must be fixed-key integers and reasons allowlisted.
- [ ] Distinguish empty successful responses from unavailable sources/timeouts. A surviving source succeeds despite another optional route failing.
- [ ] Test the controller's final accepted counts and reason categories end to end with replayed provider responses; do not test parsers in isolation only.
- [ ] Commit after the focused red/green cycle.

These counters address the previous inability to identify which acceptance gate removed every primary claim without storing sensitive provider output.

## Task 7: Complete the provider-free ladder and exact smoke runner

Run focused tests first with a fresh temporary base directory. Use the existing Python environment; do not install dependencies merely to satisfy a planned command.

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_country_detection.py tests/test_public_research.py tests/test_curated_research.py tests/test_research_controller.py tests/test_runtime_wiring.py tests/test_contracts.py tests/test_validators.py tests/test_adversarial.py tests/test_prompt_guardrails.py tests/test_smoke_mode.py -q -p no:cacheprovider
~~~

- [ ] Confirm the focused suite passes and all model/network dependencies are stubbed in provider-free tests.
- [ ] Run the complete suite once after the final code change:

~~~powershell
C:\WBG\Python313\python.exe -m pytest -q -p no:cacheprovider
C:\WBG\Python313\python.exe -m compileall -q src tests scripts
git diff --check
~~~

- [ ] Run JavaScript syntax checking with the available Node executable and Ruff only if already installed. Record unavailable checks accurately.
- [ ] Inspect the actual smoke-mode app factory/config and launch the existing Flask smoke service locally with provider credentials unused. Confirm smoke mode before upload.
- [ ] Execute the actual runner interface:

~~~powershell
C:\WBG\Python313\python.exe scripts/run_smoke_browser.py --base-url http://127.0.0.1:58422 --output output/playwright/2026-09-05-all-country-current-fcv-smoke
~~~

Use a unique suffix if the output folder already exists. The verified runner accepts --output, not --output-dir, and its synthetic country is Benin. Do not invent test_external_qa_runner.py or assert_title.

- [ ] Verify upload, result, detailed view, two assistant turns, four restored messages after refresh, mobile, DOCX integrity and no page/console errors. Expected runner marker: BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1.
- [ ] Inspect the existing mode-controlled title assertion; keep CPF, CEN and CPF / CEN compatibility using the actual selected country. Change it only if a regression demonstrates failure. Inspect screenshots and stop the local server.
- [ ] Review the full diff, dependency list, call counts and sanitized artifacts. No unrelated changes or assessment identifier may enter Git.

Expected test outcomes are targets, not observed results. Record actual counts and failures.

## Task 8: Review, record and present the concrete implementation

- [ ] Have Astra review the implemented diff against this corrected plan, especially source/date provenance, selected-country scope, semantic limits and actual request ceilings.
- [ ] Resolve evidence-backed findings and rerun only affected checks; repeat the full suite after material code changes.
- [ ] Add a new dated safe validation record with exact code commit, actual test counts, smoke results, offline country coverage, call ceilings, source routes tested and remaining live uncertainties. Update PROJECT_STATUS without rewriting historical records.
- [ ] Push the feature branch and open/update its PR with the concrete final behavior and validation. Inspect staged diff and confirm no IDs, credentials, raw documents or raw model content.
- [ ] Present provider-free evidence before deployment or paid approval. Optional no-model source probes may verify official public endpoints, bounded metadata extraction and publication fields; fixtures must cover valid zero-result behavior without requiring a real country to have no news.
- [ ] Keep ReliefWeb disabled until its own approved app name and live API probe are available. This does not block acceptance of independent trusted-news/ICG routes.
- [ ] Do not submit another paid assessment or provider-backed assistant call in this implementation cycle. A separately approved later run tests remaining live selection, synthesis and recommendation-quality uncertainty, not defects already detectable offline.

## Acceptance and remaining limits

Ready for implementation means the workflow, contracts, failing cases, budget and verification path are explicit. Ready for deployment requires the implemented diff and provider-free evidence. Actual live retrieval and semantic review quality remain unproven until separately approved live validation.

Required behavior: one selected country per assessment; reusable coverage across supported LMICs; a small trusted source set; one useful recent source sufficient; no indicator substitution; actual source findings preserved; citations bounded by their support; clear FCV pathways and materiality-first ordering; truthful source/date/diversity disclosure; bounded cost; complete provider-free and browser acceptance.

No guarantee is made that a current publication exists, is accessible, or can be dated for every country. When none qualifies, return an honest document-led review.
