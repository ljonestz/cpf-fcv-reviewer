# Current FCV Research Hardening Design

## Goal

Make the current-country research stage return a small number of trusted, recent,
substantively FCV-relevant reports without treating generic macroeconomic or demographic
indicators as evidence of present-day conflict dynamics.

## Diagnosed causes

The paid primary search produced no retained claims because normalized claims currently
survive only when the model reproduces the provider citation URL, title, and publication
date exactly. If that exact match fails, fallback salvage accepts only a dated citation
block containing exactly one sentence. The saved production artifacts contain no raw
provider response, so they do not establish which of those gates rejected the response;
the code establishes that either route can discard an otherwise grounded report.

Curated recovery returned only World Bank GDP, population, and life-expectancy observations
because its World Bank indicator adapter is always active while its ReliefWeb adapter is
disabled when `RELIEFWEB_APP_NAME` is blank. The production result confirms that effective
configuration: all 14 current-context records are World Bank indicator URLs.

The unrelated recommendation citations arose from a separate validation rule requiring
every non-withheld priority to cite some `current-*` identifier whenever any current
evidence exists. The rule checks identifier presence, not substantive support. Reduced-tier
wording then reports distinct URLs as institutional sources, obscuring the fact that the
observations all have one publisher.

## Source scope

The provider-backed primary search will use this deliberately short public-source hierarchy:

- UN and humanitarian reporting: ReliefWeb, OCHA, UNHCR, IOM, WFP, and UNDP.
- Trusted news: Reuters, Associated Press, and BBC.
- FCV-focused analysis: International Crisis Group, ISS Africa, and the Africa Center for
  Strategic Studies.

World Bank analytical reports may remain eligible when substantively relevant, but World
Bank Indicators API observations will not qualify as current-FCV evidence. No licensed
event-level data, scraping adapter, or new dependency will be added.

## Minimal implementation

1. In primary-search normalization, use the grounded URL as the join key and restore the
   trusted title, publication date, and publisher from the provider citation metadata.
   A missing publication date remains ineligible. Extend the existing publisher/host
   allowlist and research prompt only for the agreed shortlist.
2. Remove the World Bank Indicators API adapter from curated recovery. Configure the
   existing ReliefWeb adapter with a non-secret application name and retain only recent
   reports whose titles explicitly indicate conflict, violence, political transition,
   displacement, humanitarian conditions, governance, security, peace, land conflict, or
   closely related FCV conditions.
3. Keep the existing practical threshold: one retained recent trusted report can complete
   the research stage at `reduced` tier. Broader claim, publisher, and thematic targets
   continue to govern `full` tier.
4. Remove the blanket requirement that every recommendation cite current evidence. The
   review prompt will require a current-context citation only where that source supports
   the recommendation's present-day claim. Indicator API URLs will be rejected from the
   current-FCV claim set, preventing them from becoming recommendation evidence.
5. Describe reduced coverage using separate counts for observations, distinct URLs, and
   publishers. Publisher diversity will refer only to publishers.
6. Preserve the existing prompt and validation requirements for explicit direct or
   indirect FCV causal pathways and FCV-materiality-first priority ordering.

## Testing and verification

Focused tests will be written and observed failing before each production change. They
will cover grounded-metadata normalization, the trusted-source shortlist, indicator
rejection, ReliefWeb FCV-title filtering, the one-report reduced threshold, selective
current-evidence citation, publisher-diversity wording, and the existing recommendation
ordering/rationale rules.

After targeted tests, run the complete provider-free suite and the complete external
browser smoke workflow: upload, result and detailed views, two assistant turns, refresh
restoration, mobile layout, and DOCX validation. Its title assertion will accept the
legitimate mode-controlled `CPF`, `CEN`, or `CPF / CEN` label while requiring the Guinea
country and `FCV review` suffix.

No deployment, paid assessment, provider-backed assistant call, or other external model
call is authorized. The final validation record will contain safe aggregate results only
and will not contain the assessment identifier.
