# Draft review comments: workflow simplification

12 October 2026. Follow-up to the coordinator redesign in draft PR #55.

## Final behaviour

- The output is named **Draft review comments**. Its toolbar has one Copy action.
  Direct wording edits are retained when the field loses focus. Completed query
  revisions are retained automatically and restore after refresh.
- Optional feedback is removed from the UI, contracts and collection endpoint.
- One **What would you like to do next?** input handles tailoring, discussion and
  explicit assessment updates. There are no task dropdowns or assistant branding.
  Three small example links prefill prose requests without sending. The separate
  correction box is removed. The same model response signals answer, tailoring or
  explicit correction, with no extra classifier call. Ambiguous requests ask a
  focused question and leave findings unchanged.
- Tailoring uses the current draft, the validated findings and their evidence,
  including earlier-comment follow-through when available. It does not modify
  findings. Full assessment updates use the existing child-review pipeline and
  preserve older wording with its stale-draft warning.
- Invalid or incomplete revisions leave the previous comments intact. Existing
  policy, signature, stage, evidence-ID and numerical checks apply to refinements.
  Numbered lists do not count as newly invented factual targets.
- The website and Word notes share the adapted **LLMs are not magic** caveat:
  advice can be wrong, must fit country realities and the review stage, and WBG
  policy/procedure references need OPCS and human corroboration.

The Project Screener's `screenerCaveatHtml()` in its local `index.html` was read as
the wording reference. That repository was not edited. No new dependency, provider
configuration or automatic model-classification call was added.

## Prose-query acceptance checks

The latest revision also fixes four concrete findings from independent read-only
review: blank drafts no longer block questions, correction handoff releases the
editor, supported topical refinements can ignore unrelated evidence-pool items
while still requiring every asserted topic/direction to be covered, and a greeting
or introductory sentence cannot hide finalisation overreach. The new regressions
were observed failing before these fixes. Public/current evidence topic checks
remain heuristic; they are not semantic proof of every factual claim.

The exact final browser runner reached `BROWSER_QA_PASS` with no page or console
errors. It checked result, direct edits, prose tailoring, refresh, explicit
correction, stale-draft reconciliation, mobile and both Word exports. All 11 PNGs
and two DOCX artifacts are under `output/playwright/20261012-prose-query-preflight-final/`.
Headless Edge cleanup stalled after app acceptance; a blank-page reproduction
confirmed delayed browser.close() without involving the app. The final runner
therefore supports a Chrome fallback. Both browser channels keep the same flow. The final full provider-free suite passed **1,796 tests**, with one Windows-only
Gunicorn skip. No paid run has been submitted at this checkpoint.

## Earlier verification in this follow-up

New behavioural tests failed before implementation. The full local provider-free
run produced **1,782 passes, one failure and one Windows Gunicorn skip**. The failure
was the former correction-button lifecycle test. Updating it for the shared input
also exposed a stale reset reference to the removed field; that reference was
removed. The subsequent focused lifecycle/refinement/presentation run passed
**28 tests**. Further refinement cases cover invalid cached drafts and evidence IDs.

The synthetic Edge runner passed:

`BROWSER_QA_PASS mode=smoke assistant_messages_restored=2 docx=2 comments_tailored=true`

It checked the one-button comments toolbar, absence of feedback/correction boxes,
suggestion prefilling, comments tailoring and automatic retention, refresh,
assessment updates through the shared input, preservation of edits and stale-draft
handling, mobile overflow and both Word-note downloads. The dedicated visible
Edge session was navigated and restored separately. A favicon 404 in the visible
development session does not affect the application; the smoke runner had no page
or console errors.

Artifacts remain ignored under:
`output/playwright/20261012-review-comments-simplified/`.
Word source paragraphs and exported PDF text confirm both caveat paragraphs and
all analytical sections. PDF page images were inspected. The readout is one page,
the detailed note two pages. Native Word conversion produced the artifacts, but
the helper stalled during shutdown and was stopped after independent artifact
checks. No user document was opened or edited. The earlier packaged-renderer
dependency limitation remains unchanged.

Changed implementation files pass targeted Ruff checks and `git diff --check`.
JavaScript syntax checks pass. Linux CI checks the pushed candidate separately.
Historical validation records describe the first implementation and remain intact.

No paid model call, merge or deployment was performed. Synthetic tests establish
workflow behaviour; real-model tone, condensation and country-specific factual
quality still need an authorized quality test. Internal references/hosting remain
on their separately governed route.
