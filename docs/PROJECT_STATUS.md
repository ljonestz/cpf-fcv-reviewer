# Project status

Updated 2026-08-30. The advisory CPF FCV Reviewer is on `fix/research-resilience-guided-journey`; the reliability/UX implementation is verified through code commit `d9b991f`. Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Its last verified state, on 2026-08-23, was release `ef7b9ea`, health `ok`, and `volatile` storage. Live health could not be reverified on 2026-08-30, and the current branch has not been deployed. Operational production still fails closed without SQLite persistence; the public test site can run without a disk only through the explicit `ALLOW_VOLATILE_PROTOTYPE=true` exception.

The note-first redesign organizes the detailed assessment around an overall read, explicit questions on RRA/current-dynamics alignment and FCV Strategy priorities, structured driver and strategy assessments, priority areas, and limitations. Narrative paragraphs are short and readable; traceability, evidence status, and coverage are collapsible in HTML. The DOCX follows the detailed HTML scope and omits internal reproducibility/referral clutter.

Latest verified suite on 2026-08-30: 1,046 passed in 50.37 seconds. The focused extraction/runtime suite passed 99 tests. JavaScript syntax and `git diff --check` passed; Ruff remains blocked by Windows Application Control (`WinError 4551`). The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, dedicated Project Screener-aligned holding workspace, dedicated results view, question-led note sections, collapsible evidence/coverage disclosures, correction reruns, reset, and navigation-safe DOCX download.
- Three document buckets, country inference with confirmation fallback, explicit review stage and detail controls, safe source precedence, and detailed HTML/DOCX scope parity.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, bounded repair, safe failure codes, prohibited-language validation, and thematic summary-title validation.
- PDF extraction is text-first and bounded. Optional PDFs use deterministic full-range sampling with true page locators and explicit incomplete-coverage warnings. Long TXT/Markdown inputs are chunked across the full document.
- Package evidence is balanced across uploaded files. Incompletely sampled RRA/Strategy evidence cannot support an unqualified `not evidenced` absence claim.
- SQLite-backed jobs, replayable events, restart recovery, 24-hour production retention, and persistence-before-completion event ordering are implemented.
- Deterministic synthetic early-drafting, decision-review, and finalization quality cases passed as part of the automated suite. These are not a substitute for approved-material reference evaluation.
- The dedicated holding view passed browser QA at 1280px and 390px. It preserves the existing stage/timer/guidance lifecycle, has no horizontal overflow, and moves focus correctly into holding and results views.
- The public Guinea RRA structural check confirmed that the bounded review evidence includes deep pages supporting natural-resource, legitimacy, inclusion, jobs, and conflict analysis. This is not a provider-quality result.

## Remaining considerations

1. Run current-prompt real-provider acceptance for Guinea, Haiti, and Benin when credentials are available. Confirm Guinea driver-response quality, Haiti's scattered jobs/IFC/MIGA treatment, and Benin's multi-document coverage before claiming broader readiness.
2. Save new JSON, HTML, DOCX, and 1280px/390px screenshots for those provider runs without overwriting prior evidence; inspect every DOCX page.
3. Deploy the verified branch to the free Render test service with `ALLOW_VOLATILE_PROTOTYPE=true`, then verify `/health` and update the recorded release.
4. Keep the approved public registry current, versioned, checksummed, and non-confidential, and keep internal OPCS/ITS sources on a separately governed track.
5. ITS production use still requires separately approved identity, durable storage, authorization, audit/monitoring, authoritative source access, and information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Run tests and Ruff before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
