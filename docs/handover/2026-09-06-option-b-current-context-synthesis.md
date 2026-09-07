# Handover — Option B: current-context as trusted synthesis (not a machine-verified gauntlet)

Date: 2026-09-06
Repo: `cpf-fcv-reviewer`
Production at handover: `main` @ `bf1f14b` (deployed, healthy).

## Superseded status (2026-09-07)

The Option B implementation described here was subsequently merged, deployed, and
verified. The current release is `63b16da`; a full Guinea acceptance reached
`run_complete` with zero independent current-context evidence, a six-theme model-readout
fallback, and a valid DOCX. This handover remains useful as the design rationale and
search-coverage diagnosis. Use `docs/validation/2026-09-07-guinea-acceptance.md` and
`docs/PROJECT_STATUS.md` for the live status and remaining source-coverage limitation.

## Read first
- `CLAUDE.md`, `README.md`, `docs/PROJECT_STATUS.md`
- `docs/validation/2026-09-06-live-news-pipeline-fixes-and-verification.md` (what was fixed and why)

Use brainstorming/spec-first before writing code. Keep diffs narrow. Branch-first; never commit
secrets, assessment identifiers, raw documents, or provider output. This repo is fail-closed **by
design** — Option B is a deliberate change to that philosophy for the current-context section only, so
**get the maintainer's explicit sign-off on the citation-risk tradeoff before shipping.**

## The problem in one paragraph

The plumbing now works: the app searches trusted domains, gets ~20 sources, dates them, and Claude
produces a fluent cited synthesis of current FCV conditions. But the app then runs that synthesis
through a strict **machine-verification gauntlet** (publisher allowlist, exact publication date, exact
verbatim quote substring-match, country match, per-priority-area "substantive support") and **deletes**
anything that doesn't pass; when too little survives it **fails the whole run**
(`missing_current_context_support` → `repair_failed` → `review_failed`). The net effect: the useful,
current, trusted-source answer a normal Claude/ChatGPT query would give you gets shredded, and often the
user gets nothing. This is a verifiability-vs-usefulness tradeoff cranked to the extreme-verifiability
end.

## Goal of Option B

Make the current-context section behave like a good, trusted-source-guided manual LLM query:
1. **Keep** the trusted-domain web search + Claude's cited synthesis the app already produces.
2. **Present** it with its citations under a clear label (e.g. "AI-generated current context from
   trusted sources — verify before use").
3. **Soft-flag** claims the app can't machine-verify (missing exact date, non-exact quote, etc.)
   instead of deleting them.
4. **Degrade gracefully**: a review must **never fail** solely because current-context claims didn't
   pass verification. Worst case → a labelled "current context (unverified / thin)" section.
5. Leave the rest of the app (uploaded-document analysis vs FCV frameworks) as rigorous as it is.

## Where the gauntlet lives (start here)

- `src/cpf_fcv_reviewer/public_research.py`
  - `_search()` — normalization `messages.parse` → `_validate_normalized_claims` → `_salvage_grounded_segments`,
    then `raise ValueError("Anthropic response contained no parsed output.")` when both empty. This raise
    is misleading — it usually means *all claims were rejected by validation*, not that parsing failed.
  - `_validate_normalized_claims` / `_salvage_grounded_segments` — the per-claim gates:
    `source.published_at is None`, publisher == ReliefWeb, `_quote_is_from_source` (exact substring),
    `_text_mentions_country`, single-sentence (salvage). These are the deletion points.
  - `retain_public_claims` / `_is_permitted_public_source` — publisher allowlist.
  - `_source_mentions_country` — compound-neighbour disambiguation (Guinea vs Guinea-Bissau). Consider
    biasing the *search query itself* for ambiguous names ("Guinea (Conakry), not Guinea-Bissau").
- `src/cpf_fcv_reviewer/research_controller.py`
  - `_qualifying_claims`, `_missing_coverage`, tier selection (FULL/REDUCED/document-led). The reduced
    tier already accepts "one recent trusted finding"; Option B extends the same spirit.
- `src/cpf_fcv_reviewer/validators.py` (~line 677) — `missing_current_context_support` per-priority-area
  substantive-support check.
- `src/cpf_fcv_reviewer/review_engine.py` — `REPAIRABLE_ISSUE_CODES` (contains
  `missing_current_context_support`) and the `repair()` loop; when a repairable issue can't be repaired,
  the run fails. Option B likely makes `missing_current_context_support` non-fatal (drop/soft-flag the
  unsupported current-context, keep the review) rather than run-failing.

## Design questions to resolve in brainstorming (before coding)

1. **Citation-risk policy.** What labelling makes an unverified-but-trusted synthesis acceptable in a
   WBG advisory (not policy-determining) context? (The app already carries advisory disclaimers.)
2. **Verification → signal, not gate.** Turn each current-claim check (date, exact quote, country) into
   a per-claim *confidence flag* surfaced in the UI/DOCX, instead of a deletion.
3. **Graceful degradation.** Make `missing_current_context_support` non-fatal; define the "current
   context (unverified/thin)" fallback section.
4. **Search disambiguation** for ambiguous country names.
5. **Scope guard.** Only the current-context path changes; uploaded-document analysis stays rigorous.

## How to test a real end-to-end run

- Trigger: `POST /api/reviews` (multipart `cpf`, `country`, `review_stage=decision_review`,
  `context_documents`) → stream `GET /api/reviews/<id>/events` → `GET /api/reviews/<id>/result` →
  `GET /api/reviews/<id>/export.docx`. The app uses its own server-side key.
- Real Guinea docs (local): `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\guineacpf.pdf`
  + `guinearra.pdf`. Synthetic fixture: `tests/fixtures/synthetic_en.txt`.
- **Corporate proxy:** local httpx to onrender.com / api.anthropic.com must merge the WBG root CA
  (`SSL_CERT_FILE` = `...\wbg-root-ca-g2-fixed.pem`) with `certifi`, else `CERTIFICATE_VERIFY_FAILED`.
- Render MCP: service `srv-d9tju52jobas73d6jvk0`, workspace `tea-d6de2tsr85hc73bqdi0g`. Watch for
  `research_provider_exception`, `research_reduced`/`research_document_led`, and `run_failed`.
- Provider-free suite: `python -m pytest -q` (clear inherited `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`/
  `CURL_CA_BUNDLE` first). A "good" outcome for Option B: a run **completes** (`run_complete`) with a
  labelled current-context section, and never fails solely for lack of verified live news.

## Housekeeping
- Rotate the Anthropic API key exposed in the prior chat (Render → Account → API Keys), update the
  service env var.
- A real assessment is a **paid** run — get explicit authorization before each one.
