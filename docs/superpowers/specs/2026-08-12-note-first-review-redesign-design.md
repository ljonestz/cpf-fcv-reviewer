# CPF FCV Reviewer: Note-First Review Redesign

**Date:** 2026-08-12

**Status:** Approved design, awaiting written-spec review

**Scope:** Review output, stage-sensitive recommendation logic, landing-page intake, results presentation, and DOCX parity

## 1. Purpose

Redesign the CPF FCV Reviewer so that its primary output reads as a concise, tailored technical review note rather than a collection of finding and recommendation cards. The review should help a CPF team understand the overall quality of the FCV framing, identify the most important revisions, and see exactly where and how to strengthen the draft.

The design draws on the prose, prioritization, and document-specific recommendations used in the existing CPF peer-review skill and recent Sahel review notes. It preserves the prototype's evidence traceability, safety boundaries, and one-run Express workflow.

## 2. Current Problem

The current model contract separates findings, recommendations, priority-question responses, and limitations into small independent objects. The web and DOCX renderers expose those objects directly. This produces a fragmented output with repeated headings, short subsections, and weak narrative flow.

The landing page also asks for country manually, treats all supplementary files as one group, and gives limited explanation of how the review works. It does not reflect the clearer hierarchy and guidance used in the FCV Project Screener.

## 3. Design Principles

1. **Note first.** The review must read as connected analytical prose, with headings serving the argument rather than exposing the underlying schema.
2. **Actionable and document-specific.** Every priority issue must identify a feasible revision and its target document or section.
3. **Prioritized, not exhaustive.** The output should focus on changes that materially improve FCV sensitivity or responsiveness.
4. **Stage-realistic.** The review stage controls the scale, tone, location, and feasible length of proposed revisions.
5. **Evidence remains inspectable.** Citations and source locations stay attached to claims but do not interrupt the main reading experience.
6. **CPF-led assessment.** The primary CPF or CEN remains the principal object of review. Package and contextual documents inform the assessment without displacing that lens.
7. **Advisory boundaries remain explicit.** The tool does not make policy-compliance, clearance, eligibility, or formal applicability determinations.
8. **One Express workflow.** There is no user-visible step-by-step mode.

## 4. User Workflow

### 4.1 Landing page

The landing page will follow the broad visual language and explanatory structure of the FCV Project Screener while remaining specific to CPF review.

It contains:

- A short description of the tool's purpose, intended users, and advisory status.
- A concise explanation of what the review examines and what it does not determine.
- A single Express review form.
- A modal or pop-up explaining the backend review process in plain language.
- A clear review button and a progress state that describes the internal stages without requiring user intervention.

### 4.2 Upload buckets

Files are divided into three visibly distinct groups:

1. **Primary document:** one CPF or CEN. This is required and receives the greatest analytical weight.
2. **CPF package documents:** supporting package material such as a Results Matrix, Completion and Learning Review, Performance and Learning Review, implementation arrangements, or related annexes.
3. **Wider contextual material:** documents that help test the framing but may sit outside the formal package, such as an RRA, Risk and Resilience Assessment, country diagnostics, FCV strategy material, or other contextual analysis.

The backend must retain the bucket identity of every uploaded file. The prompt will use that identity to distinguish primary claims, package corroboration, and contextual challenge or nuance.

### 4.3 Inputs

- **Country:** inferred from the primary document. The detected country is shown for confirmation on the progress/results screen and may be corrected if detection is uncertain or wrong.
- **Review stage:** required.
- **Detail level:** optional, with `Standard` selected by default.
- **Additional guidance:** collapsed by default. It contains an optional free-text instruction and optional priority issues the user wants examined.

The additional guidance is treated as review emphasis, not as evidence and not as authority to override guardrails.

## 5. Detail Levels

Detail level affects model generation, not merely front-end truncation.

