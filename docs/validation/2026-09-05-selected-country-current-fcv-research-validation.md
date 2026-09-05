# Selected-country current-FCV research validation - 2026-09-05

## Scope and method

This change was developed provider-free with focused regression tests written before
implementation. Each assessment researches only its confirmed country through one
bounded route. The route is country-agnostic and does not loop over an FCV list or other
countries.

## Root-cause diagnosis

The primary route previously lost useful grounded claims when citation normalization,
date, country, or provenance checks could not retain an exact source-bound observation.
Early source caps could also discard a useful report before substantive and recency
qualification.

Curated recovery returned World Bank indicators because that was the available
deterministic public route and acceptance emphasized publisher trust and recency rather
than whether an observation described current FCV conditions. Distinct indicator URLs
were also described as distinct institutional sources even though they shared one
publisher. The indicators were trustworthy, but they did not establish current political
transition, violence, displacement, or land-conflict dynamics.

## Implemented behavior

- Primary research accepts recent, grounded reporting for the selected country from the
  approved hierarchy: ICG, Reuters/AP/BBC, approved UN/humanitarian publishers, IRC,
  public ACLED analysis, and approved think tanks.
- One recent substantive trusted finding can produce the reduced current-update tier.
  Generic macro or demographic indicators remain document-limited and cannot substitute
  for current-FCV reporting.
- Evidence is qualified for recency and substantive FCV relevance before final source,
  finding, and payload caps are applied.
- Exact supporting text, publisher, title, URL, publication date and basis, and country
  relevance survive into review and repair.
- Deterministic validation rejects known topic, direction, country, geographic-scope,
  modal, and negation mismatches between a present-day claim and its cited evidence.
- Terminal wording separately reports retained observations, URLs, and publishers.
- Every priority still requires a direct or indirect FCV causal pathway, with materially
  stronger FCV priorities ordered first.

## Provider-free evidence

- Implementation commit: `6ac2d57`.
- Complete provider-free suite: **1,438 passed**.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Astra and three independent Luna reviews: PASS.
- Complete external synthetic browser runner:
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`.
- Browser coverage included upload, summary and detailed results, two assistant turns,
  four restored messages after refresh, mobile layout, and DOCX download.
- Smoke DOCX: 39,464 bytes, 19 valid ZIP entries, and no corrupt member.

No provider-backed call was made during implementation or provider-free validation.

## Limits and paid gate

The primary live-web route is generic for any confirmed country, while optional
deterministic feeds remain deliberately mapped only where an official usable feed is
known. A current, datable source cannot be guaranteed for every country. Deterministic
validation catches defined contradictions but is not unrestricted semantic entailment.
ReliefWeb remains disabled unless an approved application name is configured.

At this checkpoint the change is not deployed. One paid Guinea run is separately
authorized only after the exact merged commit is live and provider-free health checks
pass. It must not be retried automatically. Raw provider output, uploaded documents,
conversation content, secrets, and assessment identifiers are not tracked, and no
assessment identifier may be written to `run-state.json`.
