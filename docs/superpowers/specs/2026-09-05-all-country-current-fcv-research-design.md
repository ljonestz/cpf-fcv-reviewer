# All-Country Current FCV Research Design

## Goal

Provide the same bounded current-context research capability for any recognized country
or territory, with particular coverage of World Bank FCV and institutional-fragility
contexts. The review should use a small number of recent, trusted, substantively relevant
UN, humanitarian, news, or think-tank sources. It must remain document-led when no such
source can be established.

"All-country support" means that the system can construct, run, validate, and disclose
research for every recognized country without a country-specific code change. It does
not mean that a recent relevant publication is guaranteed to exist for every country.

## Current limitations

The current implementation does not meet that contract:

- The deterministic International Crisis Group recovery map contains only Guinea.
- ReliefWeb recovery is disabled until a pre-approved application name is supplied.
- Primary search names trusted publishers in the prompt but does not enforce them through
  the provider's `allowed_domains` setting.
- Primary-search metadata treats `page_age` as a publication date, although the provider
  defines it as the page's last-update date.
- ReliefWeb claims identify the aggregator as the publisher, so distinct underlying UN or
  institutional publishers cannot be counted accurately.

The Guinea-specific ICG feed remains useful evidence that the adapter pattern works, but
it is supplementary coverage rather than a general solution.

## Selected approach

Use three complementary layers in one bounded research stage:

1. A country-agnostic provider search restricted to approved domains.
2. ReliefWeb as the global deterministic institutional fallback once an approved
   application name is available.
3. ICG country feeds as optional deterministic supplements where ICG publishes them.

This reuses the existing gateway, claim-retention, sufficiency, and disclosure paths. It
does not add a commercial search service, scraping framework, dependency, or new paid
assistant phase.

## Source policy

The initial allowlist remains deliberately short:

- UN and humanitarian: ReliefWeb, OCHA, UNHCR, IOM, WFP, and UNDP.
- Trusted news: Reuters, Associated Press, and BBC.
- FCV analysis: International Crisis Group, ISS Africa, and the Africa Center for
  Strategic Studies.
- Existing approved multilateral and institutional analytical publishers when the item
  is substantively relevant.

World Bank analytical reports may qualify when they address current FCV conditions.
World Bank Indicators API observations and generic macroeconomic or demographic data do
not qualify as current-FCV evidence.

The provider search must pass the corresponding domains through `allowed_domains` rather
than relying on prompt compliance followed by rejection. Host and publisher validation
continues after the response as a second boundary.

## Country handling

Country handling is data-driven and shared by every source layer:

- Normalize the confirmed country or territory through one checked-in alias table.
- Store the canonical display name plus source-specific names or identifiers needed by
  ReliefWeb and optional feed catalogues.
- Cover spelling and institutional aliases such as DRC, Congo Republic, West Bank and
  Gaza, Türkiye, Côte d'Ivoire, and São Tomé and Príncipe.
- An absent source-specific identifier skips only that source. It never prevents primary
  search, changes the country, or implies that FCV conditions are absent.

The catalogue must cover all entries on the current World Bank Public FCV and
Institutional Fragility lists, plus the application's existing general country set. List
updates are data changes, not adapter changes.

## Primary-search flow

For every country:

1. Build one bounded query covering political transition and governance, conflict and
   violence, displacement and humanitarian conditions, security and peace, land and
   resource conflict, social cohesion, and material resilience or implementation risks.
2. Restrict the provider search to approved domains.
3. Retain provider-grounded URL, title, publisher, and cited narrative.
4. Normalize claims only from that grounded material.
5. Reject any claim whose URL or publisher is not consistent with the source policy.

Search-result `page_age` may be retained as diagnostic metadata but cannot establish the
publication date. A primary claim may satisfy recency only when a date is grounded in:

- explicit structured publication metadata from the source;
- an explicit date in the source-linked cited material; or
- an unambiguous publication date in the canonical source URL.

If no reliable publication date is available, the item cannot satisfy the recent-evidence
threshold. It must not be silently dated using page age, retrieval date, or model guess.

## ReliefWeb recovery

ReliefWeb is the general deterministic fallback because it supports dynamic country and
date filters across its curated report catalogue.

- `RELIEFWEB_APP_NAME` remains blank by default and must contain a genuinely pre-approved
  value in deployment configuration.
- Query the canonical country dynamically; do not maintain per-country endpoint code.
- Request the minimum fields needed for title, canonical URL, original publication date,
  ReliefWeb creation date, and underlying source.
- Use the original publication date for recency. The creation date is operational
  metadata and cannot substitute for an absent original date.
- Retain only underlying publishers on the approved source list.
- Record the underlying organization as the publisher for diversity calculations while
  preserving ReliefWeb as the distributor.
- Keep the existing bounded timeout, response-size cap, HTTPS host allowlist, redirect
  rejection, and safe provider-failure categories.

One recent FCV-relevant report can establish the reduced tier. ReliefWeb availability or
multiple URLs from one organization cannot manufacture publisher diversity or full-tier
coverage.

Obtaining an approved ReliefWeb application name is an operational prerequisite for this
global deterministic layer. The implementation and provider-free fixtures can proceed
before approval, but production readiness cannot be claimed without a successful live
API probe using the approved value.

## ICG supplementary recovery

ICG country feeds remain optional:

- Replace the Guinea-only constant with a checked-in catalogue of official ICG country
  feeds that are relevant to the supported country set.
- Catalogue entries contain only canonical country keys and official HTTPS feed URLs.
- Feed content must continue to pass bounded retrieval, content-type, XML, date, URL-host,
  and FCV-relevance checks.
