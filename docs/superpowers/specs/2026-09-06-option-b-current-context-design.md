# Design spec — Option B: current-context as trusted synthesis (soft-flagged, non-fatal)

Date: 2026-09-06
Repo: `cpf-fcv-reviewer`
Branch: `feat/option-b-current-context` (off `origin/main` @ `fc544a7`, source-identical to production `bf1f14b`)
Status: implemented and verified in production on 2026-09-07. The citation-risk
tradeoff was approved on 2026-09-06; release `63b16da` completed the Guinea acceptance
with the bounded fallback, explicit limitation, and non-fatal thin-news behavior.

## 1. Purpose and the one deliberate philosophy change

The current-context (live-news) pipeline now works end to end: it searches trusted
domains, returns ~20 dated sources, and Claude produces a fluent cited synthesis of
current FCV conditions. The app then runs that synthesis through a strict
machine-verification gauntlet (publisher allowlist, exact publication date, exact
verbatim-quote substring match, country match, per-priority-area substantive-support
check) and **deletes** anything that does not pass. When too little survives, the whole
run fails (`missing_current_context_support` → repair cannot fabricate evidence →
`review_failed`). The useful, current, trusted-source answer a normal Claude/ChatGPT query
would give is shredded, and the user often gets nothing.

Option B makes the current-context section behave like a good, trusted-source-guided
manual LLM query: keep the cited synthesis, present it under a clear "verify before use"
label, turn per-claim verification checks into **confidence flags instead of deletions**,
and **degrade gracefully so a review never fails solely because current-context claims
were not machine-verified**.

**This is a deliberate, scoped change to the app's fail-closed philosophy for the
current-context section only.** Every other surface (uploaded-document analysis vs FCV
frameworks, registry language, schema validation, prohibited-policy language, stage
behaviour) stays fully fail-closed. The accepted tradeoff: the app will surface
unverified-but-trusted current-context in a WBG advisory (non-policy-determining)
deliverable, relying on visible labelling rather than deletion.

## 2. Approved product decisions (2026-09-06)

1. **Trust model — inline + per-claim confidence flags.** One current-context section with
   a top-level banner "AI-generated from trusted sources — verify before use"; each claim
   carries a ✅ verified / ⚠ partially verified / ❓ unverified chip.
2. **Influence scope — tiered.** verified → full influence (may drive rating and a priority
   recommendation); partially verified → supporting only (may corroborate, never the sole
   basis); unverified → context-only (narrative framing, never a rating change or a
   recommendation on its own).
3. **Degradation — non-fatal soft-flag, keep claim.** `missing_current_context_support`
   leaves the fatal path; the model's current-context prose is kept, flagged, and the run
   reaches `run_complete`.
4. **Search — add query disambiguation** for ambiguous country names (e.g. Guinea vs
   Guinea-Bissau).

## 3. Chosen approach

**Grade at the boundary.** Add a `verification` grade to each claim where the checks
already run (`public_research.py`), carry it through evidence → validator → export, and
make the downstream `missing_current_context_support` check advisory instead of fatal.

Rejected alternatives: (B) post-hoc reclassification — keep deleting and re-surface rejects
from a side bucket at render; creates a parallel path that can diverge from the grading
logic. (C) validator-only relaxation — just stop failing without a real confidence model;
cannot deliver the per-claim flags (decision 1) or tiered influence (decision 2).

## 4. Confidence model

A claim must first clear a **hard floor** (unchanged — still dropped entirely):

- permitted public institutional / allowlisted publisher (`_is_permitted_public_source`),
  public http(s) URL, not licensed / social-media / blog / forum / wikipedia
  (`retain_public_claims`, `_is_disallowed_source_material`);
- after Q4 neighbour-disambiguation, the source is actually about the selected country
  (`_source_mentions_country`). A source about Guinea-Bissau *alone* stays dropped — that is
  wrong context, not "unverified Guinea".

