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
- Linux CI, deployed commit, and one real Niger validation are pending.

No raw documents, model output, assistant content or live assessment IDs are committed.
Local browser artifacts are ignored under `output/20261006-limited-fix-smoke-*`.
