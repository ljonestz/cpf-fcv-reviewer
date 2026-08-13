# CPF FCV Reviewer

An advisory prototype for note-first, evidence-linked FCV review of CPF and CEN drafts. It supports expert judgment and practical options; it does not make policy, compliance, eligibility, endorsement, or clearance determinations.

**The stable FCV Project Screener is a separate product and must not be modified, integrated with, or deployed through this repository.**

## Current prototype

- Public prototype: <https://cpf-fcv-review-prototype.onrender.com/>
- Current application version: `0.1.0`
- Latest local functional commit: `0e596a9`
- Deployment health response: `ok`; storage: `volatile`; the Render release label `4acca30` is stale and is not the Git commit or application version.

The public service is an MVP, not approved for operational use. Use only approved historical, synthetic, or otherwise non-sensitive material. Do not submit confidential operational packages.

The review starts with three document buckets: the draft CPF/CEN, accompanying package documents, and an optional public RRA or supporting analytics. Country inference uses the recognized title when available and requires manual country confirmation when it is not. Review stage is selected explicitly: Early drafting / PCN, Concept review, Decision review, ROC / OC, Finalization, or Response to comments.

Every review performs bounded current-country public-web research. An uploaded public RRA changes the research window but never suppresses that current research. Retryable research failures can be retried in the browser using the retained volatile uploads; retry never exposes partial output.

Completed results open in a separate experience with a default **Five-minute readout** and an authoritative **Detailed analysis** view. Both derive from the same canonical result, and the full detailed note can be downloaded as DOCX. Evidence details are collapsed by default. Correction reruns refer to the review itself, not to individual findings. There is no questions-for-confirmation section.

## Safety boundary

- Review state is in-memory and temporary: restart, expiry, or **Start a new review** destroys it.
- A direct current RRA original takes precedence over derived copies; upload is the public-prototype fallback. Operational SharePoint and ITS access are out of scope. A future internal ITS implementation would use the existing source-adapter boundary with separately governed, permission-aware SharePoint access.
- Public current-context research is public-web only. Do not use licensed sources, including ACLED.
- The public prototype uses approved non-confidential guardrails and fails closed when its required registry bundle is invalid or unavailable. Detailed internal policy content belongs on a separately governed internal track.
- Output is English. French input support is limited.
- The public prototype is non-production, uses volatile state and public-web-only current context, and has no production-use approval. The local redesign has not been deployed; the Render `APP_RELEASE` label remains stale.

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

Use **Download full detailed note** only while the volatile review remains active.

## Documentation

- [Current project status](docs/PROJECT_STATUS.md): completed work, deployment state, limitations, and next considerations.
- [Development instructions](CLAUDE.md): commands, repository map, safety constraints, and future-session checklist.
- `docs/validation/`: dated validation evidence.
- `docs/superpowers/`: historical designs and implementation plans.