Claims that clear the floor are **graded, not deleted**:

| Grade | Criteria (existing checks) | Influence |
|---|---|---|
| ✅ `verified` | resolved publication date **within** the 24-month window **and** `_quote_is_from_source` exact-substring match | full (rating + priority) |
| ⚠ `partially_verified` | floor + country match, but exactly one soft failure: no resolved exact date **or** quote not a verbatim substring | supporting only, never sole basis |
| ❓ `unverified` | floor + country match, weak grounding: no date **and** no exact quote match | context-only narrative |

`research_controller` tier selection counts `verified` (and `partially_verified`, as
supporting) toward the FULL / REDUCED evidence tiers; **`unverified` never elevates the
tier**, so tier semantics stay honest.

## 5. Components and data flow

### 5.1 `public_research.py` — grade instead of drop
- Add `verification: Literal["verified", "partially_verified", "unverified"]` to
  `CurrentContextClaim`.
- `_validate_normalized_claims` (~`:1318`) and `_salvage_grounded_segments` (~`:1358`):
  replace the soft-check `continue`/skip on missing date / non-exact quote with a grade
  assignment that keeps the claim. Floor failures (source permission, country match after
  disambiguation) still drop.
- `retain_public_claims` keeps its floor role (duplicate id, licensed, non-public URL,
  non-permitted source) — it does not grade.
- Helper `_grade_claim(source, quote, ...) -> verification` centralises the mapping in §4 so
  the boundary and any salvage path grade identically.

### 5.2 `research_controller.py` — tier honesty + disambiguation
- `_qualifying_claims` / tier selection: only `verified` (+ `partially_verified` as
  supporting) count toward FULL/REDUCED; `unverified` claims are carried through as
  context-only and never raise the tier. `DOCUMENT_LED` remains the floor when nothing
  clears grading.
- `_prompt` (~`:630`) / the search system prompt in `public_research._web_search_create`
  (~`:788`): inject an ambiguous-name qualifier for known collisions (e.g.
  `Guinea (Conakry) — not Guinea-Bissau, not Equatorial Guinea, not Papua New Guinea`) from
  a small `AMBIGUOUS_COUNTRY_QUALIFIERS` map keyed on the canonical name.

### 5.3 `contracts.py` / `runtime.py` — thread the grade through evidence
- `EvidenceItem` (current-context) surfaces `verification`.
- `runtime.build_uploaded_evidence` (~`:982`) copies the claim grade onto the
  `current_context` `EvidenceItem`.
- `ReviewResult` current-context rendering path exposes `verification` to export.

### 5.4 `validators.py` — advisory, not fatal
- Add `severity: Literal["fatal", "advisory"]` to `ValidationIssue` (default `"fatal"`).
- `_append_current_context_support_issue` emits `missing_current_context_support` with
  `severity="advisory"`. The tiered-influence overclaim (an `unverified`/`partially_verified`
  claim used as the sole basis of a present-day FCV assertion) is also `advisory`.
- All other issues remain `fatal` and unchanged.

### 5.5 `orchestrator.py` — fatal path gates on severity only
- The `validate` step's repair/fail branch (~`:63`) fires only when there is at least one
  `fatal` issue. Advisory issues are surfaced (logged; carried to render as the confidence
  flag and a limitation line) and never cause `run_failed`.
- `review_engine.REPAIRABLE_ISSUE_CODES` and the single-repair budget are unchanged; a
  fatal issue still gets one repair, advisory issues never enter the loop.

### 5.6 Review prompt — enforce tiered influence at generation
- The `review` prompt instructs: current-context evidence carries a verification grade;
  `verified` may support a rating change or a priority recommendation; `partially_verified`
  may corroborate but not be the sole basis; `unverified` may frame narrative only and must
  not, on its own, change a rating or generate a recommendation. Prompt is the primary
  enforcement; the validator advisory is the backstop (flag, never fail).

