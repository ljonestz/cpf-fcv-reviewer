# Selected-Country Live FCV Research Design

## Purpose and scope

For each CPF/CEN review, research only its confirmed country. A Somalia CPF triggers Somalia research, not searches for all FCV countries. The application must offer this same capability for every supported country or territory, particularly low- and middle-income countries, regardless of FCV classification.

**Current status (2026-09-07):** the selected-country route, source dating, country
disambiguation, and bounded degradation described here are deployed. The latest Guinea
acceptance confirms graceful completion but found no independent current-context evidence;
source retrieval quality remains a follow-up. The model-readout fallback is context only
and does not replace live evidence.

Country catalogues and country matrices are offline development checks. They are never runtime loops or lists of countries to call during an assessment. Regional reporting may be used only where the retained excerpt concerns the selected country or an explicit spillover affecting it.

This revision incorporates Astra's review and the user's clarification. The companion implementation plan supersedes the earlier recipe and defines the work and tests. No new live-quality acceptance is claimed.

## Practical source policy

Prefer recent ICG-style conflict analysis and trusted media such as Reuters, AP and BBC. Use UN, humanitarian and other approved think-tank reporting as useful supplements. Consider the user's requested IRC and public ACLED summaries after verifying official publication domains and public access; licensed event data and authenticated datasets remain excluded.

Aim for one to three useful sources and no more than six concise findings. One trusted source containing a relevant finding is sufficient for limited current context. No mandatory corroboration, publisher diversity, exhaustive thematic coverage or review of full institutional reports is required.

World Bank analytical FCV reporting may qualify; GDP, population, life-expectancy and similar generic indicators cannot substitute for current FCV reporting. Publisher reputation alone does not establish relevance. A source labelled “news report” must still contain relevant substantive evidence.

Prefer the newest useful material. Keep a 24-month eligibility ceiling for current evidence in both holistic and RRA-update modes. Older developments since an RRA may be historical context, not proof of today's conditions. Time-sensitive assertions must respect the actual source date.

## Reusable country handling

Reuse the existing country alias registry and canonicalizer. Fill missing territories/aliases and test representative LMICs outside FCV lists as well as the current public FCV/fragility lists. Classification does not enable or disable research.

Provider-specific identifiers must be verified separately from application display names. In particular, ReliefWeb country filters must use documented identifiers/names and returned country metadata must match the selected country. Missing optional feed coverage does not prevent primary research.

## Bounded live research

Use one selected-country research stage with provider-enforced allowed domains and explicit preference for trusted media and conflict reporting. Keep the broader approved-source validation policy separate from the compact preferred search list.

Maximum budget: one initial search request and at most one existing pause continuation, three search uses across both, and one existing normalization request. Set initial search uses to two and continuation to at most one. Retain at most three sources and six findings. Source excerpts are capped at 1,500 characters each, with a 6,000-character source bundle. Start with 2,000 output tokens per model request and test adequacy for the bounded output.

Preserve the configured total deadline and pass remaining time through provider, metadata and recovery operations. Do not increase retries or add a model phase. These are ceilings, not quotas to exhaust.

Return reduced when one qualifying source is available and full coverage is absent. Do not invoke recovery merely to chase diversity or the former full-tier target. If already retrieved material satisfies full coverage, preserve full.

## Source-specific grounding and publication dates

Preserve source URL, originating publisher, title, cited excerpt, selected-country relevance, publication date and date basis together. Never flatten all narrative into a shared pool that allows any known URL to support any claim.

Use the existing normalization call to select findings and return source-bound supporting quotes. Validate quote containment against that exact source's excerpt, and bind retained factual text to the excerpt. Unknown URLs, invented quotes, swapped source attribution and missing supporting content cannot qualify.

Publication date must come from verified publication metadata, an explicit publication-labelled date in the source excerpt, or a verified publisher URL convention. Support realistic dated article slugs and opaque URLs. Never use page_age, dateModified, retrieval time, a mentioned event date or model guesses as publication date.

