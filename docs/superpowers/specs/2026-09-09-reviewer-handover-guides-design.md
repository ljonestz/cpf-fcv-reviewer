# Design: CPF and Project Reviewer Orientation and Handover Guides

**Date:** 2026-09-09  
**Owner:** Lindsey Paul Jones  
**Outputs:** Two standalone Word documents for colleagues who have some familiarity with programming but are new to the applications.

## 1. Purpose

Create separate, parallel handover guides for:

1. the CPF FCV Reviewer; and
2. the FCV Project Screener.

Each guide will explain the product's purpose, user workflow, analytical approach, outputs, codebase, editing workflow, development history, testing experience, limitations, and possible future direction. The guides will be audience-neutral and will not refer to Ricardy, the Nairobi workshop, or a specific recipient.

The documents are orientation and practical maintenance guides. They are not formal ITS integration specifications, exhaustive developer references, or claims that either tool replaces expert judgment or institutional review.

## 2. Output location and filenames

Create a new folder without altering the earlier Ricardy handover package:

`C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260909_fcv-reviewer-handovers\`

Create:

- `20260909_CPF-reviewer-handover.docx`
- `20260909_Project-screener-handover.docx`

The documents will be approximately 8-10 pages each. No existing file will be overwritten.

## 3. Shared document structure

Both documents will follow the same reader journey so that readers can compare the tools and maintainers can update the guides consistently:

1. **Purpose and intended users**
2. **What the tool does and does not do**
3. **Inputs and prerequisites**
4. **How a review works, step by step**
5. **Outputs and how to interpret them**
6. **How the tool has evolved: changes, experiments, and lessons**
7. **Testing history and what the evidence establishes**
8. **GitHub codebase and component relationships**
9. **How to edit, test, review, and deploy changes**
10. **Current status, limitations, and responsible-use boundaries**
11. **Possible future directions**
12. **Quick-start checklist and key links**

The opening sections will explain the methodology before presenting testing conclusions or readiness judgments.

## 4. Tool-specific emphasis

### 4.1 CPF FCV Reviewer

The CPF guide will explain:

- country-strategy-level review of CPFs and CENs;
- the role of the primary strategy, accompanying package documents, an RRA or equivalent diagnostic, user guidance, and current public context;
- country confirmation, review-stage selection, document processing, evidence construction, diagnostic mapping, current-context research, structured generation, validation, and bounded repair;
- the Five-minute readout, Detailed analysis, editable Word exports, corrections, and follow-on assistant;
- how RRA/current-dynamics and FCV Strategy alignment inform the review without becoming policy, eligibility, endorsement, or clearance determinations;
- the development path from the August 2026 prototype through the verified September 2026 release;
- synthetic, provider-free, browser, and provider-backed validation, including the Guinea experience and its limitations;
- the public-prototype boundary and the separate requirements for an ITS-hosted internal version.

### 4.2 FCV Project Screener

The Project Screener guide will explain:

- project- and operation-level screening;
- supported project documents, package documents, and contextual inputs;
- the three-stage workflow, Express and step-by-step modes, and stage- and instrument-aware analysis;
- FCV sensitivity, FCV responsiveness, Do No Harm, evidence traceability, differentiated approaches, and operational recommendations;
- Summary and Detailed views, reports, and follow-on functions available in the relevant build;
- the longer development history across project stages, lending instruments, knowledge-base improvements, specialist lenses, document extraction, reliability, and user-interface changes;
- testing with synthetic and public project examples, including the Somalia example and its known caveat;
- the relationship among stable `main`, later Render development branches, and ITS/QA, with every status claim dated and tied to a verified branch, commit, or deployment source.

## 5. GitHub and editing sections

The guides will assume basic familiarity with Git, Python, HTML/CSS/JavaScript, tests, and pull requests. They will avoid explaining elementary programming concepts while remaining accessible to someone unfamiliar with these repositories.

Each GitHub section will include:

- repository URL, relevant branch or release, and application entry points;
- a concise architecture map showing how inputs reach analysis, validation, presentation, and export;
- a table of key files and directories, their responsibilities, and their main dependencies;
- a change-impact map for interface wording, prompts, knowledge or registry content, extraction, structured contracts, validation, results rendering, Word export, and tests;
- local setup and the smallest relevant verification commands;
- the branch, diff review, targeted testing, pull-request, and deployment workflow;
- examples of common edits and the related files that normally need coordinated changes;
- explicit cautions around secrets, raw assessment artifacts, restricted source material, safeguards, public/internal separation, deployment branch selection, and direct changes to stable versions.

The CPF guide will preserve its package-based architecture rather than implying that it should be flattened to resemble the Project Screener. The Project Screener guide will describe its more concentrated Flask and browser code while distinguishing stable and preview functionality.

## 6. Evidence and version-control method

Before drafting, verify current state from source rather than treating the 1 September handover as authoritative:

1. Read the applicable repository instructions, README, status records, current branch, working-tree status, and recent commits.
2. Identify the relevant deployed or accepted revision for each application.
3. Reconcile repository history with dated validation and handover records.
4. Distinguish recorded historical results from checks performed for this task.
5. Do not run provider-backed assessments merely to refresh documentation.
6. Do not open or ingest restricted OPCS source documents identified by the Project Screener repository.

The earlier Ricardy package is a source, not an instruction set. Reusable factual and structural material may be adapted, but recipient-specific wording, workshop objectives, email actions, file-moving instructions, and historical task commands are out of scope.

## 7. Visual design

Use approximately three relevant visuals per document. Each visual must explain a material part of the workflow and must be traceable to the version discussed.

Preferred visual sequence:

1. intake or document-upload view;
2. workflow/progress view or a simple architecture diagram, whichever explains the process more clearly; and
3. summary or detailed-results view showing how findings and recommendations are presented.

Exclude decorative images, misleading cropped captures, duplicate views, and screenshots from a different build unless the caption explicitly explains the comparison. Every screenshot will include a short caption with its date, application/build context, and what the reader should notice.

## 8. Writing and presentation

- Use a direct World Bank technical-guide register.
- Define product-specific terms on first use.
- Use short sections, restrained tables, numbered workflows, and clearly labelled cautions.
- Avoid promotional language, unexplained implementation jargon, and raw commit-by-commit histories.
- Explain why major changes were made and what was learned, not merely that files changed.
- Separate verified current behavior, historical behavior, experimental work, and future possibilities.
- Use editable Word styles, ordinary paragraphs and tables, useful headers/footers, and page numbers.
- Do not use em dashes.

## 9. Quality assurance

For each guide:

1. Verify factual claims against repository files and dated records.
2. Check links, branch names, commit identifiers, commands, and filenames.
3. Confirm that testing claims say what was tested and what the result does and does not establish.
4. Confirm that limitations and human-review requirements are visible.
5. Generate the Word document as a new file.
6. Inspect document structure programmatically.
7. Render the document page by page and visually inspect every page for clipping, overflow, weak page breaks, unreadable screenshots, inconsistent headings, and excessive blank space.
8. Revise and rerender until both documents are visually sound.

## 10. Acceptance criteria

The work is complete when:

- two separate, self-contained Word guides exist in the approved new folder;
- each guide is approximately 8-10 pages and follows the parallel structure;
- the latest verified state of each application is accurately distinguished from historical and experimental states;
- a technically literate new contributor can understand the codebase, locate likely change points, follow the safe editing workflow, and know which tests to run;
- development and testing histories are candid but concise;
- visuals are relevant, readable, version-labelled, and correctly captioned;
- public prototype, ITS/QA, stable, preview, and internal-source boundaries are not conflated;
- neither guide is addressed to Ricardy or tied to the Nairobi workshop;
- no application code, deployment, existing handover file, restricted source, or live assessment is changed; and
- both Word files pass structural and page-by-page visual checks.

## 11. Out of scope

- Modifying either application.
- Merging the CPF Reviewer into the Project Screener.
- Re-running paid or provider-backed quality assessments.
- Creating an ITS architecture or security design.
- Updating or sending the earlier Ricardy email.
- Moving, deleting, or overwriting earlier handover materials.
- Reproducing restricted operational documents or raw model outputs in the guides.
