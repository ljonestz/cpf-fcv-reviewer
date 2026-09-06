# 2026-09-06 — live-news (current-context) pipeline: three root-cause fixes + live verification

Deployed production commit at end of session: **`bf1f14b`** (PRs #11, #12, #13 merged to `main`,
each manually deployed to Render service `srv-d9tju52jobas73d6jvk0`). `/health` returned 200 and the
app started cleanly after each deploy.

## Why this mattered

For 6–7 prior sessions the app could not embed live current-context (FCV news) into a review. The
cause was invisible because **every test mocks the Anthropic provider**, so the real failures never
surfaced, and the app logged nothing useful. The current-context research would return zero accepted
claims, fall back to document-led, and the review validator then failed the whole run
(`missing_current_context_support` → `repair_failed` → `review_failed`). That `review_failed` is the
failure that dominated the Render logs.

## Root causes found, fixed, deployed (each reproduced against reality)

1. **web_search HTTP 400 (PR #11).** `public_research.py` sent `allowed_domains` containing news wires
   (`reuters.com`, `apnews.com`, `bbc.com`, `bbc.co.uk`) whose sites block Anthropic's crawler.
   Anthropic rejects the *entire* request with `invalid_request_error: "The following domains are not
   accessible to our user agent"` (confirmed live, `req_011Cen5rjLbvogiirH5nzooS`). Deterministic →
   failed 100% of runs. **Fix:** `CRAWLER_BLOCKED_SEARCH_DOMAINS` excluded from the domains sent (they
   remain approved *publishers*), plus a self-heal that drops any domain Anthropic rejects and retries
   once (`_inaccessible_search_domains`, `_create_web_search_response`). Live proof: `source_candidates: 20`.

2. **Country over-rejection (PR #11).** `_source_mentions_country` rejected any source mentioning both
   the selected country and a compound neighbour (e.g. Guinea + Guinea-Bissau), discarding legitimate
   West-African reporting. **Fix:** strip compound-neighbour names, then require a standalone reference
   (keeps co-mentions, still rejects neighbour-only sources). Live proof: Benin `country_mismatch` fell
   from 12–14 to 2.

3. **Publication date read from the wrong field (PR #13).** Anthropic's `web_search_result` carries the
   date in **`page_age`** (verified against the web-search docs; e.g. `"April 30, 2025"`), but
   `_source_metadata` only read `published_at`/`published_date`/`publication_date`, so real search
   results were always dateless and the publication-date gate rejected every claim. **Fix:** add
   `page_age` to the date-field tuple. Live proof: real Guinea RRA run showed `missing_publication_date: 0`
   (was 3/3).

- **PR #12** (`MAX_NORMALIZATION_OUTPUT_TOKENS = 8000`) was a *mis-diagnosis* — verification against a
  live run showed it did not change the outcome. It is a harmless robustness improvement (the
  normalization `messages.parse` output can legitimately be large) and was left in place.

- **New observability:** `research_controller._classify_exception` now logs `research_provider_exception`
  at WARNING with the real exception type/status/detail — research failures are now diagnosable from
  Render logs (they were not before).

## Live verification runs (deployed app, real POST /api/reviews)

| Document | search | country_mismatch | dates | claims accepted | terminal |
|---|---|---|---|---|---|
| Benin synthetic (thin) | 20 src | 2 | — | **YES** (`research_reduced`) | `review_failed` (validator) |
| **Guinea real CPF+RRA** | 20 src | 14 | `missing_publication_date: 0` | NO (0) | `review_failed` (validator) |

Both the live-news search and dating now work. The runs still end `review_failed` for a *different*,
downstream reason (see below).

## Remaining blocker (NOT fixed — deliberately handed to a fresh session)

No run yet reaches `run_complete`, because the app **cannot complete a review with zero accepted
current-context claims**: `missing_current_context_support` is in `REPAIRABLE_ISSUE_CODES`
(`review_engine.py`) but repair cannot fabricate evidence research did not return. Two intertwined
causes:

- **Claim acceptance is still fragile.** Real Guinea search returns mostly Guinea-Bissau content
  (correctly filtered → `country_mismatch: 14/17`), and the few genuine Guinea claims still fail the
  normalization/validation gauntlet even with dates resolved.
- **The validator mandates current-context** rather than degrading gracefully when live news is thin.

The agreed next step is **Option B** — see `docs/handover/2026-09-06-option-b-current-context-synthesis.md`.

## Test assets

- **Real Guinea CPF/RRA (source docs, local only, not in repo):**
  `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\guineacpf.pdf` and
  `guinearra.pdf`. (Do **not** open the dated sub-folders' sensitive assessment-handoff files.)
- **Synthetic fixture:** `tests/fixtures/synthetic_en.txt` (used by `scripts/run_smoke_browser.py`, Benin).
- **This session's run traces:**
  `C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\20260906_pageage_fix_verification\`.

## How to trigger a real assessment (for the next session)

`POST /api/reviews` (multipart): `cpf` (file), `country`, `review_stage` (e.g. `decision_review`),
`context_documents` (file); then stream `GET /api/reviews/<id>/events` (SSE). The app uses its own
server-side Anthropic key — no key needed in the trigger. **On the WBG corporate machine**, local httpx
to `*.onrender.com` or `api.anthropic.com` must merge the WBG root CA (env `SSL_CERT_FILE` →
`wbg-root-ca-g2-fixed.pem`) with certifi, or TLS fails with `CERTIFICATE_VERIFY_FAILED`. Read Render
logs via the Render MCP (`list_logs`, resource `srv-d9tju52jobas73d6jvk0`, workspace
`tea-d6de2tsr85hc73bqdi0g`).
