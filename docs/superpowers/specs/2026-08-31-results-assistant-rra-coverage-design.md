# CPF reviewer results, assistant, and RRA coverage design

**Date:** 2026-08-31
**Status:** Approved design for implementation planning
**Scope:** Public CPF FCV Reviewer only. The stable FCV Project Screener remains unchanged.

## Objective

Make the completed review more useful to CPF/CEN reviewers without redesigning the application:

1. rebalance the five-minute readout toward the priority measures;
2. simplify the detailed presentation and Word note;
3. replace sampled RRA analysis with a full-document diagnostic map; and
4. replace the prominent correction box with a genuine, persistent follow-on assistant.

The implementation should reuse existing contracts, prompts, session persistence, streaming patterns, and visual language wherever practical. It must not introduce a vector database, account system, new frontend framework, or unrelated refactor.

## 1. Five-minute readout

The readout keeps the existing tab and overall assessment, then presents content in this order:

1. **Overall assessment.** Retain the existing concise prose.
2. **RRA and current FCV dynamics.** A visually distinct prose panel containing no more than two short paragraphs: the main alignment judgment, followed by the most material gap and any current-evidence qualification.
3. **FCV Strategy contribution.** A second visually distinct prose panel containing no more than two short paragraphs synthesizing the four strategic shifts.
4. **Priority measures to strengthen the CPF/CEN.** Three substantive summary cards. Each card contains the title, a concise summary of the gap and proposed response, and a link that selects the detailed tab and focuses the corresponding full recommendation.

The RRA and FCV Strategy panels do not need links to their detailed sections; the two result tabs make that navigation intuitive. Priority links remain because they take the user to a specific recommendation rather than merely another view.

The two analytical panels should read as prose, not tables. Their visual distinction should use the application's existing restrained panel styling and colors rather than introduce a new component system.

### Narrative source

`alignment_readout` remains the dedicated RRA/current-dynamics summary and receives tighter prompt length guidance. Add one dedicated concise FCV Strategy synthesis field to the model-authored result rather than attempting to truncate or concatenate the four detailed assessments in JavaScript. Priority summaries should be rendered from the existing priority-area content; no second set of model-authored recommendations is required.

## 2. Detailed analysis

The detailed analysis remains structurally and visually close to the current implementation.

### RRA driver cards

Display four rows:

- **Driver**
- **CPF response**
- **Remaining gap**
- **Status and confidence**

The visible CPF response must be a natural, self-contained paragraph that incorporates the relevant delivery mechanism and result/indicator where useful. The existing `delivery_mechanism` and `result_or_indicator` contract fields can remain for structured generation and validation, but the prompt should require `cpf_response` to integrate their material content and the frontend should no longer render them as separate rows.

Combine status and confidence in one compact row, for example `Partially aligned · Medium confidence`. Do not display gap locus. Gap locus may remain in the contract because it supports validation and analytical logic.

### FCV Strategy cards

Display three rows:

- **Strategic shift**
- **Assessment**
- **Status and confidence**

Do not display gap locus.

### Evidence presentation

Remove the top-level Evidence Status disclosure, the separate Traceability disclosure, and per-card evidence-location disclosures from the normal reading flow. Replace them with one short, plain-language **Basis and important limitations** disclosure at the end of the detailed analysis. It should communicate only limitations that affect interpretation, not application metadata or evidence mechanics.

The structured evidence and reproducibility data remain in application state for validation and assistant grounding; this is a presentation change, not a weakening of internal traceability.

## 3. Word download

The Word note mirrors the cleaner reader-facing detailed analysis:

- concise RRA and FCV Strategy synthesis;
- consolidated RRA and Strategy assessment fields;
- complete priority recommendations; and
- the standard advisory caveat.

Remove the evidence-status paragraph, detailed document-coverage section, evidence register, traceability material, and reproducibility metadata from the exported note. Material analytical qualifications should appear in the relevant RRA/current-context prose rather than in a technical appendix.

This change should be limited to existing export helper calls and headings. It does not require a new Word template or document-generation system.

## 4. Full-document RRA coverage

### Problem

Optional PDFs currently attempt a deterministic 16-page sample across the full page range. In the Guinea run, 16 pages were attempted and 15 yielded extractable text. This was materially better than reading only the opening pages, but it could not support confident absence findings across a 102-page RRA.

### Design

When source identification recognizes an uploaded RRA or accepted equivalent diagnostic:

1. Extract text from every PDF page with its real page number.
2. Treat pages without extractable text as explicit extraction warnings.
3. Send the full page-labelled diagnostic once through the repository's existing but currently unwired `diagnostic_map` model stage.
4. Return a bounded structured map covering principal drivers and trajectory-shifting priorities, delivery risks, contextual conditions, and resilience opportunities. Each entry retains the page evidence identifiers that support it.
5. Build the final review evidence pack from the diagnostic map and the referenced page excerpts. The final review call receives the concise map and relevant extracts rather than the full RRA a second time.

This is a simple two-stage use of the existing architecture: full-document mapping, then CPF review. It does not require embeddings, a vector store, semantic indexing, or a general document-retrieval service.

### Limits and fail-safe behavior

