# Research Resilience and Guided Journey Design

**Date:** 2026-08-14

**Status:** Approved for implementation planning

**Branch:** `feat/mvp-review-run`
**Applies to:** CPF FCV Reviewer only

## 1. Purpose

Make a valid CPF/CEN review complete reliably when live country research is malformed, temporarily unavailable, or thinner than the preferred evidence standard. At the same time, replace the compact in-page progress treatment with a dedicated, calm guided journey that explains what the system is doing and how long it is likely to take.

The immediate production defect is that Anthropic web-search responses contain several content-block types, but the gateway concatenates every text block and parses the result as one JSON document. Two observed Benin runs therefore reached `research_malformed` even though the provider had returned HTTP 200 responses. An uploaded RRA changes the research request and time window, but it does not currently provide a recovery path when the independent research payload is malformed.

## 2. Product principles

- A temporary research-provider or formatting problem must not discard an otherwise valid review.
- Independent current evidence remains preferred and must be distinguished from uploaded-document evidence.
- The app must never represent uploaded material as independently retrieved research.
- Reduced evidence must produce a visible, specific limitation, not a hidden lowering of standards.
- A review should stop only when it cannot be produced responsibly, such as invalid inputs, no usable document evidence, or a complete generation failure.
- Public sources only. Licensed ACLED data, social media, blogs, and unverified media are excluded.
- No source claims, document text, filenames, provider internals, or sensitive diagnostics are sent through progress events.
- The smallest repository-consistent solution is preferred; no new paid provider or durable data store is introduced.

## 3. Chosen approach

Use a layered research pipeline rather than a parser-only patch or a multi-provider architecture.

### 3.1 Layer 1: cited web research

The existing Anthropic web-search call remains the primary research mechanism, but its response is handled as a structured sequence of provider content blocks.

The gateway will:

1. Accept preamble text, `server_tool_use`, `web_search_tool_result`, final cited text, and provider tool-error blocks.
2. Detect and continue a `pause_turn` response within the existing total time budget.
3. Preserve source title, URL, publication date or page age, and citation relationships from search results and cited final text.
4. Select the final answer text deliberately rather than concatenating unrelated text blocks.
5. Return a provider-neutral research artifact containing narrative text, source records, citations, and diagnostics safe for server logs.

Provider tool errors are classified separately from malformed normalization output. Raw provider payloads and searched document content are not logged.

### 3.2 Layer 2: structured normalization

A second Anthropic call, without web search or citations enabled, converts the provider-neutral research artifact into the existing validated current-context claim schema. It uses structured output and a wrapper model around the claim list.

The normalization prompt may use only evidence included in the primary artifact. Every normalized claim must retain a resolvable source relationship. Claims without a public source URL, relevance statement, supported relationship, or permitted source type are rejected by the existing policy filter.

This separation is necessary because cited web search and guaranteed structured output cannot be combined in one Anthropic request.

### 3.3 Layer 3: citation-preserving salvage

If the normalization call fails or returns an invalid object, the application derives conservative claims directly from valid cited search results and their associated final text. Salvage must not infer details absent from the retrieved material. It can retain fewer claims than the preferred threshold and passes them to the tiered sufficiency decision.

### 3.4 Layer 4: curated public-source recovery

If the primary search itself is unavailable or yields no usable public source, a no-key recovery path queries a small allowlisted set of institutional endpoints. The initial implementation should include only endpoints verified during implementation and covered by contract tests, with the expected hierarchy:

1. World Bank and United Nations sources.
2. OECD, IMF, regional development banks, ICRC, IOM, and comparable institutional publishers.
3. Public humanitarian and conflict-report repositories such as ReliefWeb when their official API and terms are verified.

Network access is restricted to fixed HTTPS hosts, with connection/read timeouts, response-size caps, content-type checks, and existing public-URL validation. Recovery results go through the same source-policy filter and claim schema. A failure in one adapter does not abort the remaining adapters.

The World Bank Indicators API can contribute recent structural and development indicators without credentials. It is supplementary rather than sufficient on its own for current conflict or political developments.

## 4. Evidence sufficiency and completion policy

The hard four-claim/two-publisher gate becomes a tiered decision. The preferred dimensions remain structural or dynamic context, current development, and fragility/conflict implications.

### Full evidence

- Meets the preferred claim, publisher, dimension, and recency thresholds.
- Produces the normal note with ordinary source disclosure.

### Reduced independent evidence

- Contains at least one usable recent independent public source and enough grounded material to avoid unsupported current-country assertions, but misses one or more preferred diversity thresholds.
- Produces the note with a concise evidence-limitation statement identifying the missing dimension or diversity, without exposing provider errors.
- Unsupported current claims are omitted rather than filled by model knowledge.

### Document-led context

- Independent current evidence is unavailable after bounded primary and recovery attempts, but the submitted CPF/CEN package and any supplied RRA contain sufficient country context for a useful review.
- Produces the review, clearly labels the context as document-led, records the date or period covered by the documents, and states that current independent verification was limited.
- The RRA remains an uploaded source and is never relabelled as live research.
- Recommendations that depend on unverified recent developments are qualified or omitted.

### Blocking failure

The run fails only when responsible output is impossible: invalid or unreadable required inputs, no usable country-context evidence in either documents or research, policy-validation failure that cannot be safely downgraded, or review-generation failure after bounded retry.

The final result model records the evidence tier and limitation reason so the DOCX, browser result, audit metadata, and correction flow remain consistent.

## 5. Retry and time-budget behaviour

