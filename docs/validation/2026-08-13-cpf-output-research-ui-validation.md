# CPF Output, Research, and UI Redesign Validation

Validation date: 2026-08-13; branch: `feat/mvp-review-run`

## Automated verification

- Focused integration group: 300 passed in 4.40 seconds.
- Final full suite after the evidence-boundary and privacy fixes: 622 passed in 10.70 seconds.
- Ruff: all checks passed.
- JavaScript syntax: `node --check src/cpf_fcv_reviewer/static/app.js` passed.
- `git diff --check`: passed; Git reported line-ending warnings only.
- Pytest used an external `--basetemp` outside the sandbox because inaccessible pre-existing `.pytest_*` directories in the OneDrive worktree and sandboxed temporary directories cause Windows `WinError 5` during collection or cleanup. Those artifacts were not changed.

## Deterministic local browser QA

The local acceptance run used deterministic, synthetic, non-sensitive research and model services with the synthetic Benin CPF fixture. It therefore validates application integration and presentation, not real-provider behavior or substantive approved-material quality.

At 1280px and 390px, the run verified:

- the three upload cards, country detection, review-stage selection, and removal of the detail selector;
- safe progress labels and the successful transition to a dedicated results experience;
- **Five-minute readout** selected by default and a separate **Detailed analysis** view;
- complete priority prose, initially collapsed evidence disclosures, and keyboard tab behavior;
- correction rerun, volatile-state reset, and full-note download;
- stacked mobile intake/actions without horizontal overflow; and
- no browser console warnings or errors.

The four failure-specific research-retry codes, retained-upload retry route, no-body retry request, stale-operation guards, and absence of partial output are covered by focused route, frontend, and accessibility tests. The deterministic successful browser fixture did not fabricate a provider failure merely to exercise that state visually.

## DOCX inspection

Automated DOCX structure, accessibility, style, traceability, and web/DOCX parity tests passed. The canonical `render_docx.py` path could not run because LibreOffice/`soffice` is unavailable.

As a documented fallback, the downloaded two-page DOCX was opened in Microsoft Word and both pages were visually inspected. The title hierarchy, advisory notice, priority sections, evidence and coverage lines, reproducibility metadata, page break, and footer were visible without clipping or overlap. The inspection exposed a character-limited excerpt ending mid-word; the runtime now truncates ordinary evidence at word boundaries, with a regression test and a safe hard-limit fallback for a single overlong token. This Word inspection is not a substitute for a successful canonical renderer run.

## Output-quality inspection

The synthetic five-minute readout and detailed note were internally consistent: the overall judgment, alignment synthesis, and priority action were the same canonical content in the summary, detailed view, and DOCX. The detailed result was priority-led, linked its rationale to a practical action and target, and clearly disclosed limited diagnostic framing and document coverage.

Because the source and model responses were synthetic, this inspection cannot establish country specificity, current-context evidence quality, dated RRA handling, or the approved 0-2 substantive rubric threshold. No approved-material score is recorded.

## Task 13 prerequisite status

Presence-only checks found `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_ID`, `REGISTRY_BUNDLE_PATH`, and `REGISTRY_BUNDLE_SHA256` absent from this session. An approved Benin CPF/package and approved public registry bundle were not confirmed for a real-provider run. Consequently, the approved-material local assessment, substantive rubric score, deployed approved-Benin run, and post-deployment Render-log audit remain pending and must not be inferred from the synthetic validation.

## Safety and remaining constraints

- No secret value, uploaded text, source claim, prompt, or generated sensitive prose is recorded here.
- The stable FCV Project Screener was not modified or used for deployment.
- The public prototype remains public-web-only. A future ITS deployment would use the existing source-adapter boundary with separately governed, permission-aware SharePoint access; no such access exists here.
- Current-country public research is mandatory for each review. A public RRA upload is optional context and changes the research window; it does not suppress current-country research.
- Review state is volatile and one-process only. There is no durable retention, production identity, operational SharePoint integration, or production-use approval.
