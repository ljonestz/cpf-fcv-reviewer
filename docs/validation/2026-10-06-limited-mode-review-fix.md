# Limited-mode Niger failure: focused hotfix (2026-10-06)

## Diagnosis and scope

ITS reported `early_drafting` stopping with `limited_mode_overclaim`. Render was
serving application release `992c35a` from main; its UI/static code matched current
main. The newer development stack also contained the defect. This is an application
validation/repair issue, not evidence of ITS using a separate old branch.

The supplied Niger CPF is byte-identical to the public World Bank PDF. Actual
extraction completed: 10 pages, 37,880 characters, no extraction warnings. Historical
safe server logs confirm review failures, but omit the rejected wording; the exact
cause of ITS's individual run cannot be proven from those logs.

Provider-free reproductions established two routes to the reported stop: legitimate
abstention wording was classified as an alignment claim, and a corrected assessment
row was replaced by its original overclaim during evidence-preserving normalization.

The hotfix starts from `origin/main`, avoiding the unaccepted production/mAI stack.
It accepts specific explicit abstentions and preserves an authorized wording
correction in the existing row. Genuine alignment claims remain blocking, including
mixed caveat/claim cases. Row identity, evidence, status, confidence and unrelated row
text remain protected. Ambiguous/missing matches cannot authorize correction, and
wording repair cannot add RRA rows without an independently authorized coverage fix.
No provider retry, repair budget, model configuration, UI or hosting setting changes.

## Verification completed before release

- Original implementation failed 16 new regression cases before the fix.
- Independent review found injected-row and mixed pronoun-claim edge cases; their
  regressions failed before correction. Clear abstention suffixes also remain accepted.
- Local full provider-free suite: 1,653 passed, one Windows Gunicorn skip (before the
  final review refinements). Focused refinement suite: 459 passed. Final classifier
  and full-pipeline scenarios: 51 passed.
- Synthetic Edge preflight performed early drafting, file injection, completed result,
  summary/detail, assistant response/restoration, mobile layout and both Word exports.
  All browser assertions passed. The first runner exited successfully; a repeated
  diagnostic attempt passed its assertions but showed delayed local Edge shutdown.
- Candidate CI [37440608682](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37440608682)
  and merged-release CI [37442023537](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37442023537)
  each passed **1,670 tests**, including real Gunicorn.
- PR [46](https://github.com/ljonestz/cpf-fcv-reviewer/pull/46) merged as
  `c525c9e384d00e76782f96fbc601a1ba0fc8c7df`. Render auto-deployment reached live;
  verified HTTPS health returned that exact release. Homepage and app.js/styles.css
  checks passed with certificate verification enabled.

No raw documents, model output, assistant content or live assessment IDs are committed.
Local browser artifacts are ignored under `output/20261006-limited-fix-smoke-*`.

## Live Niger acceptance

Exactly one provider-backed assessment used the supplied public Niger CPF, country
Niger, `review_stage: early_drafting`, standard detail, and no context/RRA upload.
It completed in `limited_framing` mode with `repair_count: 1`. Safe event inspection
returned `repair_start` with one `raw_evidence_id_in_narrative` issue, followed by
`run_complete`; no `repair_failed` or `run_failed`. This live run did not require a
limited-mode row correction; that path is covered by controlled regression tests.

The browser exercised summary/detail, one management-summary assistant response,
refresh restoration of both conversation messages, mobile layout and both DOCX
exports. Eight full-page PNGs and two Word files are saved locally under
`output/20261006-niger-hotfix-quality-1/`. PNGs were inspected. Both Word archives
are valid and contain Niger and the explicit RRA abstention.

The strict runner exited nonzero at its final console check for one 404 resource
message. It had completed the functional/result/export assertions. `/favicon.ico`
is independently confirmed 404, consistent with the earlier no-cost browser check;
the original runner did not record the resource URL, so the attribution is an
inference. A subsequent read-only existing-session restoration/refresh check passed
with zero page errors and zero console errors. It blocked non-GET API calls and
created no assessment/model request. Its full-page PNGs are under
`output/20261006-niger-restoration-check-1/`. Local Edge shutdown was slow during
smoke runs; both smoke runners ultimately returned `BROWSER_QA_PASS` and exit 0.

## Practical limits and handoff

Current-context evidence in this trial was `reduced`, and the result discloses its
basis. Technical completion does not establish blanket factual or operational
acceptance. Existing supervised expert-use and volatile-session limits remain.
The phrase guard intentionally recognizes bounded explicit constructions, rather
than providing general natural-language inference. An unresolved genuine claim
still stops after bounded repair; the fix adds no retries or model calls.

ITS should start a new review on the updated Render application. A failed historical
session is not resumed. The exact wording that caused ITS's original stop cannot be
recovered from sanitized historical logs. Newer unmerged production/mAI branches
also contained the original bug and must incorporate this main hotfix before their
own acceptance or handoff; they were not deployed for this repair.

Live assessment identifiers remain only in a temporary non-repository handoff.
No documents, model output, assistant conversations, or live IDs are committed.
