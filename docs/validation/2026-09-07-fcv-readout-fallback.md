# 2026-09-07 - FCV model-readout fallback: implemented, deployed, and verified

Deployed build: `main` @ `ec8d3e3` (PRs #17 feature + #18 fix), live on Render
`srv-d9tju52jobas73d6jvk0` (`/health` → `release: ec8d3e3`).

## Superseded status

The confirmation that was pending in this dated record was completed on release
`63b16da`. The Guinea run emitted `fcv_readout_generated` with six themes, carried the
verify-before-use limitation into the result, reached `run_complete`, and exported a
valid DOCX. No independent current-context evidence was accepted, so the fallback was
exercised as a context-only resilience path. See `docs/validation/2026-09-07-guinea-acceptance.md`.


## Why (the Guinea "nothing returned" problem)

On the Option B acceptance run, Guinea returned **0 accepted external current-context claims**
(`country_mismatch: 13/13`) and went `document_led`. Root cause diagnosis: the app's web
search is **restricted to ~10 institutional `allowed_domains`** (ICG, UN, ReliefWeb, ISS,
Africa Center, etc.), and the news wires (Reuters/AP/BBC) are excluded because they 400 the
Anthropic crawler when placed in `allowed_domains`. So the search never sees the broad web a
Google-News query does; on those few institutional domains, recent Guinea-Conakry FCV
coverage is sparse and neighbour-country (Guinea-Bissau) content dominates. The country-match
floor is working correctly — the constraint is the narrow search surface.

## What was built (PR #17) + fixed (PR #18)

A **knowledge-based FCV readout fallback**: when research is `document_led` (no external
current sources), the app generates a bounded Claude readout (no web tool) of current FCV
conditions/themes for the country over the recency window (since the RRA if known), injects it
into the review as **context-only, clearly caveated** ("AI-generated; no external current
sources were available; verify before use"), and guarantees a provenance caveat + the readout
in the result `limitations`. Best-effort: a readout failure never fails the run.
Files: `fcv_readout.py`, `prompts/fcv_readout.md`, review-prompt handling,
`review_engine.review(..., current_context_readout=)`, runtime wiring, tests.

PR #18 fixed a one-line defect found on the paid run (below): `load_prompt()` has a
`PROMPT_NAMES` allowlist that did not include `fcv_readout`, so it raised `ValueError`
instantly and the best-effort guard swallowed it (`fcv_readout_unavailable`). Added
`fcv_readout` to the allowlist, a regression test, and surfaced the error type in the event.

## Paid runs tonight (2 authorized/used)

1. **Option B acceptance** (build `4dd0f69`): `run_complete`, document_led, advisory
   `missing_current_context_support` — PASS. See
   `2026-09-06-option-b-paid-guinea-acceptance.md`.
2. **Readout run** (build `f31e3c6`, before the allowlist fix): reached `run_complete`
   (46,935-byte DOCX, 3 priorities), advisory_notice fired again — but emitted
   **`fcv_readout_unavailable`** because of the `PROMPT_NAMES` allowlist defect. This run is
   what exposed the bug.

## Confirming run - completed later on release `63b16da`

At the time of this record, the allowlist fix (`ec8d3e3`) was provider-free verified
and deployed, but the confirming paid run had not yet been authorized. That run was later
completed on release `63b16da`; the original procedure is retained below as historical
reproduction context.

Original confirmation procedure:
```
cd "C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\20260907_readout_fixed_run"
C:\WBG\Python313\python.exe run_guinea_paid.py
```
(The folder already has `merged_ca.pem` and the runner; `/health` must show
`release: ec8d3e3` or later.) The expected `fcv_readout_generated` event and
verify-before-use limitation were observed in the later `63b16da` acceptance, with six
fallback themes. The current acceptance record is `docs/validation/2026-09-07-guinea-acceptance.md`.

## Recommended next (higher-value root fix, not done)

Broaden the search rather than only falling back: when the domain-restricted search yields
zero accepted current claims, do **one unrestricted `web_search` retry** (no `allowed_domains`
→ no 400) and keep only trusted publishers via the existing publisher-allowlist floor
(Reuters/AP/BBC are already permitted publishers). That would surface **real** Guinea wire
reporting and exercise the grade-and-keep/confidence-chip path with genuine sources — better
than a model readout. The readout remains the last-resort safety net. This deserves its own
careful cycle + paid run.

## Housekeeping (carried over)
- Rotate the previously-exposed Anthropic API key; update the Render env var.
- Base carries 4 pre-existing `test_public_research.py` article-metadata/streaming failures,
  unrelated to this work.
