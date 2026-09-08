# Word export presentation - 2026-09-08

## Change

Both Word exports omit the final basis/limitations section, which remains on the
website and in the review data. A short opening note cautions readers about
language-model findings and exact dates and advises country or FCV expert consultation.

The layout uses navy headings, pale blue paragraph shading and a restrained teal
accent on recommended actions. It retains Letter portrait, one-inch margins,
left-aligned Calibri text, normal paragraph flow and native Word styles. There are
no floating text boxes or fixed-height tiles. A locally supplied Radar document
informed visual styling only; none of its content or branding was copied.

## Validation

- Complete provider-free suite: **1,527 passed**.
- Focused export, end-to-end and output-parity checks: **39 passed**.
- Ruff passed for the exporter and preview script. Existing test-file lint findings
  remain outside this presentation change; no unrelated cleanup was made.
- Existing Guinea exports were restyled locally without rerunning the assessment:
  full report **9 pages**, five-minute readout **3 pages**.
- Native Microsoft Word rendered the files to PDF, with page images inspected for
  layout. The packaged LibreOffice renderer was unavailable, so local Word was used.
- DOCX checks confirm one-inch margins, one section, the revised opening note and
  absence of the limitations section and floating text boxes.
- Existing assessment text is preserved. In particular, the known RRA date error
  remains an analytical follow-up; these are layout proposals, not a new assessment.

## Artifacts and deployment

The two dated DOCX proposals and local render evidence remain untracked under
`output/20260908_word_design/`. The reusable local restyling command is
`scripts/20260908_preview_word_reports.py`; it refuses to overwrite existing files.
No raw documents, model outputs or reference-report content are committed.

The presentation change was merged through PR28 and deployed as `72743f5`. Render
reported the deployment live and `/health` returned the exact release. No paid model
or research calls were made.

## Approved top-edge running-banner follow-up

The user's edited full report established the target: a navy banner touching the top and
both side edges with a 65-pixel rendered depth. Inspection confirmed that the reference
used native shaded header paragraphs and no floating objects. The reusable exporter uses
a simpler structure: one default-header paragraph, negative one-inch horizontal indents,
a one-inch first-line indent, zero header distance, and an exact 42.5-point line height.
Existing body text and one-inch margins are unchanged.

Native Microsoft Word rendered the final examples at 3 and 9 pages. Pixel checks found
the banner at rows 0-64 on every one of the 12 pages, matching the reference exactly.
Every page was inspected in a contact sheet; the banner remained consistent and clear of
the body. Structural checks confirm one default header reference and no separate even-page
header, shapes, pictures, tables, text boxes, or anchored objects. The final files are
under `output/20260908_word_exact_top/`; earlier proposals remain preserved. No model or
research calls were made.
