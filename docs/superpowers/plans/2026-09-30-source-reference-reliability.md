# Source reference reliability follow-up

> Execute inline with test-first checkpoints; delegate only read-only mechanical work.

**Goal:** Reduce the observed reference failures and add enforceable protection against
unsupported numerical recommendations, without claiming automatic factual acceptance.

**Approved design:** Continue the existing repair branch and reuse priority `evidence_ids`.
Resolve a locator from an exact passage only when its cited primary/package records
identify an unambiguous source; copy the real coordinates and source wording locally.
Never search uncited documents to rescue a generated reference. Reject unsupported
paraphrases, empty normalized quotations, partial-word matches and ambiguous relocation.
Keep source-grounding failures fatal and preserve priority coverage during repair.

**Owner-approved addition:** Make each RRA row's `cpf_response` a literal quotation
from its cited primary/package evidence. Keep delivery and results interpretation in
the existing analytical fields, visible separately in the browser and Word export.
For `not_evidenced` or `not_assessable` rows, allow only the fixed absence disclosure
when no verified quotation exists; never invent a quotation to fill the column.
Normalize verified wording from the source and reject unsupported narrative responses.
The existing bounded repair may correct an invalid response and its known source links,
while preserving valid rows, identities, standing and unrelated analysis. No new schema
field, model call, provider allowance or hosting cost is introduced.

**Stack:** Existing Python/Pydantic application and pytest; standard-library matching.
No new dependency, model call, admission, output-token ceiling or hosting change.

## Work and acceptance

- [x] Add failing regressions in `tests/test_source_grounding.py` for cited-ID scope,
  paraphrase bypass, punctuation-only/partial-word excerpts and safe reason categories.
  Add `tests/test_reference_resolution.py` for exact source copying, unique cited-source
  resolution, preserved ambiguity, and both initial review and repair integration.
- [x] Implement the shared matcher in `src/cpf_fcv_reviewer/source_grounding.py`.
  Use it in `validators.py` and `review_engine.py`; preserve the public result contract.
- [x] Carry only allowlisted locator reason/count aggregates through `runtime.py` and
  `orchestrator.py`. Add red/green event tests proving no messages, IDs or rejected values
  enter public failure events. Preserve the existing bounded repair-call behavior.
- [x] Add a narrow source-backed percentage recommendation guard and regressions for
  the observed invented numerical triggers. It checks stated values, not semantic
  entailment: matching a number never establishes the underlying recommendation's truth.
  Supply source text/roles needed by the existing repair rather than making new calls.
- [x] Update versioned review/repair prompts to require cited exact anchors and separate
  CPF commitments, contextual government acts, dated events and proposed measures.
  Do not represent prompt instructions as a deterministic factual verifier.
- [x] Add red/green quoted-response regressions for primary/package ownership, cited-ID
  scope, source copying, absence disclosures, repair preservation and browser/Word parity.
- [x] Run focused provider-free tests, then the existing smoke/runtime checks and full
  Linux CI. Inspect the actual diff and inspect real source-anchor regression results.
  Preserve the earlier four-attempt ledger and safe-failure records unchanged.
- [x] Check an installed no-cost Word-rendering path; visually verify new exports if
  available, otherwise record the exact blocker without installing software.
- [x] Commit/push logical checkpoints and update draft PR 39, project status and a new
  dated validation record. Keep known date/actor semantic defects pending fresh source
  acceptance; do not release unvalidated output, merge or deploy.

Run focused checks with the existing venv Python and `-p no:cacheprovider`.
Broaden only after changes pass their direct regressions. Further provider-backed testing
needs a newly established attempt ceiling; durable hosting remains owner-deferred.
