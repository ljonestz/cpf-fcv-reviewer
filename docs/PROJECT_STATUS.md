# Project status

Updated 2026-09-02. The results, persistent assistant, and full-RRA coverage redesign is
provider-free verified on `fix/guinea-production-fixes` through code commit `0aa6d3d`.
Two authorized deployed Guinea cycles failed closed during diagnostic mapping; deployed
provider acceptance for the redesign is not established. Semantic application version is
`0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Render reported
code commit `894ebe5` live on 2026-09-02; `/health` returned `ok` with that exact release,
the public page returned HTTP 200, and the review and assistant shells were present. The
service remains the free, volatile public test site. Operational production still fails closed without SQLite
persistence; the public test site can run without a disk only through the explicit
`ALLOW_VOLATILE_PROTOTYPE=true` exception.

The Five-minute readout now leads with a concise overall assessment, separate RRA/current-
dynamics and FCV Strategy readouts, and up to three linked priority measures. Detailed
analysis retains the structured driver, strategy, recommendation, target, and limitations
content while removing technical evidence disclosures from reader-facing HTML and DOCX.
Structured evidence remains available internally for validation and the follow-on assistant.

Latest verified suite on 2026-09-02: 1,151 passed in 46.54 seconds. The provider-free
smoke suite passed 36 tests, the diagnostic coverage-retry focused set passed 143 tests,
Python compilation, JavaScript syntax, and `git diff --check` passed. Ruff is not installed
in the Windows environment.
The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, dedicated Project Screener-aligned holding workspace, dedicated results view, question-led note sections, collapsible evidence/coverage disclosures, correction reruns, reset, and navigation-safe DOCX download.
- Concise Five-minute readout with separate RRA and FCV Strategy synthesis, linked
  priority cards, consolidated detailed analysis, and one basis/limitations disclosure.
- Genuine streamed follow-on assistant grounded in the completed review and referenced
  evidence. It keeps at most 20 messages in the existing session store, restores after
  refresh, rejects concurrent requests, and clears history for correction children.
- Recognized uploaded RRAs/equivalent diagnostics are fully extracted within explicit
  bounds and every extractable page is assigned exactly once through the existing
  diagnostic-map concept. Unsafe or incomplete mapping fails closed without sampling.
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
- PDF extraction is text-first and bounded. Optional PDFs use deterministic full-range sampling with true page locators and explicit incomplete-coverage warnings. Long TXT/Markdown inputs are chunked across the full document.
- Package evidence is balanced across uploaded files. Incompletely sampled RRA/Strategy evidence cannot support an unqualified `not evidenced` absence claim.
- SQLite-backed jobs, replayable events, restart recovery, 24-hour production retention, and persistence-before-completion event ordering are implemented.
- Deterministic synthetic early-drafting, decision-review, and finalization quality cases passed as part of the automated suite. These are not a substitute for approved-material reference evaluation.
- The dedicated holding view passed browser QA at 1280px and 390px. It preserves the existing stage/timer/guidance lifecycle, has no horizontal overflow, and moves focus correctly into holding and results views.
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
  and code/security review. It has not been deployed or provider-tested.

## Validation cost protocol

Future sessions must follow the repository protocol in `CLAUDE.md`: targeted local
tests, provider-free smoke, deployed health/static checks, then at most one paid quality
run per deployed fix cycle. Do not rerun unchanged code. After a failure, use only safe
validation codes, add a regression test, and repeat the no-cost ladder before another
paid run is considered. Save full-page PNGs and a successful DOCX with unique filenames;
never substitute HTML for screenshots or relabel smoke output as country-quality output.

## Remaining considerations

1. If another paid fix cycle is explicitly authorized, deploy exact commit `0aa6d3d`,
   complete no-cost health/static checks, then run no more than one Guinea assessment.
   Confirm all 102 RRA pages are attempted/accounted for, inspect deep-page evidence,
   exercise two assistant requests plus refresh restoration, and inspect the saved DOCX.
2. Guinea provider acceptance is established for the previous public advisory prototype on
   deployed commit `1ba44bf`, subject to its disclosed `reduced` current-evidence tier.
3. Run Haiti and Benin provider acceptance only if broader cross-country readiness is needed:
   confirm Haiti's scattered jobs/IFC/MIGA treatment and Benin's multi-document coverage.
4. Keep the approved public registry current, versioned, checksummed, and
   non-confidential, and keep internal OPCS/ITS sources on a separately governed track.
5. ITS production use still requires separately approved identity, durable storage,
   authorization, audit/monitoring, authoritative source access, and
   information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Follow the API-cost validation ladder in `CLAUDE.md`; identify whether each run is
  provider-free smoke or a paid quality run.
- Run the smallest relevant tests and Ruff when available before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
