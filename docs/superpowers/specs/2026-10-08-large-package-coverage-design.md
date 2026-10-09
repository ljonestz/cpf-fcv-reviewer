# Large-package coverage design (2026-10-08)

## Problem

A Guinea run with the CPF as primary, two package documents (BOSIB about 255,000
characters and the PLR about 197,000) and the RRA as context stopped with
`package_coverage_unavailable` after 33 seconds. The cause was the combined package
character budget (300,000), not the document count. The message ("Upload fewer,
shorter, or text-searchable package documents") did not say which limit was hit.

Related findings:

- The review model was `claude-sonnet-4-5` (200k context). Request budgets of
  160,000 estimated tokens were sized for it.
- The primary CPF/CEN reached the review model as 12 evenly spaced segments of at
  most 1,600 characters (about 6 percent of a 105-page CPF), although the project
  rules describe it as the principal lens.
- Non-RRA context analytics reached the model as 16 sampled segments.
- Real CPF packages can exceed ten documents.

## Decision

The user approved this design on 2026-10-08 and accepted a higher cost per run for
better outcomes.

1. **Review model.** Review, repair, diagnostic map, readout and digest calls use
   `ANTHROPIC_REVIEW_MODEL_ID` (default `claude-opus-5-5`, 1M context) at high effort
   with streaming. Public research and the follow-on assistant keep
   `ANTHROPIC_MODEL_ID` until they are migrated and validated separately.
2. **Full primary.** Every extracted primary segment is supplied in full, in order.
3. **Package documents: every page is read by the model.**
   - Direct mode: when the combined package fits the direct budget, every segment is
     supplied in full, as before.
   - Digest mode: otherwise, the largest documents are digested first until the rest
     fit. A digest call reads the whole document and returns a structured summary.
     The model classifies each document as `core` (results frameworks, PLRs, policy
     matrices and other consequential package material) or `background`. Core key
     points cite page evidence IDs, which are validated; background key points may omit
     citations. The review receives one digest evidence item per document plus the
     verbatim text of cited pages.
   - Digested roles are treated as incomplete for absence claims: a reviewer may not
     mark something `not_evidenced` on the basis of a summary.
   - A digest that fails its schema twice excludes that document with a stated
     limitation instead of stopping the run.
4. **Context analytics.** Non-RRA context documents are extracted in full and
   digested as background, replacing the 16-segment sample. The RRA path is unchanged.
5. **Limits.** Up to 40 package documents. Per-document extraction bounds are
   unchanged (250 pages, 600,000 characters). The upload cap rises from 40 MB to
   80 MB; the Render starter plan has 512 MB of memory, so larger caps need a plan
   decision.
6. **Warnings.**
   - On file selection the intake shows document counts and total size, and blocks
     submission above the hard limits.
   - After extraction, a `package_plan` progress event reports how many documents will
     be read in full and how many summarised.
   - Hard failures use specific safe codes: too many package documents, a package
     document too large, a package document unreadable.

## Rule change

Replaces the CLAUDE.md rule that up to ten package documents must be supplied in full
or the run fails closed with: up to 40 package documents are each read in full by the
model and either supplied in full or summarised in a validated digest; the mode is
disclosed in the coverage note and warnings; nothing is silently sampled.

## Validation

Provider-free tests for the planner, digest validation, evidence assembly, failure
codes and frontend contract; the full suite; then one authorized paid local run of the
full Guinea package.
