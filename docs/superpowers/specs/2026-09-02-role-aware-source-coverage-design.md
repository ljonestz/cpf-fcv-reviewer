# Role-aware source coverage redesign

Date: 2026-09-02
Status: approved in conversation; written review pending

## Purpose

Replace brittle exact-once RRA page mapping with role-aware source coverage. The
review must give attention in this order:

1. the primary CPF/CEN;
2. accompanying CPF package documents; and
3. the RRA and other contextual inputs.

The primary document remains the principal analytical lens. Accompanying package
documents must be examined in detail for strengths, gaps, implementation choices,
results, and risks. The RRA and other contextual inputs provide higher-level thematic
interpretation.

This design changes source preparation only. It does not redesign results, the
persistent assistant, correction/rerun, or the stable FCV Project Screener.

## Diagnosis

The current diagnostic stage asks the model to group a full RRA thematically while
also reproducing every authoritative page ID exactly once. Three deployed corrections
changed schema retry, coverage retry, prompt wording, and scaffold shape without moving
that bookkeeping responsibility out of the model. A schema-valid Guinea map and its
full-map retry both still failed exact-once coverage.

Exact page assignment is not an analytical requirement. The RRA needs to establish the
main FCV drivers, resilience factors, delivery risks, contextual conditions, and
trajectory-shifting priorities with representative citations. Requiring every page to
belong to one and only one theme is artificial: one page may support several themes,
while other pages may be background material.

The existing package path has the opposite problem. Optional PDFs are sampled at 16
pages, and the evidence pack retains only 16-32 package segments overall, with a minimum
of three per document. That is insufficient when as many as ten accompanying documents
must support detailed gap and strength findings.

## Design principles

- Application code owns document roles, ordering, identifiers, provenance, extraction
  bounds, and input-completeness accounting.
- The model owns synthesis and analytical judgment, not mechanical source accounting.
- Full package processing means every extractable package segment reaches the final
  review payload within explicit bounds; it does not mean every segment must be cited.
- Full RRA extraction means every extractable page is available to the thematic map
  call within explicit bounds; it does not require every page ID in the map output.
- No source is silently sampled or omitted where the role requires full processing.
- Reuse the existing extraction, evidence-pack, gateway, review, validation, persistence,
  and rendering paths. Add no vector database, retrieval service, batch summarizer,
  dependency, framework, or additional provider stage.

## Role-specific source handling

### Primary CPF/CEN

Keep the current bounded, distributed high-level evidence selection and the existing
review prompt rule that makes the primary document the principal lens. The final review
must prioritize the CPF/CEN's strategic pillars, implementation choices, results logic,
risks, and material FCV-sensitive choices.

The primary document remains required and fails closed when unreadable. This redesign
does not introduce page-level primary-document mapping.

### Accompanying CPF package documents

Treat the `package_documents` upload role separately from contextual uploads.
A recognized RRA is handled by the RRA path even when it was uploaded in the package
field; it is not also counted as detailed package evidence.

- Accept at most 10 package documents.
- Fully extract readable PDF, DOCX, TXT, and Markdown package documents. Package PDFs
  must not use the optional 16-page sampling path.
- Preserve every extractable segment's document title, true page where available,
  heading, structural element, and full segment text. Do not truncate package segments
  to 1,600 characters before the review call.
- Generate stable evidence IDs from application-owned document and segment positions so
  duplicate filenames cannot collide.
- Include every extracted package segment exactly once in the final evidence pack and
  serialized review payload.
- Enforce aggregate limits of 400 extractable segments and 300,000 extracted characters
  across package documents, in addition to the existing 40 MB request limit and existing
  per-document extraction safety limits.
- Check the complete serialized review request against a 160,000 estimated-input-token
  ceiling before calling the model. This check covers the primary, package, RRA synthesis,
  contextual evidence, registry evidence, metadata, profiles, and user guidance together.

If a supplied package document is unsupported, unreadable, or would exceed a per-file,
aggregate, or serialized-request bound, stop before review with a safe
`package_coverage_unavailable` error. Do not silently exclude, truncate, or sample it.

