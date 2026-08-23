# Project status

Updated 2026-08-23. The advisory CPF FCV Reviewer is on `fix/research-resilience-guided-journey`; latest verified implementation commits: `4b8c09b` and `abaa615`. Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. It currently reports release `ef7b9ea`, health `ok`, and `volatile` storage. The branch now fails closed in production without SQLite persistence, so the next deployment requires the configured paid Render disk.

The note-first redesign organizes the detailed assessment around an overall read, explicit questions on RRA/current-dynamics alignment and FCV Strategy priorities, structured driver and strategy assessments, priority areas, and limitations. Narrative paragraphs are short and readable; traceability, evidence status, and coverage are collapsible in HTML. The DOCX follows the detailed HTML scope and omits internal reproducibility/referral clutter.

Latest verified suite on 2026-08-23: 1,001 passed in 24.56s. JavaScript syntax and `git diff --check` passed; Ruff remains blocked by Windows Application Control (`WinError 4551`). The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, progress workspace, dedicated results view, question-led note sections, collapsible evidence/coverage disclosures, correction reruns, reset, and navigation-safe DOCX download.
- Three document buckets, country inference with confirmation fallback, explicit review stage and detail controls, safe source precedence, and detailed HTML/DOCX scope parity.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, bounded repair, safe failure codes, prohibited-language validation, and thematic summary-title validation.
- PDF extraction is text-first and bounded. Long TXT/Markdown inputs are chunked across the full document so evidence sampling cannot stop at the cover page.
- SQLite-backed jobs, replayable events, restart recovery, 24-hour production retention, and persistence-before-completion event ordering are implemented.
- Deterministic synthetic early-drafting, decision-review, and finalization quality cases passed as part of the automated suite. These are not a substitute for approved-material reference evaluation.
- Guided review journey browser QA passed at 1280px and 390px using the deterministic local smoke server and the Benin test base. The final result view hides the progress panel, preserves the evidence-status label, and triggers the DOCX download without horizontal overflow.

## Remaining considerations

1. Upgrade the existing Render service to a paid single-instance plan, attach the configured persistent disk, and deploy only after `PERSISTENCE_PATH=/var/data/reviews.sqlite3` is available.
2. Verify `/health` reports the exact deployed commit, `storage: persistent`, and `queue: persistent_worker`; then verify restart recovery.
3. Repeat the real Haiti quality run after deployment and confirm that findings draw from the full CPF, not only its opening pages. Save the detailed HTML, DOCX, and 1280px/390px summary screenshots.
4. Complete visual inspection of every DOCX page when Word desktop access is available.
5. Keep the approved public registry current, versioned, checksummed, and non-confidential, and keep internal OPCS/ITS sources on a separately governed track.
6. Production use still requires separately approved identity, authorization, audit/monitoring, authoritative source access, and information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Run tests and Ruff before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