| Level | Intended output | Priority areas | Typical use |
|---|---|---:|---|
| Brief | Approximately one page | 2-3 | Rapid management readout or a tightly constrained review |
| Standard | Approximately two pages | 3-5 | Default technical review |
| In-depth | Approximately three pages | 4-7 | Fuller peer-review note where the document set supports it |

These are target ranges, not hard word-count guarantees. The model should produce less material when evidence is thin rather than padding the note. The selected review stage can further constrain the practical length of individual recommendations.

On the results page, evidence and supporting detail can be expanded or collapsed without regenerating the review. Expansion reveals existing generated detail; it does not call the model again.

## 6. Stage-Sensitive Review Logic

The stage rule must affect four dimensions:

1. **Permissible scale of change:** from strategic reframing to fine-tuning.
2. **Feasible insertion length:** how much additional text the target document can realistically absorb.
3. **Likely target locations:** where changes can still be made at that stage.
4. **Recommendation language:** challenge, revise, sharpen, clarify, or correct as appropriate.

### 6.1 Stage matrix

| Stage | Review posture | Permissible change | Length discipline | Typical targets |
|---|---|---|---|---|
| Early drafting / PCN | Strategically open but text-constrained | May challenge selectivity, causal logic, outcome architecture, sequencing, and delivery approach | Recommend concise framing, short bullets, or issues to carry into the full CPF; do not prescribe large insertions into a short PCN | Concept framing, proposed outcomes, design questions, preparation priorities |
| Concept review | Strategic and architectural | May recommend material changes to objectives, results chains, partnerships, risk treatment, and implementation logic | Prefer compact replacement framing and clearly scoped restructuring | Main narrative, objectives, results architecture, package-development priorities |
| Decision review | Specific and decision-oriented | May recommend substantive but bounded revisions | State the exact decision, paragraph, table, indicator, or arrangement to revise | Objectives, Results Matrix, risk section, implementation arrangements |
| ROC / OC | Targeted and management-facing | Prioritize issues that affect decision quality or implementability | Avoid broad rewrites; frame changes as discrete decision-ready edits | Management decisions, commitments, indicators, risks, accountabilities |
| Finalization | Fine-tuning | Limit advice to high-value clarification, factual correction, caveats, indicator refinement, internal consistency, and precise additions | Recommend minimal text and feasible edits; do not propose wholesale redesign | Specific paragraphs, table cells, indicators, cross-references, short caveats |
| Response to comments | Resolution-oriented | Link advice to the issue being addressed and propose an accept, partially accept, explain, or verify response | Keep both document edits and response language concise | Comment-response matrix and corresponding document location |

The model must not equate an early stage with permission to add unlimited text. PCN-stage advice may be strategically ambitious, but the recommended immediate edit must fit a short concept document. Larger issues should be framed as preparation priorities for the subsequent CPF rather than as long PCN insertions.

At finalization, the model may still identify a material weakness, but its recommendation must distinguish between a feasible final-stage edit and a broader issue that cannot realistically be redesigned at that point.

### 6.2 Validation

Stage sensitivity must be validated structurally, not left solely to prompt wording. Each priority area records a recommendation scale and target location. Validators flag:

- wholesale redesign language at finalization;
- long-form insertion proposals at Early drafting / PCN;
- recommendations without a target document or location;
- recommendations that conflict with the selected stage posture; and
- response-to-comments advice that is not linked to a comment or issue.

## 7. Review Output

### 7.1 Overall structure

The primary result follows this order:

1. **Overall read**
2. **What to revise**
3. **Priority areas for strengthening**
4. **Limitations and document coverage**

There is no separate “Questions for confirmation” section. If evidence is incomplete, the note states the limitation briefly and calibrates the claim. It must not manufacture a question list to fill the output.

### 7.2 Overall read

The opening is a short narrative judgment, normally one or two paragraphs. It should:

- state the bottom line first;
- identify genuine strengths as well as the central weakness or opportunity;
- distinguish FCV sensitivity from FCV responsiveness where relevant;
- reflect the selected review stage; and
- avoid generic country-context exposition unless it is necessary to explain the judgment.

### 7.3 What to revise

