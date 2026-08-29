# CPF FCV Reviewer Pilot Reliability Design

## Purpose

Make the public CPF FCV Reviewer dependable enough for another bounded country-team pilot by fixing verified evidence-coverage false negatives, adding proportionate FCV social-risk and Strategy checks, and bringing the results experience closer to the established FCV Project Screener visual language. Preserve the product's advisory boundary, current five-minute/detailed structure, and public-versus-ITS separation.

## Design principles

- Prefer the smallest repository-consistent change.
- Do not create a new retrieval framework, assessment table, scoring system, or shared dependency with the FCV Project Screener.
- Treat incomplete extraction or sampling as uncertainty, never as evidence of absence.
- Preserve thematic recommendations, HTML/DOCX scope parity, native disclosures, responsive behavior, and accessibility.
- Use real public Guinea and approved Benin/Haiti materials for acceptance, but do not commit source documents or provider output.

## Options considered

### 1. Coverage-aware bounded sampling (selected)

Sample across a PDF rather than reading only its first two pages, guarantee a small minimum contribution from each package document, expose incomplete coverage through existing evidence-pack warnings, and reject confident absence claims when their source coverage is incomplete. Add focused prompt instructions for scattered content and FCV lenses.

This directly addresses the verified causes with a narrow change to existing extraction, selection, prompting, and validation paths.

### 2. Full-document extraction for every upload

This is simpler conceptually but weakens resource bounds and may create large prompts or slow runs. It is not selected.

### 3. New semantic retrieval/indexing layer

Embeddings or a criterion-specific retrieval service could improve recall, but would add dependencies, storage questions, and a new architecture before the current bounded approach has been repaired. It is deferred unless acceptance tests later demonstrate that bounded sampling remains inadequate.

## Evidence coverage design

### PDF extraction

Replace the silent `max_pdf_pages=2` behavior for optional uploads with deterministic page sampling across the full page range. The sample must include the first and last pages and evenly distributed interior pages, preserve original page numbers in locators, and remain bounded by one named constant.

When not every page is extracted, add a standardized, filename-specific warning stating how many pages were sampled from the total. Empty-page warnings remain unchanged. No raw document text is included in the warning.

### Package selection

Retain the existing marker-aware round-robin selector. Calculate its budget from the number of readable package documents so every document can contribute up to the existing minimum of three segments. Apply a conservative overall ceiling to prevent unbounded prompt growth. Each evidence item remains truncated to the current character bound.

Do not introduce a new retrieval service or rewrite the extraction data model. Existing warnings are the model-visible coverage channel.

### Absence guard

Pass a compact set of incomplete document roles from runtime into validation. A `not_evidenced` RRA or Strategy assessment is invalid when the evidence needed for that judgment comes from an incompletely covered role. Return a repairable validation issue instructing the existing single repair pass to use `not_assessable`, or `partially_aligned` when supplied evidence demonstrates relevant but scattered or weakly operationalized content.

Do not add a new public status. Use existing meanings:

- `partially_aligned`: relevant content exists but is scattered, weakly visible, or weakly operationalized;
- `not_evidenced`: adequate source coverage supports an absence conclusion;
- `not_assessable`: coverage is unavailable or inadequate.

The review and repair prompts must tell the model to acknowledge existing content and recommend consolidation or operationalization before recommending new text.

## FCV assessment additions

Add concise prompt requirements to consider, where material and supported:

- conflict sensitivity and Do No Harm;
- inclusion and legitimacy;
- forced displacement and host-community dynamics;
- distributional effects and perceptions of winners and losers;
- natural-resource competition.

These are cross-cutting lenses, not a fifth Strategy shift and not a mandatory new recommendation. They surface only when evidence supports materiality.

For the differentiated approach, require the assessment to discuss the country-context differentiation relevant to the CPF or state that an official classification or commitment judgment is not determinable from CPF-level evidence. Where evidence permits, identify candidate trajectory-shifting actions and describe the observable basis for government commitment or sustainable delivery pathways. Never make an official classification, policy, eligibility, endorsement, or clearance determination.

