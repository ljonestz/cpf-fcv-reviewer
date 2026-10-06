# mAI country research and three-run acceptance

For the next session, start with the [6 October handover](../handover/20261006_cpf-mai-production-readiness-handover.md).
It records the final branch/CI state, evidence locations and ordered provider-free
repairs. Historical test results below are preserved; this record does not
authorize another model call.

## Authorization and scope

The owner chose to avoid the separate Anthropic API and authorized up to three
new full local assessments, with repairs between attempts. This supersedes the
earlier one-run limit for this testing cycle only. Existing quota counters,
evidence validators and historical records remain intact. No merge, deployment,
hosted Desktop credentials or change to the stable FCV Project Screener is authorized.

## Research design

The authenticated [mAI Google Search guide](https://ai.worldbankgroup.org/maifactory/google-search/)
documents Desktop access through the mAI Gemini gateway. Gemini 3.8 Flash uses
Google Search to discover public sources; Sonnet 4.6 through mAI selects substantive
passages from independently fetched original pages. The application copies those
passages and verifies source ownership, country, date and source suitability.
Google's generated synthesis is never treated as a literal source quotation.

The search request contains only a canonical country, review date and fixed public
FCV topics. Uploaded documents and review notes remain outside search requests.
Original-page retrieval uses a separate unauthenticated client, HTTPS, checked
redirects, bounded reads and the existing public-publisher catalogue. Catalogue
coverage limits retrieval; it is not a claim that other publishers are unreliable.
Provider search suggestions are displayed in an isolated, scriptless frame.

Local setup: reuse the existing mAI environment and Desktop sign-in. Set
`MAI_TEAM_NAME` to the approved team and `RESEARCH_PROVIDER=mai_google`, then run
`scripts/20261004_run_mai_desktop.py`. No separate Anthropic key is required.
`APP_RELEASE` can identify the exact checked-out commit for acceptance. Preserve
the workstation's verified certificate configuration; never disable TLS checks.
Costs accrue through mAI model/search usage. This is not a free or offline route.
Desktop remains local DEV only; hosted use still needs Application/ACN approval.

## Failures reproduced before repairs

- First discovery probe exhausted its output budget; incomplete responses are rejected.
- A subsequent research check found 17 leads but only one parsed original among
  the first eight. Four of six model-transcribed quotations failed exact matching.
- Passage-ID selection now copies original text instead of asking the model to
  transcribe quotations. Invented IDs and model-authored quotations are rejected.
- Public fetches inspect up to 16 leads with four concurrent readers and a shared
  deadline. Every redirect retains the same URL and credential boundary.
- Conflicting World Bank article-path and metadata dates remain undated.
- Country-incompatible passages are excluded before selection using the same
  country check that validates the final observation; the validator is unchanged.

## Acceptance method fixed before full runs

Use the frozen Guinea strategic overview, results framework and June 2023 RRA
from the [earlier acceptance specification](2026-10-01-provider-free-release-gates.md),
Decision Review, with no focus instruction steering around known defects.
Run the exact browser runner against synthetic inputs first, then identify the
live local service by its exact commit. Reserve each of the three attempts in a
separate non-overwriting ledger file. Failed attempts count; no quota resets.

Inspect all accepted priority references, target excerpts and RRA response quotes;
all five RRA drivers and four Strategy shifts; date/projection fidelity; feasibility
and numerical recommendations; current research coverage; summary/detail agreement;
assistant grounding; persistence and both Word exports. On failure retrieve only
allowlisted safe diagnostics, reproduce synthetically, and repair before another run.

Compare with the saved direct-Anthropic Guinea candidate using the same frozen
three-document corpus and the historical deployed Render assessment. These differ
in release, model and date; the comparison is a factual/coverage benchmark, not a
controlled claim of provider equivalence. Neither baseline is error-free. Specifically
check the eight issues recorded in the
[3 October accepted-output review](2026-10-03-quote-selection-paid-acceptance.md).

## Evidence and status

Ignored preparation records: `output/20261004_mai_grounding/`. Browser/assessment
artifacts and the new three-run reservation ledger:
`output/playwright/20261004_mai_grounded_acceptance/`. Live identifiers remain in
the existing OS-temporary handoff directory, outside the repository.

Preparation has established mAI-native search connectivity and exact passage
copying, but research breadth and end-to-end acceptance remain under test.
Production readiness is not established by these preparation probes. Final test
counts, full-run outcomes and comparison findings will be recorded after inspection.

## First full attempt and focused follow-up

Candidate `d5027efa66214cec6969722d45ed1e63f75e741d` passed 1,859 Linux tests
and Python name/import lint. The exact browser runner passed 12 synthetic checks,
assistant restoration and both exports (`synthetic-05`). Earlier screenshot-driven
runner attempts exposed an iframe-navigation/scroll interaction; search links now
open a separate tab and the runner verifies keyboard navigation. No paid assessment
was spent diagnosing that runner. The original database was backed up with SQLite's
backup API and an integrity check; its quota counters were preserved.

New full attempt 1 (`mai-grounded-01-guinea`) was submitted at 22:03 UTC on 4 October
and failed safely after 362.53 seconds overall. It reached research, full RRA mapping,
review and repair. Six initial and six residual issues remained: three
`unsupported_cpf_response` / `quote_not_in_cited_text`, and three
`target_locator_mismatch` / `excerpt_mismatch`. Only safe codes and counts were read;
no rejected draft was retrieved. No accepted report, export or assistant response
was released. Research was reduced for claims, publishers and current developments.
One of the new three full attempts is consumed; two remain.

The follow-up reproduces that exact six-issue pattern synthetically. mAI review and
repair schemas now constrain CPF response quotations and priority target excerpts
to supplied passage IDs; the application supplies original text and coordinates.
The existing quotation, own-citation, policy and date validators remain active.
Literal quotation support remains for other transports or when no index is available.
The installed SDK's schema transformer removed enum restrictions, so the supported
Bedrock enum/const constraints are added after transformation. A tiny synthetic mAI
probe verified these constraints without running an assessment. The new target
selection and repair controls passed in a 407-test focused batch including smoke tests.

Research follow-up found that ISS original pages expose explicit `Published on`
dates without standard metadata. These dates are now parsed, with conflicting dates
still withheld. Up to six fetched originals can be compared before the unchanged
three-source, six-observation and 6,000-character final evidence limits apply. No
publisher catalogue expansion or validation relaxation was needed.

Replaying saved discovery with original-page fetches and one mAI normalization
produced four accepted observations from Amnesty, ISS Africa and World Bank, meeting
the controller's full-tier threshold. Inspection still found narrow topical coverage
and relevance explanations adding facts absent from their selected passage. The
selection instructions now prioritize uncovered topics and require relevance to
preserve the passage's facts, uncertainty and time frame. A prompt regression failed
before that change; live breadth and semantic fidelity still require assessment review.

## Second full attempt and transport follow-up

Candidate `671af409356f97aad9d41d6d4b8513eb1009fac6` passed 1,870 Linux tests
and Python name/import lint ([CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37240343995)).
Three stale prompt-version assertions found in the preceding CI were corrected;
application behavior was unchanged by that test-only commit.

Attempt 2 (`mai-grounded-02-guinea`) was submitted at 22:33 UTC on 4 October,
completed research and RRA mapping, then stopped during review generation after
137.61 seconds overall. Safe logs identify `MaiUnavailable`; no draft or provider
response from that assessment was retrieved. No findings, exports or assistant call
were released. Two full attempts are consumed; one remains. The existing two-per-hour
limit is reached until the next UTC hour; it must not be bypassed.

A bounded synthetic full-schema probe reproduced HTTP 400: compiled grammar too
large. The earlier small enum/const probe did not expose this full-schema limit.
Numeric selections, explicit required fields and locator-definition reuse did not
resolve it. Selecting the target passage ID directly, without generating its redundant
coordinate object, was accepted with HTTP 200. The application reconstructs the
locator from supplied primary/package evidence, then applies the same own-citation
and exact-passage validation. Unknown selections remain blocked. No numeric-choice
fallback, relaxed validator or automatic model retry was introduced. HTTP failures
now retain only their safe status code for the existing sanitized runtime logger.

The compact-target conversion and schema regression failed before implementation;
183 focused provider-free checks, including smoke and prompt guardrails, pass after it.
The same complete schema also passed a 32-token synthetic transport probe with all
260 source choices from the frozen corpus. Its deliberate token-limit stop is not
an accepted assessment; it establishes schema compatibility only.
Full CI passed for `e97398e`. A final narrow follow-up maps mAI transport failures
to the existing `model_output_unavailable` message rather than inaccurately blaming
evidence grounding. Its regression failed before the change; 81 focused checks,
including smoke, passed afterward. No new browser text or workflow was introduced.

## Final authorized attempt: execution passes, analytical acceptance held

Candidate `14f32d9cb8f9dbe68eb88c5ac5f5c39fcb637780` passed 1,875 Linux tests
and name/import lint ([CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37241723863)).
Attempt 3 (`mai-grounded-03-guinea`) was submitted at 23:01 UTC on 4 October, after
the normal hourly admission window opened. It completed without repair: 225.3 seconds
waiting for assessment, 295.11 seconds for the full browser flow. **All three newly
authorized full runs are consumed. No fourth assessment is authorized.** One real
assistant response was generated within the final acceptance flow. Preparatory research
and small schema-compatibility calls were separate from these full assessments; exact
provider cost was not measured.

The frozen input hashes match. Seven primary pages, five package pages and 101 readable
RRA pages out of 102 attempted were retained, with complete thematic mapping. All five
RRA drivers and four Strategy shifts appear. Four delivered CPF quotations matched
their own cited primary/package evidence and physical PDF pages; the fifth row used
the explicit absence sentinel with `not_evidenced`. Four target excerpts also matched
the cited PDF pages. These checks normalize punctuation/whitespace and do not establish
the truth of surrounding analysis or the suitability of an edit target.

The browser runner recorded 11/12 checks passing, zero console/page/resource errors,
working research attribution, assistant restoration and both Word downloads. The one
failure was its literal whitespace comparison of the material research caveat. A
GET-only independent browser check confirmed the complete caveat is visible after
whitespace normalization; the original failed-check report was preserved. Native Word
rendering preserved both DOCX hashes. All nine pages were inspected: two summary and
seven detailed, readable without clipping or blank pages. Some detailed sections
continue across pages. Desktop summary and native-size mobile crops were inspected.

### Comparison with saved benchmarks

| Dimension | Historical deployed Render (10 September) | New local mAI (attempt 3) |
| --- | --- | --- |
| Detail length | 3,546 words; summary 1,461 | 2,717 words; summary 770 |
| Structured coverage | Five drivers, four Strategy shifts, three priorities | Five drivers, four Strategy shifts, four priorities |
| Existing CPF provisions | Understates institutional roles and operational commitments | Better acknowledgement of One WBG roles, Poverty Targeting Index and elite-capture screening |
| Current research | Reduced, two publishers; older transition reporting | Reduced: three dated observations from two publishers, plus one undated World Bank observation |
| Recommendations | Includes unsupported illustrative numerical commitments | Avoids those invented commitments, but creates a material false gap from a misread table |
| Accuracy conclusion | Known defects; not a gold standard | Not demonstrated equivalent or production-ready |

The later saved direct-Anthropic candidate used the same three frozen PDFs and was
also checked. Improvements include preserving the Simandou earnings projection's
conditional status and recognizing existing elite-capture screening. Unlike that
candidate's verified US$1 billion source reading, this mAI output wrongly treats the
private-capital target as missing. Different dates, models, releases and input coverage
in the historical Render run prevent a controlled provider-equivalence conclusion.
Word count alone is not a measure of analytical depth.

### Material findings still blocking acceptance

1. **Table interpretation:** framework physical page 5 specifies private-capital
   baseline 0 (2025) and target US$1 billion (2033). The report and assistant call both
   TBC and recommend adding the existing target. Only the adjacent jobs row is TBC.
   That row already states women as a disaggregation and footnote 2 identifies IDA
   ISR and IFC/MIGA client reporting; the report overlooks these provisions too.
2. **Units:** the alignment readout converts the 2,260,022 electricity-beneficiary
   target (people) into connections. Exact quote validation does not catch this.
3. **Current context:** retained dated material is concentrated on civic space
   (Amnesty July 2026 and HRW December 2024), with an undated World Bank safety-net
   observation. This is not thorough contemporary country coverage. The report still
   extrapolates transition risk from the June 2023 RRA. One priority collapses the
   HRW passage's 53 dissolved and 54 suspended parties into over 100 dissolved parties.
4. **Attribution/targets:** the report describes contents of an unprovided risk annex,
   inconsistently treats RRA-described GRM infrastructure as a current CPF provision,
   and anchors a results-framework edit to a narrative passage. Another target excerpt
   is merely `Baseline: TBC.`; exact presence is insufficient semantic targeting.
5. **Assistant boundary:** safe category `unsupported_policy_determination` was observed
   in the cached response. No further model call was made. It also amplifies the table
   error and exceeds the requested management-summary length.
6. **Date consistency:** research used the host's local date (5 October) while metadata,
   exports and model instructions used UTC (4 October). The saved output is unchanged.

### Provider-free follow-up and remaining gate

The research date default now uses UTC like run metadata. mAI assistant responses are
checked with the existing policy-determination validator before their first chunk is
released; the observed approval-language class was added to that validator. Synthetic
regressions failed before both changes. The follow-up batch passed 367 tests; two
registry tests initially hit Windows temporary-folder permissions and both passed
when rerun alone in a fresh repository-local temporary directory. Full CI for the
follow-up commit `529807080e01c75d486a0928d2bd33f891c26456` passed **1,881 tests**
and Python name/import lint ([CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37243473492)).
These fixes have **not** had another live
assessment or assistant acceptance, and do not repair the saved narrative.

Do not mask these analytical failures with country-specific substitutions, relax
evidence checks, or treat more prose as accuracy. The next work should use synthetic
adjacent table rows and source-preserving extraction to test indicator/value/unit
association; improve research topic and event-date coverage with original sources;
and prevent the assistant from amplifying unsupported accepted analysis. Another
bounded real-model acceptance requires fresh authorization after those free checks.
Cross-country reliability, hosted Application/ACN approval, Python/Posit compatibility,
durable hosted storage/recovery and operational acceptance remain open.

Evidence remains ignored under `output/playwright/20261004_mai_grounded_acceptance/`
and `output/20261005_mai_accepted_word/run03/`. Safe events, original results, Word
files, screenshots, read-only checks and hashes are preserved. The database records
four daily assessments (one earlier historical mAI attempt plus the three in this
cycle), and one assistant call. No quota reset, merge, deployment, separate Anthropic
key configuration or stable FCV Project Screener modification occurred. The two
verified temporary local service processes were stopped after testing; SQLite,
quotas and all original outputs were preserved.
