# Project status

Updated 2026-08-15. The advisory CPF FCV Reviewer MVP is on `fix/research-resilience-guided-journey`; latest verified local commit: `9736ed6`. Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Its health endpoint reports `ok` with `volatile` storage. The Render service is live on the guided-journey validation commit `9736ed6`, and `/health` reports the matching release label.

The note-first redesign organizes reviews around Overall read, What to revise, Priority areas for strengthening, and Limitations and document coverage. It supports three document buckets, country-inference confirmation fallback, explicit review stages and Brief/Standard/In-depth detail, collapsed evidence, DOCX parity, and correction reruns that refer to the review rather than findings. There is no questions-for-confirmation section.

Latest verified suite on 2026-08-13: 458 passed in 5.83s; Ruff clean; `git diff --check` passed with only line-ending warnings and no errors. The focused frontend suite passed 19 tests in 3.36s. The service remains an MVP: volatile one-process state, no operational SharePoint or ITS access, no durable retention or identity controls, public-web-only current context, and no production-use approval. The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, progress workspace, dedicated results view, note-first sections, collapsed evidence disclosures, correction reruns, reset, and DOCX export.
- Three document buckets, country inference with confirmation fallback, explicit review stage and detail controls, safe source precedence, and JSON/DOCX note parity.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, one bounded repair attempt, safe failure codes, and prohibited-language validation.
- Supporting-PDF extraction is bounded while the primary CPF remains fully extracted.
- Deterministic synthetic early-drafting, decision-review, and finalization quality cases passed as part of the automated suite. These are not a substitute for approved-material reference evaluation.
- Guided review journey browser QA passed at 1280px and 390px using the deterministic local smoke server and the Benin test base. The final result view hides the progress panel, preserves the evidence-status label, and triggers the DOCX download without horizontal overflow.

## Remaining considerations

1. Keep future Render releases intentional: the service was deployed to the exact validated commit and its `APP_RELEASE` label was updated to `9736ed6` during this session.
2. Keep the approved public registry current, versioned, checksummed, and non-confidential.
3. Keep any internal OPCS/ITS implementation in a separate governed track; do not expand the public bundle with internal policy detail.
4. Rerun and record validation after material model, prompt, registry, extraction, deployment, or UI changes. The 2026-08-15 browser validation is recorded in `docs/validation/2026-08-15-guided-journey-benin-browser-qa.md`. Approved-material reference evaluation remains unavailable because the local smoke server uses deterministic synthetic output and the required provider environment variables are absent.
5. Production use would require separately approved identity, retention, audit, monitoring, authoritative source access, and information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Run tests and Ruff before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