- Retain bounded retries and the existing overall research budget.
- Retry only errors likely to recover: transient transport failures, provider overload, `pause_turn`, and normalization format failures.
- Do not repeat a request rejected for policy reasons without changing the inputs.
- Apply short jittered backoff within the total budget.
- Move to salvage or curated recovery as soon as retrying the same failure mode is unlikely to add value.
- Deduplicate sources and claims across attempts using normalized URL and stable content keys.
- Cancellation and browser-side retry continue to create clean run lineage; superseded run artifacts remain purged according to the existing correction-lineage policy.

## 6. Guided journey user experience

Selecting **Start review** transitions from intake to a dedicated full-page progress view. The selected visual direction is **Option A: Guided journey**.

### 6.1 Page structure

- Header: `Building your FCV review`, country name, elapsed time, and approximate remaining time.
- Three-stage rail:
  1. Reading documents
  2. Establishing current country evidence
  3. Drafting and validating the review
- Active-stage panel with one short, plain-language status.
- Rotating `While we work` cards with light, useful FCV-review messages.
- Quiet secondary actions for cancellation or returning to intake where existing run semantics allow them.
- Automatic transition to the separate results view on completion.

### 6.2 Timing

The interface shows elapsed time continuously. Estimated remaining time is stage-aware and explicitly approximate. Initial estimates use conservative configured stage ranges; as stages complete, the estimate is recalculated from actual elapsed time and the remaining ranges. It never counts down to zero while work is still running and never promises a fixed completion time.

### 6.3 Status messaging

Messages describe activities rather than internals, for example:

- `Reading the submitted strategy and context material`
- `Checking recent public country evidence`
- `Cross-checking evidence across institutional sources`
- `Working from the submitted evidence while live sources recover`
- `Drafting findings and validating citations`

Recovery messaging is informative but non-alarming. Provider names, exceptions, prompts, filenames, extracted passages, URLs, and claim text are forbidden in SSE progress payloads.

### 6.4 Motion and accessibility

- Use restrained opacity/translation transitions and a soft active-stage pulse.
- Honour `prefers-reduced-motion` by removing rotation and nonessential animation.
- Preserve keyboard navigation, focus visibility, semantic headings, live-region announcements, and sufficient contrast.
- At mobile width, stack timing and stage details without horizontal scrolling or overlapping controls.

## 7. Result presentation

The results view remains distinct from progress. It adds a compact evidence-status treatment:

- `Current evidence established` for full evidence.
- `Current evidence partially established` with the specific limitation for reduced evidence.
- `Review based primarily on submitted documents` for document-led context.

The generated DOCX carries equivalent wording. Source lists identify uploaded and independently retrieved sources separately.

## 8. Smoke and quality modes

“Free smoke application” is implemented as a provider-free deterministic smoke path for development and browser QA, not as a hidden production bypass.

- Smoke mode uses synthetic/public fixtures and exercises intake, upload validation, SSE progression, all three progress stages, result rendering, correction, and download without paid provider calls.
- It is enabled only through explicit development/test configuration and is visibly identified outside production.
- Production continues to use real providers and approved public-source recovery.
- One paid Benin quality run may be performed only after focused tests, the complete automated suite, linting, syntax checks, and repeated smoke runs pass.
- The supplied package can be used for a real run only after confirming that each uploaded file is approved/public and country-consistent. The folder currently mixes a Benin RRA with Burkina Faso CPF material, so it must not be treated as one Benin package without deliberate file selection.

## 9. Testing strategy

Implementation follows test-driven development.

### Unit and contract coverage

- Mixed provider content blocks and final-text selection.
- Citation and source-metadata extraction.
- `pause_turn`, web-search tool errors, timeouts, and malformed output.
- Structured normalization success and validation failure.
- Citation-preserving salvage.
- Curated adapter host restrictions, timeout, size, schema, and partial failure.
- Claim deduplication and source-policy enforcement.
- Full, reduced, document-led, and blocking sufficiency decisions.
- RRA recognition, date handling, and country mismatch.
- Evidence-tier propagation into browser, DOCX, audit, and correction lineage.
- SSE privacy allowlist.

### Browser coverage

- Repeated deterministic smoke runs at 1280px and 390px.
- Stage changes, timer behaviour, rotating cards, reduced motion, retry, cancellation, and final transition.
- Full-, reduced-, and document-led result states.
- No clipping, overlap, stale progress, or sensitive event text.

### Completion checks

- Focused new tests pass.
- Full pytest suite passes.
- Ruff, JavaScript syntax, and `git diff --check` pass.
- Generated DOCX is rendered and visually inspected with the available documented fallback.
- A dated validation record captures commands, browser scenarios, evidence tier, provider use, limitations, release identifier, and deployment state.

## 10. Observability and privacy

Server logs use stable failure and recovery codes such as `research_provider_error`, `research_normalization_error`, `research_salvaged`, `research_curated_recovery`, and `research_document_led`. Logs may include attempt number, stage duration, counts, evidence tier, and exception class. They must not include document text, prompts, claim text, raw model responses, credentials, or non-public URLs.

Run metrics should make it possible to distinguish successful primary research from salvage, curated recovery, and document-led completion. This supports production diagnosis without introducing persistent user-content storage.

## 11. Deployment and acceptance

Implementation is production-ready when:

- The malformed-response defect is covered by a reproducing test and fixed.
- A valid review no longer fails merely because preferred research diversity is unavailable.
- Evidence limitations are accurate and visible in browser and DOCX outputs.
- Guided journey progress works on desktop and mobile and exposes no sensitive data.
- Provider-free smoke runs are repeatable.
- All automated and visual checks pass.
- The feature branch is pushed and the intended Render service is verified against that exact commit; a successful push alone is not treated as deployment.

No deployment, paid quality run, or upload of non-public material is implied by approval of this design. Those actions occur only during the verified implementation workflow and within available credentials and access.
