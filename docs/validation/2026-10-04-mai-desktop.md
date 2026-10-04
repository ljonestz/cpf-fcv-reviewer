# Local mAI Desktop integration: 4 October 2026

Scope: local DEV proof-of-concept/testing only. This is not a hosted deployment,
Application access approval, or a full CPF quality acceptance result.

## Connection checks

Desktop WAM authentication succeeded using the existing local SDK environment.
The owner selected Sonnet 4.6 and supplied a team label. The gateway accepted that
label; this does not establish its administrative allocation in ITSAI reporting.
No token or credential was saved.

Three non-sensitive, bounded DEV requests were made:

| Check | HTTP | Outcome | Input / output tokens |
|---|---|---|---|
| Plain echo | 200 | Expected response | 15 / 5 |
| Anthropic-style schema field | 200 | Plain text, not schema conforming | 19 / 5 |
| Bedrock Converse schema field | 200 | Valid structured JSON, completed normally | 160 / 8 |

Total reported usage: **212 tokens**. There were no direct Anthropic API calls
and no full assessments. DEV quota usage is not a statement that all platform
usage or eventual production usage is free.

The second check matters: HTTP success alone did not establish schema enforcement.
The adapter uses `outputConfig.textFormat.structure.jsonSchema`, the successful
Converse format, and still applies the application's Pydantic/evidence validation.
See [AWS's structured-output contract](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
and [the platform's text-generation documentation](https://ai.worldbankgroup.org/maifactory/text-generation/).

## Implementation and verification

- Opt-in `MODEL_PROVIDER=mai_desktop` requires development mode and a valid team
  header. The default remains the existing direct Anthropic provider.
- Review, diagnostic mapping, repairs and assistant calls use the same Desktop
  adapter. Its endpoint is fixed to DEV; no provider fallback or HTTP retries.
- Authentication is serialized and refreshed through `get_token`, avoiding the
  installed SDK's indefinitely cached `token_provider` method.
- Incomplete, refused, empty, invalid and failed responses are withheld. Provider
  error bodies are not exposed in application exceptions.
- The owner approved the existing institutional research path. It currently uses
  Crisis Group feeds and ReliefWeb when an approved app name is configured; the
  World Bank indicator adapter is not part of that recovery path. Research remains
  qualified even if ordinary source-count thresholds are met. No broad search is
  claimed. Existing document-led limitations remain in force when research fails.
- The local assistant returns a completed response in one chunk. Native provider
  streaming is not yet verified.
- The launcher binds to `127.0.0.1:58423`, disables the reloader, uses SQLite and
  retains the four-per-day assessment admission default. Remote, foreign-origin,
  non-local-host and forwarded requests are rejected in Desktop mode.

**252 focused tests passed** across Desktop contracts, configuration, runtime wiring
and smoke mode. A subsequently added cross-site regression failed before the guard
was implemented; **61 Desktop/smoke checks then passed**. Six changed Python files
were parsed successfully. The local Ruff executable is blocked by Windows
Application Control, so local Ruff success is not claimed.

The first broad focused run hit the workstation's pre-existing invalid
`SSL_CERT_FILE` (21 failures, 225 passes). Re-running with a valid CA file set only
for that process produced the 252 passes. TLS verification was not disabled.

Local startup authenticated successfully and `/health` reported persistent storage,
a live persistent worker and status `ok`. Intake, JavaScript and CSS returned HTTP
200; a foreign-origin request returned 403. Eleven missing application packages
were added to the existing mAI virtual environment; every pre-existing package
version was preserved. The pre-install inventory is retained locally under ignored
`output/mai-desktop/`.

## Running locally

Use the existing Desktop SDK environment after installing the app's Python runtime
dependencies. Do not run `uv sync` against the currently empty mAI dependency list.
From this repository, set `MAI_TEAM_NAME` to the actual team label, ensure
`SSL_CERT_FILE` points to a valid trusted CA bundle if that variable is set, and run:

```powershell
& '<your-existing-mAI-venv>\Scripts\python.exe' scripts/20261004_run_mai_desktop.py
```

Open `http://127.0.0.1:58423`. The launcher performs sign-in only; assessments start
only when explicitly submitted. Tokens stay in memory. The optional
`RELIEFWEB_APP_NAME` must be an approved ReliefWeb app name.

## Remaining acceptance

The checks establish connectivity, the request contract and local startup, not
full-size schema acceptance or the analytical quality of a complete review. A
bounded public-document assessment and its exports/assistant still need acceptance
on this provider. Desktop rate limits, full-context latency and streaming remain
unproven. The existing factual/production acceptance holds are unchanged.

Posit Connect hosting remains separate: Application/ACN approval, supported Python
runtime, durable single-instance storage, backups and actual hosted verification
are still required. Never copy Desktop tokens or WAM caches to a server.
