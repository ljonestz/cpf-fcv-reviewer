# Comments fallback acceptance - 13 October 2026

## Result and release state

The owner approved a labelled fallback when the optional comments-drafting step
fails. Application commit 988db71 provides that fallback without another model
call. Its browser, retention and export behavior are verified. The generated
Guinea analysis remains acceptable as a supervised coordinator first draft, as
recorded in the [fresh output review](2026-10-13-final-output-review.md).

PR 55 remains draft and no merge or deployment occurred. Word pagination has not
been visually verified; this record does not claim full production acceptance.
No paid assessment or tailoring query was made during this follow-up.

## Fallback behavior

The draft uses the validated priority headings, rationale and recommended actions
in their existing order. These passages are copied intact, including qualifications;
the application adds only a short opening and unsigned closing. The browser and
Word comments export explain that the draft was assembled because comments drafting
was unavailable. The existing Copy control, automatic retention and prose query
remain the only drafting workflow.

Saved coordinator wording takes precedence. A copied, unchanged fallback retains
its label; replacement wording removes the fallback label. The underlying assessment
and original safe failure diagnostic remain unchanged. Empty or oversized fallback
content is not silently truncated. This mitigates the earlier blank-draft failure;
it does not recover the discarded rejection reason or add automatic model retries.

## Verification

- 95 focused tests plus one text-budget edge test passed. Targeted Ruff and
  git diff --check passed.
- Exact application-head Linux CI passed all 1,813 provider-free tests, including
  Gunicorn concurrency: [CI run](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/38401362873).
- A synthetic Edge flow deliberately failed only comments synthesis, then verified
  a labelled nonempty fallback, refresh restoration, comments Word export and saved
  replacement wording. Both resulting screenshots were visually inspected.
- A read-only preview from the retained real Guinea assessment produced a 467-word
  fallback and retained all four recommended actions. This was not a new assessment
  or a model call; its Word page appearance is unverified.

Ignored browser artifacts:
`output/playwright/20261013-fallback-qa/01-labelled-fallback.png` and
`02-edited-restored.png`. The real fallback preview is
`output/20261013-word-qa/real-fallback-review-comments.docx` (ignored).

## Word pagination check

The previously downloaded summary and detailed notes passed Word package/structure
checks. Native Word automation had failed to render them. This follow-up attempted
the bundled document renderer with an isolated, checksum-verified LibreOffice
package and the existing managed Python/Poppler tools. Administrative and direct
cabinet extraction did not yield a complete runnable renderer within the bounded
attempts. The partial runtime failed both PDF conversion and the renderer's ODT
fallback (exit 0xE06D7363), producing no page images. A final read-only cabinet check
found no duplicate filenames to explain the extraction timeout.

No application export defect or organizational policy cause was established by
these failures. No Office/security settings were changed. Source documents were
not edited, no new application dependency was introduced, and no raw assessment
or live identifier was committed. The renderer log is retained locally at
`output/20261013-word-qa/render-summary-local.log` (ignored).

Word pagination remains a release acceptance gap: inspect the saved summary and
full note in a working native Word or LibreOffice renderer before wider rollout.
The current-country evidence, absent source annexes and single-country validation
limits in the fresh output review also remain. Another paid run is not needed
merely to inspect these saved exports.
