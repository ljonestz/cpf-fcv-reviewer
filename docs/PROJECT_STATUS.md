# Project status

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
