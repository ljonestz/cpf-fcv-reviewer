# Application utilities

Run these from the repository root. Ordinary application startup does not require these utilities.

| Script | Purpose |
|---|---|
| run_smoke.py | Deterministic local demonstration; no model API calls |
| run_smoke_browser.py | Browser validation; synthetic by default, real assessment when explicitly supplied --cpf; requires separate Playwright installation |
| 20260907_probe_live_research.py | Historical research probe; inspect arguments and API-cost implications before executing |
| 20260907_run_quality_local.py | Model-backed local quality-run utility; not a quick-start command |
| 20260908_preview_word_reports.py | Local Word presentation preview utility |

Preserve dated scripts for reproducibility. Do not run model-backed utilities as part of routine setup. Generated outputs belong in ignored output folders.
