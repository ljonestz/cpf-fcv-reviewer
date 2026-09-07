# All-country live-research finalization

## Purpose and acceptance standard

Improve source-backed, CPF-specific FCV analysis across countries. Guinea is a test
case, not a special retrieval route. The intended benchmark is a useful native-LLM
CPF review with live research, enhanced by traceable sources and structured output.
Human specialist review remains necessary; sparse research must not make the app fail.

## Findings and changes

- Discovery was restricted to a narrow crawler list that excluded major wires.
  Search now uses the existing bounded web-search call without a domain restriction;
  approved-publisher checks still apply to evidence. No additional calls are added.
- Publication-date fetching incorrectly reused crawler restrictions. It now checks
  approved publisher provenance while preserving bounded reads and URL protections.
- Every quote previously had to repeat the country name. An exact quote can now use
  an unambiguous country-specific article title for attribution. Regional titles,
  other-country passages, and invented quotes do not gain that contextual support.
- Approved source candidates are prioritized before the three-source normalization
  limit so broad discovery cannot crowd them out with unapproved hits.
- Search now receives up to 12,000 characters of primary CPF text and 4,000 characters
  of review focus in both RRA and holistic modes. Context is serialized separately
  from control fields. No additional extraction model or model call is introduced.
- Political events such as held elections and swearing-in now qualify. Mixed
  conflict/economic reporting is no longer rejected merely for mentioning GDP;
  pure indicator observations and FCV topic lists remain excluded.
- Fallback instructions distinguish historical knowledge and hypotheses from current
  reporting, and require qualification where a fallback-based assertion is used.
  This is prompt guidance, not a guarantee of factual accuracy or a new failure gate.

## Verification

Baseline: 201 source tests passed and four existing publication-metadata tests failed.
The metadata issue was reproduced before fixing. New contextual attribution tests
were exercised for Guinea, Kenya, Haiti, and Ukraine. Source-only regression tests
cover normalized claims and the full extraction/salvage path.

Final verification: **1,501 tests passed** (`python -m pytest tests -q`, with a
fresh temporary directory and valid certifi bundle outside the Windows sandbox).
The initial sandbox integration run encountered temporary-directory permissions and
an invalid inherited certificate bundle; the complete rerun passed without code
changes for those environmental errors. The focused export/route/smoke set passed
115 tests. Changed production Python and source-gateway tests pass Ruff, and
`git diff --check` passes. Older controller/runtime test files retain 11 pre-existing
lint findings (long lines and a duplicate literal key); these do not fail pytest.

Independent read-only review checked source selection/country attribution and the
CPF-context/controller changes. The source-crowding finding was fixed and covered
by a regression. No further concrete regression was identified.

## Live acceptance still required

Local fixtures establish pipeline behavior, not real-provider research quality.
Before calling this production-ready, run a bounded live research probe across
several countries and inspect actual accepted sources, publication dates, country
attribution, and relevance to CPF priorities. Then run one complete Guinea CPF/RRA
review and inspect both readouts and exports for specific, grounded recommendations.
Do not count an AI knowledge fallback as successful live-source acceptance.

Subsequent authorized live probes failed acceptance; see
`2026-09-07-paid-source-probes.md`. No full review or deployment followed.
