# CPF coordinator review redesign specification

## Follow-up revision: simplified draft review comments

The owner's follow-up instructions supersede the earlier feedback and email-toolbar
choices in this document. Remove optional pilot feedback and the separate correction
box. Label the output **Draft review comments**. Provide one Copy control and retain
wording edits automatically. Use one prose query box for tailoring, discussion and
explicit assessment updates, with no task dropdowns or assistant branding. Three
small example prompts prefill the box without sending. The existing single model
response signals its action; ambiguous requests are answered or clarified, never
silently treated as a correction. Suggestions cover tone, focus, condensation and
elaboration. Tailoring updates the comments from the current draft and reviewed
evidence without changing the findings. Assessment updates use the existing child
review and refresh its derived outputs, while preserving older wording for comparison.

Adapt the Project Screener's "LLMs are not magic" caveat for CPF/CEN context and review
stage. The Screener itself is read-only background. No additional model-routing or
classification call is required, and no provider or hosting change is part of this
revision. See the [revision record](docs/validation/2026-10-12-review-comments-simplification.md).


Date: 12 October 2026
Status: agreed design consolidated from the working discussion
Repository baseline: a210b29 (origin/main); documented application release e1eabcf.
Feature branch: feat/coordinator-review-redesign.

## Purpose and boundaries

Adapt the CPF/CEN reviewer into an evidence-linked drafting aid for Country
Coordinators preparing departmental comments. Expert country knowledge and final
responsibility remain with the coordinator and the established review process.

The three products are an authoritative detailed note, a five-minute summary and
an unsigned peer-review email draft. They use one set of findings. The email is
the final drafting product and is generated automatically after analysis without
a required coordinator checkpoint.

The FCV Project Screener and operations review are separate and unchanged.
Formal PC14 assessment and FCV Envelope decisions remain separate processes.
Timing is not a design constraint.

The public prototype accepts public or approved non-sensitive inputs. The target
internal ITS installation can supply separately approved references and style
examples. Internal policy text, confidential examples, uploads, corrections,
feedback and final comments must remain outside this public repository.
Internal hosting alone does not establish approval to load a particular source.

## User journey

1. Upload the primary CPF/CEN and select the review stage.
2. Add available package documents and diagnostics. Supporting files may include
   the CLR, previous CPF, results framework, Envelope notes, previous comments and
   decision records. Optional coordinator guidance and CMU review questions are
   separate fields.
3. Generate the detailed note, summary and draft email in one user action.
4. Read the default five-minute summary, open the detailed note or email, and
   optionally edit wording or supply a substantive correction.
5. Copy or download outputs and optionally provide feedback.

Country identification retains the existing automatic detection and manual
correction. Country-context framing is a proposed interpretation with a short
rationale, evidence and uncertainty. A coordinator can override it without a new
mandatory confirmation screen. Official list status, Envelope status and
contextual framing are separate; the model must not turn a proposed framing
into an official classification. Only approved dated reference data can establish
official status. Unavailable status remains unknown.

Context changes analytical expectations, not the obligation to consider material
risks. Crisis contexts emphasise feasible delivery, local platforms and authorities'
actual influence. Transition contexts examine windows of opportunity and phased
engagement. Conflict-affected contexts examine critical actions, commitment,
selectivity and security. Prevention contexts examine emerging and latent risks.
A verified absence from the FCS list permits lighter presentation, but does not
justify suppressing a material strategic concern.

## Analytical findings

Every completed new-format review includes exactly one concise qualitative
finding for each of these questions, in this order:

1. Drivers and priorities: how key FCV drivers and sources of resilience informed
   selected outcomes and priorities.
2. Critical actions and commitment: the reforms, investments or other actions
   that matter, and evidence of authorities' willingness and ability to act.
3. Program implications: consequences for selectivity, sequencing, geography,
   delivery, ambition and the potential for lasting development impact.
4. If/Then calibration: conditions that warrant changes and the corresponding
   strategic or operational response.

A finding may explicitly state that available evidence limits assessment. Missing
documents, incomplete coverage or digests must not become evidence of absence.
Each supported finding has real evidence links and can refer to detailed priority
comments. A finding does not automatically require an email comment.

