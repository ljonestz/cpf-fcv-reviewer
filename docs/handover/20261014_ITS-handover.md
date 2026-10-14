# CPF FCV Reviewer ITS Handover

Main changes and internal integration requirements — 14 October 2026

## 1 Status

The updated CPF/CEN reviewer is ready to hand over to ITS for integration and supervised acceptance testing. The redesign is on `feat/coordinator-review-redesign`, in [draft pull request 55](https://github.com/ljonestz/cpf-fcv-reviewer/pull/55). The latest application commit is `9a049c0`; the subsequent documentation checkpoint is `a726e64`. These changes have not been merged to main or deployed to the public site. This brief describes the candidate code, rather than the currently deployed prototype.

The changes respond to Maimouna's request for more systematic, strategic and practical CPF comments. The tool helps FCV Country Coordinators develop a few consequential comments while retaining responsibility for the final review. It remains CPF/CEN only. Operations and the FCV Project Screener remain separate.

## 2 Analytical framework and review stage

Every new-format review now develops four qualitative findings, with evidence, implications and practical responses. These are the backbone of the detailed note, summary and draft comments.

- **Drivers and priorities:** whether the CPF explains how key FCV drivers and sources of resilience informed its outcomes and priorities.
- **Critical actions and commitment:** which reforms, investments or other actions matter most, and what supports the authorities' willingness and ability to act. Where available, the CLR, earlier CPF and other evidence help distinguish intentions from demonstrated action.
- **Program implications:** how that assessment affects selectivity, sequencing, geography, delivery arrangements, ambition and lasting development impact.
- **Adapting to changing conditions:** whether the CPF already links plausible changes in conditions to adjustments in engagement, including arrangements that are not labelled If/Then. Where material gaps exist, the review proposes a few relevant conditional scenarios and clearly identifies them as suggestions.

Review stage shapes the advice throughout. Concept-stage comments can address strategic choices and the theory of change. ROC/OC comments focus on follow-through, discrete clarifications and feasible adjustments; material strategic concerns can still be raised with an appropriately bounded response. Finalisation advice focuses on wording, consistency and results-framework refinements. Recommendations identify where an adjustment belongs, such as CPF text, the results framework, meeting records or internal implementation planning.

The RRA remains a dated diagnostic baseline, linked concisely to the program and the approved FCV Strategy references. The review distinguishes structural conditions from subsequent developments and considers positive openings as well as deterioration. Country-context framing is a proposed interpretation that the coordinator can correct, not an official classification or a mandatory confirmation step.

Formal PC14 and FCV Envelope reviews remain with their established processes and the Secretariat. The tool offers a brief qualitative push where a material CPF gap or inconsistency warrants it. It does not give compliance ratings or eligibility determinations. Previous comments are checked separately after the independent assessment.

## 3 Readout and Word export changes

The output has been revised to make the argument readable across all three products. The four findings now use developed prose rather than compressed notes. Each analytical heading has a short explanation so a new reader understands what is being assessed. The summary covers all four questions, alongside the concise diagnostic and Strategy connection.

- **Priority measures in the summary:** each starts with a short prose explanation of the finding and why it matters. The blue recommended-response area then gives a brief sentence. A pointer directs the reader to the detailed note for the full recommendation and its qualifications.
- **Detailed note:** keeps the fuller assessment, evidence-based implications and practical recommendations. The main narrative avoids repeating evidence lists beneath every section.
- **Evidence traceability:** moves into a grouped annex. In the browser it is initially collapsed and placed below draft review comments. Both Word exports put it after the comments. Evidence links, quotations and canonical locators remain subject to the existing validation.
- **References in reader prose:** review and comments prompts prefer verified section or subsection names, or a description of the relevant passage, instead of page or paragraph numbers. They must not invent headings. Structured evidence locators are retained internally.
- **Both Word downloads:** include the currently displayed draft review comments before the evidence annex, including saved wording and any relevant fallback or stale-draft notice. The thematic comment headings use native Word styles. Older-format reviews retain their previous rendering behavior.

The colleague-review Word copies dated 14 October reflect the owner's revised order and shorter summary responses. They also include editorial condensation and section-reference corrections to the accepted Guinea output. Their exact wording should therefore not be treated as a guarantee of what a future model run will generate.

## 4 Draft review comments and the query box

The final drafting product is now called **Draft review comments**. It is unsigned and uses the department's concise management tone as a base. The structure can follow CMU questions or a few descriptive themes; Tier 1/Tier 2 is used when useful. Three to five comments is a preference, not a quota. There is no requirement to turn each analytical finding into a separate comment.

The interface is deliberately light. Optional feedback collection and the separate correction box have been removed. Users can copy the comments, edit their wording directly, or use one prose query box under **What would you like to do next?** There are no task dropdowns or extra suggestion links between the short introduction and the input. Users can ask a question or request a change in tone, emphasis or length without entering an assistant workflow.

Wording changes remain distinct from substantive assessment updates. Tailoring uses the current comments and reviewed evidence; an explicit assessment update refreshes the affected findings and derived outputs. Ambiguous requests are answered or clarified rather than silently changing the assessment.

If optional comments drafting fails, the app shows a clearly labelled, editable fallback assembled from validated recommendations without an additional model call. Saved wording takes precedence. Refresh and exports preserve the displayed draft and its status. The output also carries the caution beginning **Be aware: LLMs are not magic, and neither is the CPF FCV Reviewer**, reinforcing expert judgment and stage-sensitive use.

## 5 Verification and example documents

Application commit `9a049c0` passed all **1,821 provider-free Linux CI tests**, including Gunicorn concurrency checks. The documentation checkpoint also passed CI. A dedicated Edge smoke test checked the new summary, navigation to detail, comments and annex order, refresh, mobile layout and both downloads. These browser checks used synthetic content and no paid model call.

An earlier paid Guinea CPF/RRA assessment on `b75719c` produced a readable first draft with developed findings and unsigned comments. It remains one historical country case with limited current-context evidence. The latest descriptive-reference prompt changes have not been exercised in a fresh model run; passing functional checks does not establish factual or analytical acceptance across countries.

Two companion files in the main repository folder are suitable for colleague review:

- `20261014_Guinea-CPF-summary.docx` — the revised five-minute readout, draft comments and evidence annex; eight rendered pages in total.
- `20261014_Guinea-CPF-detailed.docx` — the detailed note, draft comments and evidence annex; eleven rendered pages in total.

All pages of these revised copies were visually inspected. The original files were preserved. These are edited example outputs, not new model runs. No additional paid call was used for the latest presentation changes or this handover.

## 6 What ITS needs to carry forward

ITS should take the candidate branch and preserve the complete behavior across analysis, browser presentation and Word exports. The main implementation locations are `contracts.py` and `review_profiles.py` for analytical structure and stage; `prompts/review.md` version 4.1.2 and `prompts/peer_email.md` version 1.1.2 for model instructions; `static/app.js` and `templates/index.html` for presentation; and `routes.py`, `email_draft.py` and `export_docx.py` for comments state, fallback and downloads. These application files sit under `src/cpf_fcv_reviewer/`; prompts are in the repository's `prompts/` folder.

Three items remain for internal rollout:

- **Approved model and research route:** this branch still uses the direct Anthropic gateways. The separately developed mAI adapter is not integrated into this candidate. The recorded 4 October Desktop access was for local DEV testing; it does not establish hosted application access or permission for internal retrieval. ITS needs the approved hosted route and a successful end-to-end review with evidence validation.
- **Internal hosting and document access:** confirm the deployment, access controls, approved reference material and durable session configuration. The existing SQLite-backed session option is available; the public pilot's volatile storage is not evidence of internal operational readiness. The current public prototype remains limited to public or approved non-sensitive inputs.
- **Coordinator acceptance:** test representative Concept and ROC/OC packages and inspect findings, recommendations, comments, references and both Word exports. Check that sensitive recommendations go to a suitable internal record and that missing evidence remains qualified. This can use the agreed light-touch drafting workflow rather than adding mandatory feedback forms.

The code and example outputs are ready to share for this handover. Internal production release still depends on the approved integration and acceptance checks above.

### Source records

- [Draft PR 55](https://github.com/ljonestz/cpf-fcv-reviewer/pull/55)
- [Application CI for 9a049c0](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/38562282729)
- [Documentation checkpoint CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/38563460149)
- [Reviewed brief presentation and export validation](../validation/2026-10-14-reviewed-brief-layout.md)
- [Coordinator redesign specification](../../20261012_cpf-coordinator-redesign-spec.md)
