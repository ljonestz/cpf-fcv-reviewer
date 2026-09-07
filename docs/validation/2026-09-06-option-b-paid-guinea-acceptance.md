# 2026-09-06 — Option B paid Guinea acceptance run (PASS)

This is the first Option B acceptance record and remains historical. The later
`63b16da` release added the model-readout fallback and completed a further Guinea
acceptance with six fallback themes; see `docs/validation/2026-09-07-guinea-acceptance.md`.


Deployed build: `main` @ `4dd0f69` (merge of PR #15, "Option B: current-context as graded
trusted synthesis"), manually deployed to Render service `srv-d9tju52jobas73d6jvk0`
(`cpf-fcv-review-prototype`, free tier, autoDeploy off). `/health` returned 200 with
`release: 4dd0f69…` before the run.

## Result: PASS

One authorized paid run against the deployed Option B build, real Guinea CPF + RRA
(`guineacpf.pdf` + `guinearra.pdf`) via `POST /api/reviews` (`country=Guinea`,
`review_stage=decision_review`, RRA as `context_documents`). Assessment ID retained in the non-repository run folder. Terminal event **`run_complete`** (repair_count 1) in
~413 s; valid **46,394-byte DOCX**; 3 priority areas; 6 limitations.

This is the first time a Guinea CPF+RRA run has reached `run_complete` — the exact
previously-blocking failure (`missing_current_context_support` → `review_failed`) is
resolved on live paid infrastructure.

## Event trail (the acceptance evidence)

- `research` → 20 source candidates, 13 linked excerpts, **`missing_publication_date: 0`**
  (page-age dating holds), **`country_mismatch: 13`** — every linked excerpt was a
  neighbour (Guinea-Bissau) and correctly dropped by the hard country-match floor →
  0 accepted → `research_document_led`. Research degrading to document-led was never the
  bug; it is expected and non-fatal.
- `validate` → **`advisory_notice {issue_count: 2, codes: ["missing_current_context_support"]}`**
  — the two current-context support issues were classified **advisory (non-fatal)** and
  surfaced, not used to fail the run. This is the core Option B behaviour.
- `validate` → `repair_start {codes: ["unknown_institutional_referral"]}` — a *separate,
  genuine fatal* issue was repaired normally (one bounded repair). Fail-closed integrity is
  preserved for real fatal issues.
- `validate` → `render` → **`run_complete {repair_count: 1}`**.

## Result behaviour

- `metadata.current_evidence_tier: document_led`;
  `current_evidence_limitation: "Independent current-country research could not be
  established; review is based primarily on submitted documents."`
- Limitations #1 and #5 honestly frame the current-context gap (present-day political
  transition progress, CNRD transparency, intercommunal dynamics not independently
  verified). This is the labelled, gracefully-degraded thin-current-context path.
- `current_context` evidence items: 0 (all search hits floored on country mismatch), so no
  confidence chips were rendered for this run.

## What this run did and did not exercise

- **Exercised (the primary Option B goal):** non-fatal graceful degradation — a real Guinea
  run completes end-to-end instead of `review_failed`, with an honestly labelled
  document-led current-context section, while a genuine fatal issue still repairs.
- **Not exercised live:** grade-and-keep of partially-verified claims and the per-claim
  confidence chips, because this Guinea search returned only neighbour-country
  (Guinea-Bissau) content, all removed by the country-match floor. The prompt
  disambiguation line did not overcome Guinea/Guinea-Bissau news dominance. The
  grade-and-keep + chip paths are covered by the provider-free suite (1468 passed). A
  country with cleaner search yield, or stronger search-side disambiguation, would exercise
  the chips live — a follow-up, not a blocker.

## Follow-ups (not blocking)

- Consider strengthening search-side disambiguation for Guinea (e.g. biasing the query
  toward "Guinea Conakry" terms, or a light post-filter) so genuine Guinea reporting
  surfaces and the grade-and-keep/chip path is exercised in production. Option B already
  guarantees the run completes regardless.
- Provider-free base carries 4 pre-existing `test_public_research.py` article-metadata /
  streaming failures, unrelated to Option B; left as-is.
- Housekeeping from the prior handover still applies: rotate the previously-exposed
  Anthropic API key and update the Render env var.

Run artifacts (local, not in repo):
`C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\20260906_optionb_paid_run\`
(`events.log`, `result.json`, `guinea_optionb_result.docx`).
