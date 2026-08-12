# CPF FCV Reviewer

An advisory prototype for evidence-linked FCV review of CPF and CEN drafts. It supports expert judgment and practical options; it does not make institutional determinations.

**The stable FCV Project Screener is a separate product and must not be modified, integrated with, or deployed through this repository.**

## Current prototype

- Public prototype: <https://cpf-fcv-review-prototype.onrender.com/>
- Current application version: `0.1.0`
- Latest functional commit: `728eec6`
- Deployment health response: `ok`; storage: `volatile`; the Render release label `4acca30` is stale and is not the Git commit or application version.

The public service is an MVP, not approved for operational use. Use only approved historical, synthetic, or otherwise non-sensitive material. Do not submit confidential operational packages.

## Safety boundary

- Review state is in-memory and temporary: restart, expiry, or **Start a new review** destroys it.
- A direct current RRA original takes precedence over derived copies; upload is the fallback. Operational SharePoint and ITS access are out of scope.
- Public current-context research is public-web only. Do not use licensed sources, including ACLED.
- The public prototype uses approved non-confidential guardrails and fails closed when its required registry bundle is invalid or unavailable. Detailed internal policy content belongs on a separately governed internal track.
- Output is English. French input support is limited.

If a policy-boundary, registry, non-sensitive-input, or unexpected-output concern arises, stop the local server. Do not retry, export, or share the review; record only a safe error category through the applicable internal process.

## Run locally

Use Python 3.13 and install `requirements.txt` plus `requirements-dev.txt` in a virtual environment. Configure these environment variables without committing their values:

- `ANTHROPIC_API_KEY` (required outside tests)
- `ANTHROPIC_MODEL_ID` (optional model override)
- `REGISTRY_BUNDLE_PATH` and `REGISTRY_BUNDLE_SHA256` (approved bundle and integrity check)
- `APP_RELEASE` (deployment label)
- `SESSION_TTL_SECONDS` (optional; defaults to one hour)

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
```

Use **Export Word note** only while the volatile review remains active.

## Documentation

- [Current project status](docs/PROJECT_STATUS.md): completed work, deployment state, limitations, and next considerations.
- [Development instructions](CLAUDE.md): commands, repository map, safety constraints, and future-session checklist.
- `docs/validation/`: dated validation evidence.
- `docs/superpowers/`: historical designs and implementation plans.
