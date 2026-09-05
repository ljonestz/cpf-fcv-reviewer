# Guinea production follow-up on selected-country research - 2026-09-05

## Scope and paid-run outcome

Render reported merged commit `01dc9392801eb3849864cf69777b4337988436ee`
live, and no-cost health and root-page checks returned HTTP 200. One authorized Guinea
assessment was then submitted. This used the release's single paid allowance. No
provider-backed assistant call or automatic retry was made.

The run completed upload, extraction, source resolution, current research, evidence
building, and the start of diagnostic mapping. It then failed closed with
`diagnostic_coverage_unavailable`, caused by a second diagnostic-map
`ValidationError` after the one permitted sanitized correction. No result or DOCX was
produced.

Safe aggregate research events recorded zero accepted primary claims and zero curated
claims. The primary route reported the broad `provider_failure` category before any
usable candidate was recorded. That category does not identify whether the failure arose
from the initial search call, a tool result, a network/status condition, or another
pre-extraction provider error. No provider configuration or retry change is justified
from this evidence alone.

The diagnostic-map failure also does not expose the invalid field or value. Existing
behavior already retries once, preserves the second failure cause internally, removes
partial output, and returns the safe failure code. The strict schema was therefore not
weakened and no third call was added.

## Provider-free root cause and correction

The official International Crisis Group Guinea RSS feed was reachable and contained a
recent country-specific political-transition headline. The adapter rejected it because
it preferred the generic description whenever a description existed, then required the
chosen description itself to name Guinea and contain the FCV terms. The substantive
headline was never considered.

The narrow correction now:

- keeps a qualifying country-specific FCV summary when available;
- otherwise accepts the exact headline only when that headline independently matches the
  selected country, an FCV topic, and a substantive assertion;
- stores the same exact source field as both review text and supporting quote; and
- preserves existing official URL, publication-date window, and compound-country gates.

A provider-free live check of the official feed retained one Guinea claim from
International Crisis Group dated 2025-10-03. This supports the existing reduced-tier
rule: one recent trusted FCV-relevant source may be sufficient, while one URL and one
publisher are disclosed as such. It does not relabel generic indicators as current-FCV
evidence.

## Verification

- Focused research tests: **212 passed**.
- Complete provider-free suite: **1,441 passed**.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Independent specification and code-quality reviews: PASS.
- Complete external synthetic browser runner:
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`.
- Browser coverage included upload, both result views, two assistant turns, four restored
  messages after refresh, mobile layout, and DOCX download.
- Smoke DOCX: 39,465 bytes and a valid OOXML ZIP package.

The paid allowance for this release is exhausted. The follow-up correction has not been
deployed or tested with another paid assessment. No assessment identifier, uploaded
document, raw provider output, or assistant content is recorded in Git.