### 5.7 Rendering / export — banner + chips (decision 1)
- `export_docx.py` and `static/app.js`: the current-context section gains the top banner
  "AI-generated from trusted sources — verify before use" and a per-claim ✅/⚠/❓ chip driven
  by `verification`. HTML and DOCX stay at parity (existing scope-parity requirement).

## 6. Scope guard

Only the current-context path changes. Untouched and still fully fail-closed: uploaded
primary/package/context document extraction and analysis, RRA driver and FCV Strategy
assessment against frameworks, registry-language support, schema validation and the single
schema retry, prohibited-policy-language checks, stage-behaviour limits, unknown-evidence /
unknown-referral checks, reproducibility metadata. `severity` defaults to `fatal`, so every
issue except the two named current-context ones behaves exactly as today.

## 7. Testing and acceptance

All provider-free (clear inherited `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE`
first; `python -m pytest -q`). New / updated unit tests:

- `public_research`: `_grade_claim` returns each of the three grades for representative
  inputs; floor failures still drop; a verbatim-quote+dated source grades `verified`; a
  dated source with a paraphrased quote grades `partially_verified`; an undated,
  non-substring source that clears the floor grades `unverified`; a neighbour-only source
  still drops.
- `research_controller`: `unverified` claims do not elevate the tier; `verified` claims can
  reach REDUCED/FULL; disambiguation qualifier appears in the prompt for an ambiguous name
  and is absent for an unambiguous one.
- `validators` / `orchestrator`: `missing_current_context_support` is `advisory`; a result
  whose only issues are advisory reaches `run_complete` (no repair, no `run_failed`); a
  fatal issue still triggers the one repair and fails closed on persistence; a mixed
  fatal+advisory set repairs only the fatal one.
- `contracts` / `runtime`: `verification` round-trips claim → `EvidenceItem` → result.
- export: HTML and DOCX render the banner and the three chip states.

Acceptance gate: the **paid Guinea CPF+RRA run** (`guineacpf.pdf` + `guinearra.pdf`, local
only). A "good" outcome is `run_complete` with a labelled current-context section that shows
graded claims, and **never** `review_failed` solely for thin/unverified live news. **Each
paid run needs explicit maintainer authorization before it is triggered** (money action);
follow the API-cost ladder in `CLAUDE.md` (targeted tests → provider-free smoke → deployed
health/static → at most one paid run per deployed fix cycle; never rerun unchanged code).

Corporate-proxy note for any local httpx to `*.onrender.com` / `api.anthropic.com`: merge
the WBG root CA (`SSL_CERT_FILE` → `wbg-root-ca-g2-fixed.pem`) with certifi or TLS fails
with `CERTIFICATE_VERIFY_FAILED`. Render logs via the Render MCP (service
`srv-d9tju52jobas73d6jvk0`, workspace `tea-d6de2tsr85hc73bqdi0g`); watch for
`research_provider_exception`, `research_reduced` / `research_document_led`, `run_failed`.

## 8. Risks and tradeoffs

- **Citation risk (accepted).** Unverified-but-trusted current context is now shown. Mitigated
  by the top banner, per-claim ❓ chip, context-only influence for `unverified`, and the
  existing advisory disclaimers. The deliverable remains advisory, not policy-determining.
- **Grading drift.** Boundary and salvage paths must grade identically — centralised in
  `_grade_claim` to prevent divergence.
- **Tier inflation.** Guard against `unverified` claims silently raising the evidence tier by
  excluding them from FULL/REDUCED counting.
- **Severity leakage.** A default of `fatal` and an explicit allowlist of the two advisory
  current-context codes prevents accidentally softening unrelated checks.

## 9. Out of scope (explicitly not this change)

Broader search-provider changes beyond ambiguous-name qualifiers; ReliefWeb approved-name
integration; multi-country / all-country current-FCV; any change to uploaded-document
rigor; persistence / auth / ITS-production controls.