### RRA and supporting analytics

Retain the current identification and full re-extraction of a recognized RRA or accepted
equivalent diagnostic. Preserve the existing 250-page, 600,000-character, 50 MB
uncompressed, and 160,000 estimated-input-token diagnostic bounds. Never fall back to
the optional PDF sample for a recognized RRA.

The diagnostic-map response remains bounded to at most 20 thematic entries and should
normally contain 8-12. Each entry retains the existing six fields and cites one or more
representative known RRA evidence IDs. Validation requires:

- unique diagnostic entry IDs;
- at least one source evidence ID per entry;
- every cited ID to be an authoritative extracted RRA ID; and
- no duplicate source ID within one entry.

The same known RRA page may support more than one theme. Uncited RRA pages are permitted.
Only cited RRA excerpts are added to the final evidence pack. The application records
pages attempted, pages with extractable text, and successful thematic synthesis; it does
not claim exact page mapping.

Remove the coverage-retry diagnostics and scaffold. Keep the initial map call and at most
one sanitized schema retry. A second schema-invalid response, an unknown citation, an
entry without usable evidence, or an over-budget full RRA fails closed as
`diagnostic_coverage_unavailable`. A third map call is forbidden.

Other contextual documents retain bounded, disclosed selection and remain secondary to
the primary and package evidence.

## Final review data flow

1. Extract the primary document.
2. Preflight optional uploads sufficiently to identify a recognized RRA.
3. Re-extract the recognized RRA in full.
4. Extract all non-RRA package documents in full under package limits.
5. Build the evidence pack in priority order: primary evidence, all package evidence,
   RRA thematic entries and cited excerpts, current-country and other bounded contextual
   evidence, then registry material.
6. Validate package completeness and the full serialized request budget.
7. Run the existing final review and validation/rendering path.

The review prompt must state that package evidence is detailed and complete within the
declared readable-text bounds, while RRA and other context are thematic supporting lenses.
Structured evidence and locators remain internal and available to validation and the
follow-on assistant even though technical registers remain absent from reader-facing HTML
and DOCX.

## Failure and disclosure behavior

- Package coverage failures stop the review before model drafting and identify only a
  safe error category to the client and logs.
- A recognized RRA that cannot be fully extracted or thematically synthesized fails
  closed without sampling.
- Blank or image-only pages remain explicit extraction limitations and are not treated as
  extractable evidence.
- Context-document sampling remains disclosed and cannot support an unqualified absence
  conclusion.
- Full package readable-text coverage can support gap and strength findings, subject to
  disclosed image-only, unsupported-format, and extraction limitations.
- No uploaded text, raw model output, filenames, evidence excerpts, or identifiers are
  added to safe operational error logs.

## Testing and acceptance

Implementation must use TDD and cover at least:

- ten package documents with every extractable segment present exactly once in the review
  payload;
- a long package PDF with material late-page content and no 16-page sampling;
- duplicate filenames with collision-free evidence IDs and correct locators;
- package document-count, segment, character, extraction, and complete serialized-request
  bounds failing before the review call;
- unreadable package input failing rather than being silently excluded;
- no package uploads preserving current primary/context behavior;
- a 102-page RRA with one blank page producing a valid thematic map with a small set of
  representative citations and no exact-once requirement;
- overlapping known RRA citations across themes succeeding;
- empty, duplicate-within-entry, and unknown RRA citations failing safely;
- one schema retry at most and no coverage retry or third map call;
- cited deep-page RRA provenance retained in the evidence pack;
- prompt-injection boundaries for all uploaded text and model diagnostics;
- unchanged results, assistant persistence/streaming, correction/rerun, HTML, and DOCX
  behavior; and
- targeted tests, provider-free smoke, complete local tests, compilation, JavaScript
  syntax, static diff checks, browser QA, and DOCX structural/render inspection where the
  environment permits.

No deployment or paid country-quality run may occur until all provider-free gates pass,
the integrated diff is inspected directly, and separate approval is obtained. Any later
deployed fix cycle may run at most one Guinea assessment and must not rerun unchanged code.