No new schema field is introduced initially. Prompt and behavioral tests come first; structured support is added only if those tests prove prompt-only handling unreliable.

## Visual and UX alignment

Retain the current Open Sans and navy/blue/cyan tokens, dark hero, upload flow, progress journey, five-minute/detailed tabs, thematic titles, and native collapsible evidence.

Make only these focused changes:

1. Refine the results container into a clearer output card using a subtle top accent, lighter header separation, and consistent inner spacing.
2. Apply one consistent bordered, rounded, lightly shaded summary treatment to evidence, traceability, coverage, and evidence-status disclosures.
3. Add restrained semantic status classes: aligned green, partially aligned amber, not evidenced muted red, and not assessable grey. Text labels remain primary; color is supplementary and must meet contrast requirements.
4. Add targeted `min-width: 0` and wrapping rules for long titles, filenames, locators, and result actions at 390px. Do not hide overflow globally.

Do not copy or import the stable Screener stylesheet, add its branded top bar, redesign uploads, add decorative animation, or introduce any numeric/segmented FCV score.

## Expected files

- `src/cpf_fcv_reviewer/extraction.py`
- `src/cpf_fcv_reviewer/runtime.py`
- `src/cpf_fcv_reviewer/validators.py`
- `src/cpf_fcv_reviewer/review_engine.py`
- `prompts/review.md`
- `prompts/repair.md`
- `src/cpf_fcv_reviewer/static/app.js`
- `src/cpf_fcv_reviewer/static/styles.css`
- focused tests in the existing extraction, runtime, validator, prompt, narrative, frontend, and accessibility test files

`contracts.py`, templates, and DOCX rendering remain unchanged unless a failing test demonstrates a necessary contract or parity change.

## Test-first acceptance

### Deterministic regression tests

1. A long PDF with decisive text after page 2 contributes a correctly numbered deep-page segment or carries an explicit incomplete-coverage warning.
2. Multiple DOCX package files each contribute representative evidence, including later high-value sections.
3. Benin's nine-document package receives at least one meaningful contribution from every readable document and respects the overall ceiling.
4. An incomplete relevant source cannot support `not_evidenced`; validation requests repair to `not_assessable` or a qualified partial finding.
5. Scattered jobs/IFC/MIGA evidence is described as existing but insufficiently integrated, and the recommended direction is consolidation rather than addition.
6. Context-supported social-risk evidence can surface a proportionate priority; unsupported lenses do not generate boilerplate priorities.
7. Strategy wording preserves the advisory boundary and permits `not determinable at CPF level`.
8. Status classes, disclosure panels, tab behavior, focus states, and mobile wrapping pass frontend/accessibility contracts.

### Reference runs

- **Guinea:** public 7-page CPF plus public 102-page RRA. Confirm that the RRA driver-response collection is populated and uses material from beyond page 2, including relevant natural-resource, legitimacy, inclusion, jobs, and conflict evidence where supported.
- **Haiti:** confirm the jobs finding acknowledges existing scattered CPF content and recommends integration rather than implying absence.
- **Benin:** use the RRA and multi-file package as the package-coverage stress test. A real-provider run is required before claiming multi-document/RRA readiness; if credentials are unavailable, report the blocker and do not relabel smoke output.

Save dated JSON, HTML, DOCX, and 1280px/390px screenshots without overwriting prior evidence. Visually inspect every DOCX page when rendering or Word access is available.

## Completion boundary

Run focused tests during each red-green cycle, then the full suite, JavaScript syntax, `git diff --check`, and Ruff if Windows Application Control permits it. Update project status and append a new validation record only after material verification. Confirm the deployed release from the live health endpoint before changing deployment documentation.

The tranche is complete only when deterministic regressions pass, Haiti is corrected, Guinea demonstrates current-prompt RRA use, and Benin either passes a real-provider package run with FCV specialist review or is recorded as the remaining external acceptance blocker.
