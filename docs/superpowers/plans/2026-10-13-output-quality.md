# Output quality implementation plan

**Goal:** Deliver a readable, stage-aware assessment whose four core questions carry the analysis, with a concise summary, usable comments and a simple query input.

**Architecture:** Reuse the existing review call and validated result. Add a short summary to each core finding; preserve historical results with an empty default. Render intentional paragraphs and safe inline emphasis consistently in browser and Word. No extra polishing call or new dependency.

**Approved design:** The user approved the full output critique and specified that conditional adaptation counts wherever it appears in the CPF, whether labelled If/Then or not. If materially missing, propose a few evidence-grounded conditions and corresponding adjustments, clearly distinguished from existing provisions. Keep sensitive details in appropriate internal destinations.

## Tasks and acceptance

- [x] Add regression checks for summary coverage, paragraph preservation, safe formatting, evidence references and query layout. Run them before implementation.
- [x] Update contracts.py, validators.py and review/repair prompts: developed four findings, separately grounded concise summaries; no mechanical word-count repair calls. Recommendations identify one main stage-feasible request. Preserve evidence/stage/policy checks on new prose.
- [x] Update app.js, styles.css and index.html: four-question summary, full-width recommendations, intentional paragraphs, plain editable comments with comfortable height; query input immediately after introduction, latest answer below, no duplicated revision/history or example links.
- [x] Update export_docx.py with matching reading order, safe emphasis, paragraph boundaries and priority source references. Update peer_email/follow_on prompts to retain qualifications and material issues during synthesis.
- [ ] Run focused tests, then suite and deterministic browser/export checks. Inspect screenshots at readable scale. Check source PDF annex availability without another model call.
- [ ] Record output-quality limitations, remove current rollout-ready claims, commit/push the candidate and update existing PR. Do not deploy or spend the remaining paid assessment during this implementation checkpoint.

Verification: Python pytest for contracts/validators/export/coordinator presentation and Node DOM tests; existing provider-free browser runner for input, results, query, refresh, mobile and downloads. Synthetic material demonstrates layout only, not generated analytical quality. A subsequent paid acceptance run remains a separate decision after inspecting the improved outputs.
