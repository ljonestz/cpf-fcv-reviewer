# Coordinator candidate: public Guinea quality acceptance

12–13 October 2026. Feature branch `feat/coordinator-review-redesign`, PR #55.

## Outcome and cost

One additional provider-backed assessment was submitted, plus one follow-on request
on that assessment. The owner's authorization caps full assessments at two; the
second was not used. The test used the approved local public Guinea CPF and RRA,
decision-review stage, the existing provider configuration and the approved public
registry. No internal style corpus or policy text was added to the public bundle.
Credentials and live assessment identifiers remain outside Git.

The analysis ran on **9e84d06**, using `claude-opus-5-5`. It completed with four
qualitative findings and four priorities after one existing bounded repair for
`unknown_institutional_referral`. Research was **reduced**; two current-context items
from two publishers were retained. Present political/security status remained
unestablished and the outputs said so. The June 2023 RRA is treated as a dated
baseline, with evidence of authorities' commitment explicitly limited.

The prose request to condense the comments produced a retained, unsigned draft of
**648 words**, down from **1,358**. It focused the comments on three issues while the
underlying four priorities remained unchanged. Material evidence and missing-annex
qualifications were preserved. The note, summary, comments, refresh restoration,
mobile view and both Word downloads were exercised.

## Browser findings and corrections

The exact provider-free runner completed its Edge preflight before paid submission.
Edge cleanup was delayed even in a blank-page reproduction, then completed; this
was separate from application acceptance. Chrome fallback was attempted but stopped
at upload preflight without submitting an assessment. Edge remained the quality channel.

The paid runner's final assertion failed only because of a missing-favicon 404.
All result, tailoring, restoration and download steps had completed. The final
candidate adds a local SVG favicon and corrects a result-header layout in which a
long contextual rationale squeezed the download controls. Sentence casing is now
preserved. These changes affect presentation, not analytical/model behaviour.

A separate **GET-only** browser check restored the retained assessment with all API
writes blocked. It passed with **zero console/page errors**, one Copy comments
control, no query dropdowns, retained comments/history, all three result views and
no mobile overflow. It made **no new model calls**:

`QUALITY_READ_ONLY_RESTORE_PASS no_model_calls=true errors=0 comments_restored=true mobile=true`

Unique, ignored artifacts are under:
`output/playwright/20261012-guinea-quality-run1/`.
Original quality PNGs and both DOCX downloads are retained. Final presentation PNGs
are `20-restored-summary-final-full.png`, `21-restored-detailed-final-full.png`,
`22-restored-review-comments-final-full.png` and `23-restored-mobile-final-full.png`.
The final comments page and earlier synthetic query page were visually inspected.

## Verification and limits

The full local suite passed **1,796 tests**, with one Windows-only Gunicorn skip.
Exact-candidate Linux CI passed **1,797**, including Gunicorn. After the favicon
and header change, **80 focused provider-free tests** passed. JavaScript syntax,
targeted Ruff and diff whitespace checks passed. Final-head CI is recorded by the PR.

Both Word files passed ZIP/OOXML and source-text checks, including the shared LLM
caveat and OPCS reference. The detailed note has 71 native paragraphs, the summary
32, with no tables. Native Word PDF conversion could not start a separate instance
(`server_execution_failed`); no local LibreOffice renderer was found. Full real-run
Word pagination was therefore **not visually verified**. Earlier synthetic Word
layout QA remains historical evidence, not a substitute for this missing check.

One real-country case does not establish universal factual accuracy. The initial
comments were verbose; the tested prose refinement provides effective condensation.
Source coverage remains reduced, and country judgment and stage feasibility still
need coordinator review. Operational ITS hosting, approved internal references and
restart-safe deployment are separate from this code acceptance. The existing public
pilot still uses volatile sessions. No merge or live deployment was performed.
