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

## Approved full-width running-banner follow-up

The user's manual full-width example remained structurally simple, with native header
paragraphs and no floating objects. Its zero header offset clipped alternate rendered
pages, so the reusable implementation adopts the same visual direction with one shaded
paragraph, negative one-inch horizontal indents, a one-inch first-line indent, and a
stable quarter-inch header offset. Existing body text and one-inch margins are unchanged.

Native Word rendered both final examples at 3 and 9 pages. The banner was visually
inspected on every page and remains clear of the body. Structural checks confirm no
shapes, pictures, tables, text boxes, or anchored objects in either header; body text is
identical to the prior approved reports. All 39 focused export/parity tests and exporter
Ruff checks passed. New files are under `output/20260908_word_full_width/` and preserve
the earlier proposals. PR28 deployed the final implementation as `72743f5`; `/health`
confirmed the exact release. No model calls were made.
