# Full Niger CPF plus RRA retest - 6 October 2026

## Scope and release

After the owner explicitly authorized one full retest, one provider-backed review
was submitted on the public Render application using the same Niger CPF and the
June 2022 Niger RRA. Form settings were verified before submission: **early drafting**
and **in-depth**. Existing document-use approval remained in force. No second
assessment was submitted and no application code or hosting settings changed.

TLS-verified health before and after the run confirmed application commit
`99cba0835421dd845c10725475c1a2eb23846436`, the merged referral repair in
[PR 48](https://github.com/ljonestz/cpf-fcv-reviewer/pull/48).
This is separate from the earlier failed RRA trial on `c525c9e`; its
[failure record](2026-10-06-niger-rra-release-test.md) remains unchanged.

## Assessment outcome

The assessment **completed successfully**. The terminal event was `run_complete`
with one bounded repair. The initial validation issue was
`unknown_assessment_evidence`; neither `unknown_institutional_referral` nor
`limited_mode_overclaim` appeared in this run. This real trial therefore establishes
successful completion after the release, while the targeted synthetic regressions
remain the direct evidence for removal of unknown referral IDs.

Application-owned result metadata and coverage confirmed:

- `review_stage=early_drafting`, `detail_level=in_depth`,
  `diagnostic_mode=rra_alignment`: no limited-mode fallback.
- June 2022 diagnostic provenance, supported by the document cover. The internal
  normalized date represents the publication month, not a known publication day.
- **81 pages attempted, 81 pages with extractable text; thematic diagnostic synthesis
  complete**. Representative citations are not a count of pages read.
- Two synthesized RRA assessment rows, all four FCV Strategy assessment areas,
  three priorities and three corresponding summary revisions.
- Forty document-fact evidence items, eight registry-language items and three
  current-context items. Current sources represented two publisher labels and had
  no established publication dates. The result correctly records **reduced**
  current-context evidence; this is not a full current-context acceptance claim.
- Result schema, reproducibility-field validation, export evidence completeness
  and referral membership in the exact hash-verified approved registry passed.
  The final structured referral list was empty.

Accepted result data was inspected in memory. Raw input documents, extracted text,
accepted/rejected model output, conversations and live review identifiers are not
included in this record or committed.

## Browser and export checks

The visible Edge runner reached `BROWSER_CHECKS_PASS` after checking:

- Summary and detailed result panels, with visible screenshots inspected.
- One management-summary assistant response and restoration of both conversation
  messages after refresh, without creating another assessment.
- Both Word download actions and valid DOCX ZIP structures. Additional content
  checks confirmed Niger, June 2022 provenance and the language-model caution.
  The detailed note had 66 paragraphs / approximately 3,025 words; the readout
  had 24 paragraphs / approximately 1,418 words. Its references to 2025 concerned
  a later governance development, not an incorrect RRA publication date.
- Mobile summary layout with no horizontal overflow; its screenshot was inspected.
- No JavaScript page errors or unexpected console errors. The only permitted
  exception was an explicitly identified missing `favicon.ico` response.

Eight PNG captures and both Word files remain in the ignored local folder
`output/playwright/20261006-niger-rra-quality-2`. The session handoff was saved
outside the repository immediately after submission. The runner then remained in
Edge shutdown for several minutes; only the identity-verified QA Python process
was stopped after all assertions and downloads had finished. The final post-close
`BROWSER_QA_PASS` marker and a normal runner exit were not obtained. This local
shutdown issue is separate from the successful server assessment and completed
browser checks; no additional review was submitted.

## Remaining limits and follow-up

This is one successful real assessment, not a guarantee of every future model
response. Expert review remains necessary, particularly because the retrieved
current-context sources were undated and unverified. Full RRA extraction and
successful technical completion do not establish exhaustive thematic or factual
correctness of the assessment.

A pre-existing observability limitation was found: `build_run_metadata` hardcodes
`app_release="0.1.0"`, while `/health` reports the actual Render commit. The exact
deployment was verified independently; the result's generic version label should
not be used to diagnose an old branch. This was documented without adding a new
application change to the retest. The restored assistant response is readable but
renders its Markdown markers as plain text, which is a separate presentation issue.

The public pilot's volatile 24-hour session storage remains unchanged. No message
was sent to ITS. The fixes are shared application behavior, with no Niger-specific
condition; see the [limited-mode record](2026-10-06-limited-mode-review-fix.md) and
[referral-repair record](2026-10-06-registry-referral-repair.md).