Distinguish:
- an explanation gap from a concern with the program itself;
- stated intentions from demonstrated actions, capacity and contrary evidence;
- addressing a driver from mitigating or adapting to it;
- authority commitment from the practical ability to influence country outcomes;
- an evidenced fact from analytical interpretation or a proposed adjustment.

Use the CLR, previous CPF, Envelope milestones and current evidence where
available to examine what has changed. Do not infer commitment merely from a
forward-looking CPF statement. Where a driver sits outside the WBG's direct
mandate, examine adaptation, partnerships and implications for the program
rather than inventing a WBG reform responsibility.

## Diagnostic, Strategy and current-context connections

Retain the existing RRA map and Strategy assessments internally, with their
evidence and coverage safeguards. The reader-facing note uses a concise synthesis
rather than duplicate matrices. Relevant diagnostic and Strategy connections also
appear naturally within the findings and priority comments.

Use approved Strategy references for the existing anticipation, differentiation,
One WBG jobs and toolkit/partnerships/staffing lens. Do not substitute the four
analytical questions for these Strategy elements.

Treat the diagnostic as a dated baseline. Separate structural conditions from
subsequent developments and consider positive openings as carefully as risks.
Current claims require dated supporting evidence and qualified source breadth.
Unverified hypotheses cannot become confident directional claims.

## Stage-specific advice and recommendation destinations

Use the existing stage profiles as substantive constraints throughout analysis,
prioritisation, email drafting and corrections.

| Stage | Main emphasis |
| --- | --- |
| Early drafting / Concept Note | Framing, theory of change, selectivity and choices still open |
| Decision review | Specific feasible revisions to objectives, results, risks and delivery |
| ROC/OC | Earlier-comment follow-through, discrete meeting questions and limited feasible adjustments |
| Finalisation | Wording, factual corrections, consistency and results-framework refinements |
| Response to comments | Responses linked to the supplied comments, after independent assessment |

Retain the existing finalisation option. Do not broaden ROC/OC into routine
program redesign. A material concern can be identified with an appropriately
bounded response or meeting referral even when substantial revision is no longer
feasible. Early-stage advice can examine alternatives more deeply.

Each priority includes its practical destination:
- primary text or annex;
- results framework;
- meeting minutes or decision note;
- annual business planning or internal implementation/management.

The existing target locator anchors the issue in the reviewed document; the
destination explains where the response belongs. Sensitive issues need not be
recommended as public CPF wording. Destination is issue-specific: some scenario
language belongs in the CPF while monitoring responsibilities may belong in a
meeting record. No blanket rule sends every scenario outside the CPF.

## Independent analysis and earlier comments

Recognise dedicated prior-comment and decision-note uploads automatically using
document structure and purpose, with an optional manual role correction for
misidentified files. Dedicated prior-comment material is not supplied to the
initial substantive review, research focus or digest used for that review.

Prior-comment sections within package documents require equivalent separation.
The primary CPF itself remains the full primary document; its ordinary references
to previous decisions are legitimate package content, not instructions.

After fresh findings pass validation, perform a separate follow-through pass using
the prior comments and current-document evidence. It reports addressed, partly
addressed or unresolved items with evidence; insufficient coverage is explicit.
This pass cannot rewrite the independent findings or the selected priorities.
Coordinators can subsequently supply a substantive correction through the normal
correction workflow. Ambiguous source roles are disclosed rather than silently
treated as current facts.

## PC14 and Envelope observations

Use short qualitative observations only where a material CPF gap or package
inconsistency is supported. No compliance rating, provisional compliance view,
eligibility decision, template audit or separate Secretariat output.

An observation should identify the underlying issue and a feasible CPF adjustment
or coordination point. Relevant material findings may enter the priorities;
immaterial observations need not appear. Do not assert applicability from model
inference. When applicable reference data are unavailable, describe the underlying
drivers-to-outcomes issue without making an official policy claim.

Uploaded Envelope notes can inform coherence on drivers, commitments and program
recalibration. The tool does not take over the Secretariat's assessment.

## Output structure

### Detailed note

1. Overall assessment and priorities calibrated to stage.
2. Brief RRA, current-context and relevant Strategy connection.
3. Four concise findings with evidence links.
4. Prioritised comments: existing treatment, concern, implications, practical
   response, recommendation destination and evidence.