Apply explicit extraction and context-size bounds suitable for the configured model. If the complete extracted diagnostic cannot fit safely within the mapping request, the run must not silently fall back to partial sampling and claim RRA alignment. It should stop with a clear, safe message requesting a text-searchable or shorter diagnostic version, or downgrade to limited framing only if the user explicitly proceeds without full RRA assessment.

The coverage note should distinguish:

- pages attempted;
- pages with extractable text; and
- whether the full extracted diagnostic completed the mapping stage.

Absence conclusions are permitted only after complete extracted-text coverage. Image-only content remains a disclosed limitation.

Non-RRA optional documents can retain the existing bounded selection behavior; this change is targeted to the diagnostic whose full coverage materially affects the central judgment.

## 5. Current-country public research

Keep the existing sufficiency rules: at least four accepted claims, at least two publishers, coverage of structural dynamics and current developments, and evidence within the applicable date window.

Make two narrow improvements:

1. Retry instructions should explicitly seek missing non-economic themes relevant to the mapped RRA, rather than returning more evidence on an already-covered economic theme.
2. User-facing limitations must distinguish claims, unique sources, and thematic coverage. For example: `Two recent claims from two institutional sources were established, both concerning economic trends. Current evidence on conflict and institutional dynamics remains insufficient.`

When the threshold is not met but credible current material exists, retain the reduced-evidence route. The review may use established claims narrowly but must not imply that wider current dynamics were validated.

## 6. Persistent follow-on assistant

### User experience

Replace the prominent correction/rerun section with a Project Screener-aligned follow-on card headed **What would you like to do next?** Suggested actions should include:

- Draft a peer-review email
- Expand a priority measure
- Clarify the assessment
- Summarise for management

Selecting a suggestion prefills the input; it does not immediately incur a model call. The user can edit the request and send it. Responses stream into a conversation beneath the input. Earlier exchanges are restored when the same review is reopened or the browser refreshes.

Keep **Correct source information and rerun** as a smaller secondary action. It opens the existing correction workflow so analytical reruns remain distinct from conversational follow-up.

### Context and behavior

Each assistant request receives:

- the completed structured review;
- the relevant evidence excerpts and page/source locators;
- the current conversation history; and
- a concise system prompt defining the assistant as an FCV review follow-on tool.

The prompt should support iterative drafting, clarification, recommendation expansion, and explanation while preserving the prototype's advisory and public-information boundaries. It must not invent evidence, convert the review into a clearance decision, or make policy/eligibility determinations.

### Persistence and bounds

Store completed user/assistant exchanges with the existing assessment payload in the existing SQLite or volatile session store. No new database or identity layer is required.

- History shares the review's existing 24-hour sliding retention.
- Retain at most 20 messages, matching the bounded Project Screener pattern.
- Apply message-length limits and reject empty or oversized requests.
- Save only completed assistant responses; interrupted partial streams are not added to history.
- Disable concurrent sends in the interface and reject assistant requests for reviews that are incomplete, expired, or failed.

A small `GET` endpoint returns conversation history and a streaming `POST` endpoint generates the next response. Keep assistant history outside the `ReviewResult` schema so export and analytical validation remain unchanged.

## 7. Error handling and privacy

- An assistant failure leaves the completed review intact and displays a retryable inline message.
- RRA mapping failures fail safely and never produce an unqualified sampled-RRA assessment.
- No raw model response, live assessment identifier, uploaded document, or assistant conversation is committed or written to validation documentation.
- Resetting a review deletes its conversation through the existing session-lineage deletion behavior.
- The public prototype continues to accept only approved public or otherwise non-sensitive material.

## 8. Verification and acceptance

Follow the repository's API-cost ladder.

### Provider-free verification

- Contract tests for the concise FCV Strategy synthesis.
- Full-page extraction and diagnostic-map wiring tests, including a blank/image-only page and an over-limit fail-safe case.
- Regression proving a mapped deep-page RRA issue can reach the final evidence pack.
- Research limitation tests distinguishing claims, sources, and missing themes.
- Frontend tests for ordering, prose panels, priority links, consolidated detailed rows, removed disclosures, assistant restoration, and secondary correction action.
- Assistant route tests for history persistence, 20-message bounding, input limits, incomplete/expired reviews, streaming failure, and successful completed-turn storage.
- DOCX structural tests confirming the reader-facing sections remain and the technical appendix/coverage material is absent.
- Local smoke-browser screenshots at desktop and mobile widths.

### One quality run

After local checks, provider-free smoke, deployment verification, and confirmation of the exact live commit, run Guinea once using the public CPF and full RRA. Verify:

- every RRA page was attempted and all extractable pages entered the diagnostic mapping stage;
- the RRA map and final output retain accurate deep-page references;
- RRA/Strategy readouts and priority cards have the approved hierarchy;
- two successive assistant requests demonstrate retained context, including after refresh;
- the streamlined DOCX downloads successfully; and
- full-page screenshots and the DOCX are saved under unique dated filenames.

Do not run additional paid country assessments unless a deployed fix changes model-facing behavior and the user authorizes another quality run under the repository protocol.

## 9. Implementation boundaries

Organize implementation into three bounded batches:

1. results presentation and Word simplification;
2. full-RRA mapping and research wording; and
3. persistent follow-on assistant.

The batches may be planned and tested independently, but final acceptance requires their integrated Guinea result. Do not modify the stable FCV Project Screener, add dependencies without necessity, change unrelated review logic, or redesign the existing results shell.
