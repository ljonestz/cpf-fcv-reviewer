# Project status

Updated 2026-08-30. The advisory CPF FCV Reviewer implementation is verified on `main`
through code commit `9816de4`; repository instructions include the API-cost protocol
in `CLAUDE.md`. Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Render reported
code commit `9816de4` live on 2026-08-30; `/health` returned `ok`, the public page
returned HTTP 200, and the assessment form was present. The service remains the free,
volatile public test site. Operational production still fails closed without SQLite
persistence; the public test site can run without a disk only through the explicit
`ALLOW_VOLATILE_PROTOTYPE=true` exception.

The note-first redesign organizes the detailed assessment around an overall read, explicit questions on RRA/current-dynamics alignment and FCV Strategy priorities, structured driver and strategy assessments, priority areas, and limitations. Narrative paragraphs are short and readable; traceability, evidence status, and coverage are collapsible in HTML. The DOCX follows the detailed HTML scope and omits internal reproducibility/referral clutter.

Latest verified suite on 2026-08-30: 1,063 passed in 14.93 seconds. The provider-free
smoke suite passed 34 tests, focused sanitizer/repair tests passed 61 tests, Python
compilation and `git diff --check` passed. Ruff remains unavailable or blocked by the
Windows environment. The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, dedicated Project Screener-aligned holding workspace, dedicated results view, question-led note sections, collapsible evidence/coverage disclosures, correction reruns, reset, and navigation-safe DOCX download.
- Three document buckets, country inference with confirmation fallback, explicit review stage and detail controls, safe source precedence, and detailed HTML/DOCX scope parity.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, safe failure codes,
  prohibited-language validation, thematic summary-title validation, and one bounded
  repair phase. A single internal follow-up model call is allowed only when every
  residual issue is an allowlisted mechanical guardrail violation; all other residual
  issues remain fail-closed.
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
- The latest paid Guinea run on `90f962b` reduced six initial validation issues to one
  residual raw evidence ID and then failed closed. Commit `9816de4` deterministically
  fixes that exact residual and is deployed, but no additional paid run was made after
  the fix. Therefore no successful post-fix Guinea result or DOCX is claimed.

## Validation cost protocol

Future sessions must follow the repository protocol in `CLAUDE.md`: targeted local
tests, provider-free smoke, deployed health/static checks, then at most one paid quality
run per deployed fix cycle. Do not rerun unchanged code. After a failure, use only safe
validation codes, add a regression test, and repeat the no-cost ladder before another
paid run is considered. Save full-page PNGs and a successful DOCX with unique filenames;
never substitute HTML for screenshots or relabel smoke output as country-quality output.

## Remaining considerations

1. With explicit approval for another paid run, perform one full Guinea quality assessment
   on deployed commit `9816de4`. Capture full-page summary/detailed PNGs and the DOCX,
   inspect the rendered output, and record safe validation outcomes before claiming
   Guinea acceptance.
2. Run Haiti and Benin provider acceptance only when needed for broader readiness:
   confirm Haiti's scattered jobs/IFC/MIGA treatment and Benin's multi-document coverage.
3. Keep the approved public registry current, versioned, checksummed, and
   non-confidential, and keep internal OPCS/ITS sources on a separately governed track.
4. ITS production use still requires separately approved identity, durable storage,
   authorization, audit/monitoring, authoritative source access, and
   information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Follow the API-cost validation ladder in `CLAUDE.md`; identify whether each run is
  provider-free smoke or a paid quality run.
- Run the smallest relevant tests and Ruff when available before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