This is a concise, numbered summary of the highest-priority revisions. It normally contains three to five actions, adjusted for detail level and evidence strength.

Each item is a compact action statement. It does not repeat the full analysis. Selecting an item scrolls or links to its corresponding priority area in the web result.

### 7.4 Priority areas for strengthening

Each priority area is a coherent prose section with a self-explanatory heading. The section contains:

- a clear lead sentence stating what the CPF does well, does incompletely, or does not yet address;
- a short explanation grounded in the uploaded material and relevant context;
- why the issue matters for the CPF's strategy, implementation, risks, or results;
- a stage-appropriate recommended action;
- the specific target document and, where available, section, paragraph, table, or indicator; and
- attached evidence references.

Recommendations are embedded within the relevant priority area. There is no detached recommendation-card section.

The note may group issues by calibrated priority, but it should not mechanically reproduce “critical/moderate/opportunity” headings when a more natural thematic structure reads better. The model should identify the few issues that most affect the CPF rather than generate one section for every diagnostic pathway.

### 7.5 Evidence display

Evidence is collapsed by default in the web result. Expanding it shows:

- source document;
- page, section, paragraph, table, or other locator when available;
- a short supporting excerpt or faithful evidence summary; and
- confidence or coverage caveat when material.

The visible note uses restrained inline source markers. Evidence IDs and internal schema terminology are not shown in the primary prose.

### 7.6 Limitations and document coverage

The closing is brief. It identifies missing or unreadable material, important scope constraints, and any resulting calibration of the assessment. It does not present open questions.

## 8. Output Contract

The internal contract should support narrative composition while retaining machine-verifiable evidence links. A suitable conceptual structure is:

- `overall_read`
- `revision_summary[]`
- `priority_areas[]`
  - `heading`
  - `assessment`
  - `why_it_matters`
  - `recommended_action`
  - `target_document`
  - `target_locator`
  - `recommendation_scale`
  - `evidence_ids[]`
  - `sensitivity`
- `limitations[]`
- `document_coverage`
- metadata including `review_stage`, `detail_level`, and detected country

The exact Pydantic types belong in the implementation plan. The design requirement is that the contract preserves the note's narrative units instead of forcing separate finding and recommendation collections.

## 9. Prompt Design

The review prompt will instruct the model to:

- synthesize a senior-facing technical note from the evidence pack;
- lead each substantive section with a clear analytical point;
- prioritize a small number of CPF-specific issues;
- pair each issue with a feasible, document-specific action;
- apply both the stage matrix and selected detail level;
- use the primary CPF as the main lens, package documents as secondary evidence, and wider contextual material to test or nuance the CPF framing;
- avoid generic FCV commentary, exhaustive pathway reporting, and thin subsection-by-subsection summaries;
- avoid unsupported claims and prohibited policy determinations; and
- return structured data matching the narrative contract.

Prompt examples should demonstrate the desired shape and tone using synthetic or cleared text. They should not copy confidential review language into the application bundle.

## 10. Web Results Experience

The results page is a readable note on a restrained white content surface, consistent with the FCV Project Screener's visual language.

- Overall read appears first with no dashboard framing.
- “What to revise” is a compact orientation block.
- Priority areas follow as normal document sections, not equal-sized cards.
- Recommended actions are visually distinct within each section but remain part of the prose flow.
- Evidence uses accessible expand/collapse controls.
- Review stage and detail level appear as quiet metadata.
- Download, start-new-review, and correction actions remain available without dominating the note.

The page must remain usable on narrow screens and retain keyboard-accessible disclosure controls.

## 11. DOCX Export

The DOCX export mirrors the web note's order and wording:

1. Title and short advisory label
2. Overall read
3. What to revise
4. Priority areas for strengthening, with embedded recommended actions
5. Limitations and document coverage
6. Reproducibility metadata in a restrained appendix or final technical section

The DOCX should read as a standalone peer-review note. Evidence references may appear as concise source lines or endnotes beneath the relevant section. Internal evidence IDs, validation codes, and application mechanics should not interrupt the main document.