- A missing feed or a feed with no recent item is normal and falls through to other
  evidence or the document-led outcome.

The application must not scrape the ICG feed index at assessment time. Feed catalogue
maintenance is an explicit, reviewable data update.

## Claim provenance and publisher diversity

The retained evidence needs to distinguish the organization responsible for the report
from the service that distributed it. Use the smallest representation compatible with the
existing claim contract:

- `publisher`: the canonical originating organization used for diversity counts.
- `source_url`: the public evidence URL.
- `distributor`: optional, set to `ReliefWeb` only for ReliefWeb-hosted reports.
- `source_date`: verified original publication date.

Direct publisher-host matching remains the default. A narrow exception permits an
approved underlying publisher on a ReliefWeb URL only when that publisher came from the
structured ReliefWeb API source field. Model-supplied publisher labels cannot use this
exception.

Reduced-tier disclosure reports observations, distinct URLs, and originating publishers
separately. Distributor count is not presented as publisher diversity.

## Substantive relevance and recommendation citations

Current evidence may be cited only by a recommendation whose present-day assertion it
supports. Relevance is evaluated against the retained title and grounded claim text, not
publisher reputation alone.

At minimum, current claims are classified into political/governance, conflict/security,
displacement/humanitarian, land/resource conflict, social cohesion, and implementation or
resilience conditions. A recommendation citing current evidence must share a material
theme or express a narrower causal link supported by that evidence.

Generic GDP, population, life-expectancy, poverty, or other background indicators cannot
establish political transition, violence, displacement, land conflict, social cohesion,
or similar dynamics. They remain background data outside the current-FCV sufficiency
calculation.

Existing requirements remain unchanged: each priority must state a clear direct or
indirect FCV causal pathway, and priorities with more material FCV relevance rank first.

## Terminal outcomes

- `full`: existing multi-claim, multi-publisher, thematic, and recency requirements are
  all met.
- `reduced`: at least one recent trusted and substantively FCV-relevant source is retained,
  but full coverage is incomplete.
- `document_led`: no qualifying recent current source is established after the bounded
  primary and deterministic paths.

The system does not automatically widen the 24-month window, substitute generic
indicators, or relabel unavailable research as sufficient. The limitation must identify
whether the gap is recency, relevance, trusted-source availability, or publisher
diversity without exposing provider content.

## Error handling and cost control

- Keep one default provider-backed research attempt and the existing total time budget.
- Deterministic fallbacks do not call a model.
- One successful source layer may survive failure in another; all enabled layers failing
  retain the existing safe provider or timeout category.
- Unsupported countries, missing optional ICG feeds, and zero qualifying results are
  insufficiency outcomes rather than configuration failures.
- A configured but rejected ReliefWeb application name is a provider/configuration failure
  and must be distinguishable in safe diagnostics from a valid zero-result response.
- No additional provider-backed assistant call is introduced.

## Provider-free acceptance matrix

Tests are written first and must cover:

1. Every country and territory on the current World Bank Public FCV and Institutional
   Fragility lists, plus representative non-FCV countries.
2. Canonical names and aliases producing valid country-specific primary and ReliefWeb
   requests without a code change.
3. Provider-side domain restriction and post-response publisher/host enforcement.
4. Rejection of `page_age` as publication evidence and acceptance of each permitted date
   basis.
5. ReliefWeb original-date precedence and rejection when only creation date is available.
6. Underlying publisher attribution through ReliefWeb and accurate diversity wording.
7. ICG catalogue availability, absence, malformed XML, stale items, unsafe URLs, and
   bounded-response failures.
8. One relevant trusted source producing reduced tier while generic indicators or
   irrelevant reports remain document-led.
9. Recommendation citation relevance and preservation of FCV pathway and ordering rules.
10. Upload, result, detailed view, two assistant turns, refresh restoration, mobile layout,
    and DOCX through the complete external smoke-browser runner.

After targeted tests, the complete provider-free suite, Python compilation, JavaScript
syntax, diff checks, and independent review must pass.

## Deployment and paid-validation gates

No second paid assessment is authorized by this design.

Before requesting approval for another paid run:

- all provider-free acceptance cases must pass;
- the source catalogue must cover the current World Bank FCV and fragility lists;
- an approved ReliefWeb application name must be configured and pass one provider-free
  live API probe;
- representative live, no-model probes must demonstrate at least one conflict setting,
  one institutionally fragile setting, and one country without qualifying evidence;
- the complete external smoke-browser runner must pass; and
- the proposed deployment diff and safe validation record must be presented for approval.

The eventual paid run should validate only behavior that provider-free evidence cannot:
primary search selection, grounded date handling, substantive synthesis, recommendation
citation fit, FCV prioritization, and rendered output quality. It must not be repeated to
compensate for a known source-configuration defect.

## Non-goals

- Exhaustive news monitoring or event enumeration.
- Licensed datasets such as ACLED.
- Scraping arbitrary publisher pages.
- A commercial news API or new dependency.
- Automatic expansion of the source allowlist.
- Claiming that every country will always have a recent qualifying report.

## Acceptance criteria

- The same research pipeline accepts any recognized country or territory without a
  country-specific code change.
- Every current claim has an approved originating publisher, trusted URL provenance, a
  verified original publication date, and substantive FCV relevance.
- One recent trusted FCV-relevant source may produce the reduced tier.
- Generic indicators and unrelated reporting cannot satisfy current-FCV coverage or
  support unrelated present-day assertions.
- Publisher diversity counts originating publishers, not URLs or aggregators.
- Missing evidence produces an accurate document-led result.
- FCV recommendation pathways and materiality-first ordering remain enforced.
- Full provider-free and browser-smoke validation passes before any request for a paid
  run.
