# Project status

Updated 2026-08-12. The advisory CPF FCV Reviewer MVP is on `feat/mvp-review-run`; latest functional commit: `728eec6`. Semantic application version is `0.1.0`.

The public prototype is <https://cpf-fcv-review-prototype.onrender.com/>. Its health endpoint reported `ok` with `volatile` storage. The Render health release label `4acca30` is stale: it is neither the Git commit nor the application version.

The latest public Benin run on `728eec6` completed in `limited_framing` mode with 7 findings, 3 recommendations, 5 limitations, and 22 evidence items. JSON/DOCX parity and evidence traceability passed. Safe external artifacts are under `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\test_cpf` and are not repository records.

Latest suite: 310 passed; Ruff clean. The service remains an MVP: volatile one-process state, no operational SharePoint or ITS access, no durable retention or identity controls, public-web-only current context, and no production-use approval. The stable FCV Project Screener is untouched and prohibited.

## Completed to date

- Guided landing, progress workspace, dedicated results view, evidence disclosures, correction reruns, reset, and DOCX export.
- Evidence-linked diagnostic findings, grouped priority questions, limited framing when a suitable current RRA is unavailable, and safe source precedence.
- Approved public guardrail registry with checksum validation and fail-closed loading.
- Structured model output, application-owned metadata, one bounded repair attempt, safe failure codes, and prohibited-language validation.
- Supporting-PDF extraction is bounded while the primary CPF remains fully extracted.
- Live public Benin smoke test and local automated validation completed on `728eec6`.

## Remaining considerations

1. Update Render's stale `APP_RELEASE` deployment label so `/health` identifies the deployed Git commit accurately.
2. Keep the approved public registry current, versioned, checksummed, and non-confidential.
3. Keep any internal OPCS/ITS implementation in a separate governed track; do not expand the public bundle with internal policy detail.
4. Rerun and record validation after material model, prompt, registry, extraction, deployment, or UI changes.
5. Production use would require separately approved identity, retention, audit, monitoring, authoritative source access, and information-security controls.

## Future-session checklist

- Read `README.md`, `CLAUDE.md`, and this file.
- Verify the branch, commit, and worktree status rather than trusting this summary blindly.
- Run tests and Ruff before claiming completion.
- Update this file after material work, keeping dated validation records unchanged.
