# CPF FCV Reviewer

An advisory prototype for note-first, evidence-linked FCV review of CPF and CEN drafts. It supports expert judgment and practical options; it does not make policy, compliance, eligibility, endorsement, or clearance determinations.

**The stable FCV Project Screener is a separate product and must not be modified, integrated with, or deployed through this repository.**

## Current prototype

- Public prototype: <https://cpf-fcv-review-prototype.onrender.com/>
- Current application version: `0.1.0`
- Latest verified implementation: `main` through `9816de4` (1,063 tests; 34 provider-free smoke tests).
- Last verified deployment: `9816de4` on 2026-08-30. Render reported the deploy live,
  `/health` returned `ok`, and the public page returned HTTP 200.

The public service is an MVP, not approved for operational use. Use only approved historical, synthetic, or otherwise non-sensitive material. Do not submit confidential operational packages.

The review starts with three document buckets: the draft CPF/CEN, accompanying package documents, and an optional public RRA or supporting analytics. Country inference uses the recognized title when available and requires manual country confirmation when it is not. Review stage is selected explicitly: Early drafting / PCN, Concept review, Decision review, ROC / OC, Finalization, or Response to comments.

Every review performs bounded current-country public-web research. An uploaded public RRA changes the research window but never suppresses that current research. Retryable research failures can be retried using the retained review package; retry never exposes partial output.

Optional PDFs use deterministic, bounded sampling across the full page range. Package evidence is balanced across uploaded files, and incomplete coverage is disclosed rather than treated as proof that content is absent.

Starting an assessment opens a dedicated Project Screener-aligned holding view with a compact elapsed timer, estimate, connected three-stage ticker, and rotating guidance. Completed results open with a default **Five-minute readout** and an authoritative **Detailed analysis** view. The detailed narrative uses question-led RRA/current-dynamics and FCV Strategy sections, short WBG-style paragraphs, and collapsible traceability, evidence-status, and coverage material. The DOCX follows the detailed HTML scope, and download failures stay on the results page with an inline message.

## Safety boundary

- Operational production configuration requires SQLite persistence and fails closed without it. The public reference prototype can use volatile storage only when `ALLOW_VOLATILE_PROTOTYPE=true` is set explicitly.
- A direct current RRA original takes precedence over derived copies; upload is the public-prototype fallback. Operational SharePoint and ITS access are out of scope. A future internal ITS implementation would use the existing source-adapter boundary with separately governed, permission-aware SharePoint access.
- Public current-context research is public-web only. Do not use licensed sources, including ACLED.
- The public prototype uses approved non-confidential guardrails and fails closed when its required registry bundle is invalid or unavailable. Detailed internal policy content belongs on a separately governed internal track.
- Output is English. French input support is limited.
- The public prototype is non-production and has no production-use approval. Keeping it awake can support a bounded test run, but a restart still discards that run; ITS should use governed durable storage in its operational implementation.

If a policy-boundary, registry, non-sensitive-input, or unexpected-output concern arises, stop the local server. Do not retry, export, or share the review; record only a safe error category through the applicable internal process.

## Run locally

Use Python 3.13 and install `requirements.txt` plus `requirements-dev.txt` in a virtual environment. Configure these environment variables without committing their values:

- `ANTHROPIC_API_KEY` (required outside tests)
- `ANTHROPIC_MODEL_ID` (optional model override)
- `REGISTRY_BUNDLE_PATH` and `REGISTRY_BUNDLE_SHA256` (approved bundle and integrity check)
- `APP_RELEASE` (deployment label)
- `PERSISTENCE_PATH` (required in production; use the mounted disk path)
- `ALLOW_VOLATILE_PROTOTYPE` (set to `true` only for the non-production Render test site)
- `SESSION_TTL_SECONDS` (optional; production default is 24 hours)

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
```

Use **Download full detailed note** before the retained review expires or is reset.

## Validation and API-cost control

Use the validation ladder in `CLAUDE.md`: targeted local checks, provider-free smoke,
deployed health/static checks, then one paid quality run only when real model or rendered
output behavior must be verified. Never rerun an unchanged deployment. After a failed
quality run, diagnose only from safe validation codes, add a local regression test, and
repeat the no-cost ladder before seeking approval for another paid run.

Paid browser quality runs must save unique full-page PNGs for intake, holding/progress,
summary, detailed output, and failure states, plus the DOCX on success. Smoke output must
remain clearly labelled synthetic and must not be presented as country-quality evidence.
The detailed future-session protocol is in [`CLAUDE.md`](CLAUDE.md).

## Documentation

- [Current project status](docs/PROJECT_STATUS.md): completed work, deployment state, limitations, and next considerations.
- [2026-08-30 Guinea production-fix validation](docs/validation/2026-08-30-guinea-production-fixes-validation.md): automated checks, Render deployment evidence, paid-run outcomes, and remaining acceptance limitation.
- [2026-08-30 pilot reliability validation](docs/validation/2026-08-30-cpf-pilot-reliability-validation.md): automated, Guinea structural, and browser evidence plus provider limitations.
- [Development instructions](CLAUDE.md): commands, repository map, safety constraints, and future-session checklist.
- `docs/validation/`: dated validation evidence.
- `docs/superpowers/`: historical designs and implementation plans.