## 12. Country Detection and Errors

Country detection uses the primary document's title, cover material, and high-confidence introductory text. If one country is detected confidently, the review proceeds and displays it. If detection is ambiguous, the interface pauses before model review and asks the user to confirm or correct the country.

Other error behavior:

- A missing primary document blocks submission with a specific message.
- Unsupported or unreadable files are identified by name and do not silently disappear.
- Missing optional documents reduce coverage but do not block the review.
- Thin evidence produces a shorter, more qualified note.
- Model-contract or validation failures use the existing bounded repair path.

## 13. Model Coordination During Development

Codex development work may route bounded implementation and test tasks to Luna High, while Sol Medium retains planning, synthesis, integration review, and final verification. Delegated output is not accepted without review against the specification and repository tests.

This development routing is separate from the CPF Reviewer's runtime model configuration. Changing the application's production model is outside this design's scope.

## 14. Testing Strategy

### 14.1 Contract and prompt tests

- The new contract requires a complete narrative unit for every priority area.
- Every priority area has evidence links and a target document or location.
- Detail-level instructions produce bounded priority counts and target lengths.
- The output contains no question-for-confirmation section.

### 14.2 Stage tests

Use the same synthetic evidence pack across all stages and assert that recommendation scale and feasible insertion length change appropriately.

Specific tests cover:

- an Early drafting / PCN review that recommends a strategic change through a concise PCN edit plus a later preparation priority;
- a Decision review that identifies exact sections and results changes;
- a Finalization review that avoids structural redesign language;
- a Response to comments review that links actions to the relevant issue; and
- validator rejection or repair of stage-inappropriate output.

### 14.3 Rendering tests

- Web and DOCX contain the same substantive sections in the same order.
- Evidence is collapsed by default on the web and remains accessible by keyboard.
- The revision summary links to the matching priority area.
- Internal evidence IDs do not appear in the primary prose.
- Brief, Standard, and In-depth results render without broken or empty sections.

### 14.4 Reference-based evaluation

Run representative Sahel CPF materials through the revised flow and compare the result with the existing overview and detailed peer-review notes. Evaluation is rubric-based rather than a demand for textual similarity.

The rubric checks:

- clarity of the overall judgment;
- CPF and country specificity;
- prioritization;
- actionability and target precision;
- stage realism;
- distinction between sensitivity and responsiveness;
- evidence fidelity;
- narrative coherence; and
- absence of generic pathway-by-pathway output.

Reference documents remain evaluation material and are not bundled into tests or committed if they contain restricted content.

## 15. Implementation Slices

The work should be implemented and reviewed in three slices:

1. **Narrative output foundation:** contract, stage/detail rules, prompts, validators, web result renderer, and DOCX renderer.
2. **Guided intake:** three upload buckets, country inference and confirmation, detail selector, collapsible additional guidance, explanatory content, and backend modal.
3. **Evaluation and polish:** reference-based runs, stage comparison tests, responsive/accessibility checks, and final output tuning.

The first slice is the highest priority because output quality is the primary product problem. The landing-page redesign should not delay validation of the note structure.

## 16. Acceptance Criteria

The redesign is complete when:

- the default result reads as a connected technical note rather than a set of mini cards;
- the opening provides a defensible overall judgment and the top revision priorities are immediately visible;
- every priority area contains a CPF-specific explanation and a feasible, document-specific action;
- recommendations demonstrably change with the selected review stage, including PCN text constraints and finalization fine-tuning;
- users can choose Brief, Standard, or In-depth generation and expand evidence without regeneration;
- country is inferred and can be corrected when uncertain;
- the landing page presents three document buckets and collapsible additional guidance;
- there is no questions-for-confirmation output section;
- web and DOCX outputs have substantive parity;
- existing policy and evidence guardrails continue to pass; and
- representative Sahel evaluation runs meet the narrative-quality rubric without exposing confidential source material in the repository.
