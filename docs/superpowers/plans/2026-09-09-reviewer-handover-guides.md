# Reviewer Handover Guides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two accurate, parallel, visually verified Word orientation and handover guides for the CPF FCV Reviewer and FCV Project Screener.

**Architecture:** Treat the two guides as one coordinated documentation package with a shared structure and separate tool-specific evidence. Reconcile each guide against its repository and dated validation records, use only version-relevant visuals, generate editable DOCX files, and render every page for visual QA. Do not change either application or run paid assessments.

**Tech Stack:** Markdown source records, Git, Python 3.13, `python-docx`, the bundled document-rendering runtime, Poppler/LibreOffice where supplied by that runtime, and existing PNG screenshots.

---

## File structure

**Create final deliverables:**

- `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260909_fcv-reviewer-handovers\20260909_CPF-reviewer-handover.docx`
- `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260909_fcv-reviewer-handovers\20260909_Project-screener-handover.docx`

**Create temporary QA artifacts outside Git:**

- one task-specific temporary working directory under the system temporary directory;
- rendered page PNGs and optional QA PDFs within that temporary directory; and
- a temporary generation script only if the document runtime requires one.

**Modify repository documentation only:**

- `docs/superpowers/plans/2026-09-09-reviewer-handover-guides.md`

No application source, test, deployment, earlier handover, or restricted source file will be modified.

### Task 1: Reconcile the CPF Reviewer source baseline

**Read:**

- `CLAUDE.md`
- `README.md`
- `docs/PROJECT_STATUS.md`
- `docs/PRODUCTION_READINESS.md`
- `docs/handover/20260908_ITS-handover.md`
- `docs/validation/2026-09-07-live-release-acceptance.md`
- `docs/validation/2026-09-08-word-export-presentation.md`
- `src/cpf_fcv_reviewer/`
- `prompts/`
- `registry_bundles/README.md`
- `tests/`

- [ ] **Step 1: Confirm repository state**

Run:

```powershell
git status --short --branch
git log -12 --date=short --pretty=format:'%h %ad %s'
```

Expected: the documentation feature branch is identified, existing user changes are preserved, and the most recent local CPF handover/status commits are visible.

- [ ] **Step 2: Build a dated factual source matrix in working notes**

Record the verified product purpose, inputs, pipeline stages, outputs, principal files, editing dependencies, latest documented release, completed tests, provider-backed evidence, and limitations. Label every status item as current, historical, experimental, or future/internal.

- [ ] **Step 3: Verify current external status without submitting an assessment**

Check the public repository/deployment health and visible static interface only if needed to resolve an unstable status claim. Do not upload documents, invoke model APIs, or represent a health response as analytical acceptance.

- [ ] **Step 4: Cross-check the source matrix**

Expected: release and test claims agree with the dated repository records; the public prototype, future ITS version, and stable Project Screener remain clearly separate.

### Task 2: Reconcile the Project Screener source baseline

**Read:**