5. Earlier-comment follow-through, where material is available.
6. Related corporate considerations, only where material.
7. Coverage and uncertainty.

Sections 2 and 3 summarise; section 4 carries the developed argument. Avoid
repeating the same country background or recommendation three times. The website
retains coverage disclosure. Word exports retain the established opening caution
and convey material uncertainty within the relevant findings, consistent with
the existing export convention.

### Five-minute summary

A concise overall assessment and the same priority order as the email. Material
caveats remain visible. It does not use compliance verdicts or official category
claims to simplify uncertain analysis.

### Peer-review email

Use the style and editorial emphasis of the approved departmental examples,
including Shubham's tone as a base. No signature or named sign-off is generated.
Opening recognition of strengths must be supported; recognition of progress on
prior comments requires a supported follow-through finding.

Organise by CMU questions when supplied, otherwise by the most consequential
themes. Use descriptive headings. Three to five comments is a preference, never
a quota; one well-developed strategic argument can be appropriate. Tier 1/Tier 2
is optional when it meaningfully distinguishes meeting priorities from task-team
guidance. Suggested wording is included only where useful and feasible.

Every substantive email comment links to the underlying priorities or findings.
The email cannot add new country facts, policy determinations or recommendations
that have not passed review validation. Questions with insufficient evidence
receive a qualified response rather than an invented answer.

Approved confidential style examples are runtime inputs for the internal
installation, never public fixtures. They influence tone and structure, not facts
or conclusions about another country.

## Editing, corrections and feedback

Store email wording edits as an overlay on the generated email. These edits do not
silently alter findings or evidence. Refresh and email download preserve them.

Substantive corrections use the existing linked child-review/rerun mechanism and
regenerate affected findings, summary and email consistently. Prior wording edits
remain available; a new generated draft must not silently overwrite user work.
Clearly mark edits based on an earlier analysis. If a natural-language request is
ambiguous between a wording edit and a substantive correction, ask one question.

Optional feedback consists of an accuracy/usefulness rating, correction text and
a final-comments upload. No feedback is required for generation, editing or
download. Feedback and final comments are evaluation material, not analytical
inputs, instructions or automatic additions to the style corpus.

Reuse the session store, lifetime and deletion controls. The public prototype's
24-hour lifecycle is not extended. Longer-term internal evaluation storage needs
an explicitly governed internal destination; this design does not silently create
a public archive. Explain the configured lifetime wherever feedback is collected.
The feedback upload follows existing type, size, extraction and safe-failure
controls, and supports authorised non-sensitive inputs in the public test track.

## Implementation constraints

Start from the refreshed merged baseline, including October large-package
coverage, full primary reading, RRA provenance, digest disclosure, provider stream
handling, source-backed claims and bounded repair. Preserve those behaviours.

Extend current Pydantic contracts, stage profiles, review engine, validators,
routes, session payload, frontend and native Word exports. Add focused modules
only for clearly separate email generation and post-review follow-through.
Keep provider configuration, hosting and existing model selections intact.

Use current approved registry/reference mechanisms. Version and hash externally
supplied internal references and style examples, with approved ownership. Public
synthetic tests must exercise the interfaces without copying confidential content.

Legacy sessions remain readable for their existing lifetime; new analysis uses
versioned new fields. Use explicit legacy behaviour rather than inventing four
findings for an old result. Do not introduce permanent compatibility machinery.

## Acceptance and verification

- All four findings appear once; RRA and Strategy links are compact and grounded.
- Stage limits survive review, repair, email generation and correction.
- Official classifications and policy determinations cannot be inferred.
- Prior comments cannot steer initial review or leak through digests/research.
- Every priority has a destination and real supporting evidence.
- Summary and email use the same priorities and preserve qualifications.
- Emails have no named signature; optional tiers and CMU questions work.
- Wording edits survive refresh/download and are not lost during corrections.
- Feedback is optional and follows expiry/deletion; final uploads never enter review.
- Invalid references, over-budget inputs and unreadable required content retain
  safe failures; covered-document absence safeguards remain enforced.
- Synthetic tests and browser smoke are distinguished from analytical quality.
  Paid runs and deployment follow the existing repository authorisation ladder.