For an otherwise useful source without a date, permit one bounded HTTPS metadata request to that article within the three-source and time limits. Reuse httpx and stdlib parsers; enforce approved hosts, public URLs, no redirects, response content type and a 256 KiB streamed size cap. Parse recognized publication metadata only. Do not crawl links, fetch whole reports or bypass access controls.

If the date remains unavailable or conflicting, skip that source for current qualification and record a safe reason count. Other sources can succeed.

## Optional recovery

ICG country feeds supplement primary research where official feeds exist. Maintain a checked-in catalogue verified against the official RSS index; do not scrape it at assessment time. Preserve useful short descriptions/summaries and original dates. Validate country relevance, especially for shared regional feeds.

ReliefWeb is an optional distributor. Enable its API only with an approved app name and verify its country-filter contract. Retrieve bounded summary/body material, original publication date, origin organization and URL. Creation date cannot replace original date.

Attribute ReliefWeb evidence to an approved originating publisher and retain ReliefWeb as distributor. The exception allowing an origin publisher on a ReliefWeb URL is application-owned and cannot be minted by model output. Multiple names on one jointly published report do not constitute independent corroboration.

A generic report title is a lead, not evidence for its unobserved contents. A title can support only the narrow finding it explicitly states. If no usable summary/finding is available, skip it. Missing, empty or inaccessible optional feeds do not disable independent news research.

ReliefWeb approval is a prerequisite for ReliefWeb itself, not for the whole application.

## Recommendation support and FCV priorities

Current citations must support the recommendation's actual present-day assertion: condition, direction, country and time. Political-transition reporting cannot automatically support land-conflict claims; demographic observations cannot prove violence.

Carry source-bound excerpts and provenance into existing review and repair calls. Add only the minimal internal support record needed to associate an evidence ID, supporting quote and asserted condition. Validate IDs, quote provenance and mechanically identifiable mismatches. Preserve expert-reviewed fixtures for cases requiring semantic judgment.

A topic match or exact quote alone is not proof of entailment. Deterministic checks cannot guarantee unrestricted semantic correctness or optimal ranking. Prompt-string tests must not be presented as evidence that these properties are solved.

Every priority retains a clear direct or indirect FCV causal pathway. More materially FCV-related priorities rank first. Existing repair-call limits remain unchanged.

## Outcomes and diagnostics

- Full: already retrieved evidence meets existing broader coverage conditions.
- Reduced: at least one recent trusted source contains a substantive country-relevant finding.
- Document-led: no qualifying current finding survives the bounded process.

Describe observations, distinct URLs and originating publishers separately. Limited scope is not failure to meet mandatory corroboration. Never label generic indicators as sufficient current evidence.

Record only safe fixed-key counts and reason categories for candidates, source-linked excerpts, date failures, source-policy rejection, country mismatch, background/non-FCV content, normalization failure and accepted sources. Never store assessment IDs, raw provider output, document text or arbitrary error prose in validation records.

## Verification and approval

Use realistic sanitized response replays and behavioral fixtures before implementation changes. Cover selected-country-only calls, broad offline country support, date formats, opaque URLs, source/claim swaps, generic data under misleading labels, irrelevant reporting, stale RRA-gap evidence, source attribution and exact request ceilings.

Then run focused tests, full provider-free suite, static checks and the actual smoke-browser runner using its --output option. Verify upload, result, detail, two assistant turns, four-message restoration, mobile and DOCX. Synthetic smoke is not country-quality acceptance.

Astra reviews the implementation diff. Record actual outcomes and residual limitations in a dated safe validation record, then present the concrete PR before deployment or further paid approval. No second paid assessment is authorized by this design.

No-model public endpoint probes may establish accessibility and metadata behavior; they do not establish live model selection or synthesis quality. A later separately approved bounded assessment addresses those remaining uncertainties. Do not require a real country to have no recent news to test empty-result behavior.

## Non-goals and limits

No exhaustive monitoring, all-country runtime sweep, new commercial news service, repeated corroboration, licensed datasets, full-report ingestion, runtime feed-index scraping or extra model stage.

The design cannot guarantee a recent accessible publication for every country. Where none qualifies, the review must disclose its document-led basis.