- `C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\FCV-AGENT\CLAUDE.md`
- `C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\FCV-AGENT\README.md`
- `C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\FCV-AGENT\HANDOVER.md`
- relevant dated handovers and accepted-branch records under `FCV-AGENT\docs\`
- tracked files on the relevant accepted Render-development branch
- the 1 September Ricardy Project Screener guide and quick reference

- [ ] **Step 1: Confirm local and remote-reference state without modifying the repository**

Run:

```powershell
git -C 'C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\FCV-AGENT' status --short --branch
git -C 'C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\FCV-AGENT' branch -a --sort=-committerdate --format='%(committerdate:short) %(objectname:short) %(refname:short) %(subject)'
```

Expected: the dirty working tree is treated as user-owned, stable `main` is distinguished from later branches, and no checkout, fetch, reset, merge, or edit occurs in this repository.

- [ ] **Step 2: Identify the authoritative dated reference points**

Record stable-main, accepted Render-development, and ITS/QA status separately. Verify branch, commit, date, and evidence for each claim; do not describe preview features as stable production behavior.

- [ ] **Step 3: Build the Project Screener source matrix**

Record purpose, supported inputs and instruments, three-stage workflow, Express/step-by-step modes, outputs, codebase map, common edit paths, safeguards, major development eras, testing examples, and limitations.

- [ ] **Step 4: Enforce the source restriction**

Confirm that no raw OPCS policy corpus, policy index, triage document, or ESF manual identified as restricted in `FCV-AGENT\CLAUDE.md` has been opened or incorporated.

### Task 3: Select and verify the visuals

**Candidate sources:**

- `C:\Users\wb559324\OneDrive - WBG\Documents\Cowork\Tasks\welcome-ricardi-to-nairobi-workshop-team-2026-09-01\output\20260901_ricardy-nairobi-handover-v2\01_project-screener\visuals\`
- `C:\Users\wb559324\OneDrive - WBG\Documents\Cowork\Tasks\welcome-ricardi-to-nairobi-workshop-team-2026-09-01\output\20260901_ricardy-nairobi-handover-v2\02_cpf-reviewer\visuals\`
- newer verified PNGs associated with the documented September CPF release, if they show a materially more current interface;
- existing Project Screener knowledge-architecture visual, if it is accurate for the reference build.

- [ ] **Step 1: Inventory candidate images**

Record dimensions, file sizes, dates, and associated branch/build for each candidate. Reject duplicate, cropped, misleadingly named, or provenance-unclear images.

- [ ] **Step 2: Inspect every shortlisted image visually**

Use original-resolution inspection. Check readability, whether the image shows the intended feature, and whether any sensitive or raw assessment material is exposed.

- [ ] **Step 3: Select approximately three visuals per guide**

Prefer intake, workflow/architecture, and result presentation. Use fewer where an additional image would not add explanatory value.

- [ ] **Step 4: Write factual captions**

Each caption must include the application, date/build context, and the specific feature the reader should notice.

### Task 4: Draft the CPF FCV Reviewer guide

**Create:**

- `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260909_fcv-reviewer-handovers\20260909_CPF-reviewer-handover.docx`

- [ ] **Step 1: Draft the twelve approved sections**

Follow the design specification in order. Explain methodology before readiness conclusions. Keep the text audience-neutral, technically literate, and approximately 8-10 finished pages.

- [ ] **Step 2: Add the architecture and change-impact maps**

Cover the packaged `src/cpf_fcv_reviewer/` architecture, prompts, registry, contracts, validators, browser files, persistence, Word export, tests, and documentation. Show coordinated change dependencies, especially prompt/contract/validator/render/export/test changes.

- [ ] **Step 3: Add the editing workflow**

Include local setup, branch-first changes, targeted tests, full verification when appropriate, pull-request review, deployment verification, and the prohibition on committing secrets or assessment artifacts.

- [ ] **Step 4: Add the development and testing history**

Summarize major iterations by problem solved. Distinguish synthetic tests, provider-free browser QA, provider-backed Guinea validation, Word presentation checks, and remaining cross-country limitations.

- [ ] **Step 5: Insert only the selected CPF visuals**

Scale images to remain readable without exceeding page margins. Keep captions with images and avoid splitting explanatory callouts across pages.

### Task 5: Draft the FCV Project Screener guide

**Create:**

- `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260909_fcv-reviewer-handovers\20260909_Project-screener-handover.docx`

- [ ] **Step 1: Draft the same twelve sections**

Use the parallel structure while tailoring content to project/operation screening, instruments, review stages, FCV sensitivity and responsiveness, Do No Harm, and the three-stage workflow.

- [ ] **Step 2: Add the architecture and change-impact maps**

Explain the concentrated Flask/browser architecture, `app.py`, `index.html`, `background_docs.py`, document structure and routing helpers, browser storage, reports, tests, and reference documentation. Explain which related locations must change together.

- [ ] **Step 3: Add the editing workflow and version cautions**

Cover branches, tests, pull requests, Render/ITS differences, deployment branch verification, and restricted-source boundaries. State clearly that a local dirty or behind working tree is not an authoritative deployment reference.

- [ ] **Step 4: Add the development and testing history**

Group changes into analytical architecture, instrument/stage coverage, reliability, clearer outputs, specialist lenses, and institutional integration. Present the Somalia example as useful evidence with its documented caveat, not as a gold-standard analytical answer.

- [ ] **Step 5: Insert only the selected Project Screener visuals**

Label every stable, preview, or ITS/QA view accurately and avoid implying parity between versions.

### Task 6: Structural and factual QA

- [ ] **Step 1: Inspect both DOCX files programmatically**

Check that each file opens as a valid Word package, contains the twelve-section structure, includes captions and page numbering, has no recipient-specific Ricardy/Nairobi wording, and contains no placeholder text.

- [ ] **Step 2: Search for prohibited ambiguity**

Check for unsupported words such as `current`, `latest`, `production`, `accepted`, and `verified` without a nearby date or reference point. Correct any ambiguous status language.

- [ ] **Step 3: Cross-check parallel coverage**

Confirm that both guides cover all shared sections while preserving genuine tool differences. Remove unnecessary duplication within each document.

- [ ] **Step 4: Verify commands and links**

Check repository links, local setup commands, test commands, branch names, release identifiers, and referenced paths against source files.

### Task 7: Render and visually verify both guides

- [ ] **Step 1: Render each DOCX page by page**

Use the bundled document runtime's `render_docx.py` workflow to generate page PNGs and an optional PDF in the task-specific temporary QA directory.

Expected: every page renders successfully with no missing font or image errors.

- [ ] **Step 2: Inspect every rendered page**

Check margins, headings, tables, page breaks, captions, image legibility, headers/footers, page numbers, widows/orphans, blank space, clipping, and overflow.

- [ ] **Step 3: Revise and rerender**

Correct every material visual issue in a new generation pass. Do not overwrite an existing final deliverable until its path is confirmed to be the newly created task output.

- [ ] **Step 4: Run final package checks**

Confirm both files exist at the approved paths, open successfully, contain no tracked changes or comments, and have page counts within the intended standard range unless a small deviation materially improves readability.

### Task 8: Final verification and handoff

- [ ] **Step 1: Confirm repository scope**

Run:

```powershell
git status --short --branch
git diff --check
```

Expected: only approved documentation records are changed in `cpf-fcv-reviewer`; `FCV-AGENT` remains untouched.

- [ ] **Step 2: Record final evidence**

Report the two absolute output paths, page counts, structural checks, rendering results, visual-inspection result, and any material limitations.

- [ ] **Step 3: Commit documentation changes if any were added after this plan**

Use a narrow documentation commit and inspect the staged diff before committing. Do not commit the generated Word documents, screenshots, temporary scripts, or QA renders.

- [ ] **Step 4: Push the feature branch**

Push `codex/reviewer-handover-guides` after all repository documentation is clean and verified.
