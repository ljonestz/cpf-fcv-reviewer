# CPF FCV Reviewer

An advisory prototype for note-first, evidence-linked FCV review of CPF and CEN drafts. It supports expert judgment and practical options; it does not make policy, compliance, eligibility, endorsement, or clearance determinations.

**The stable FCV Project Screener is a separate product and must not be modified, integrated with, or deployed through this repository.**

## Current prototype

- Public prototype: <https://cpf-fcv-review-prototype.onrender.com/>
- Current application version: `0.1.0`
- Latest provider-free verified implementation: `fix/guinea-production-fixes` through
  code commit `361fe8c` (current branch: 1,170 tests; 36 provider-free smoke tests).
  Review attention is role-aware: the CPF/CEN is the principal lens, accompanying
  package documents are reviewed in detail, and the RRA and other context are thematic
  supporting inputs. The implementation keeps the existing architecture and dependencies.
- Last verified deployment: `361fe8c` on 2026-09-02. Render reported the exact commit
  live, `/health` returned `ok`, and the public page returned HTTP 200 before the quality
  run. Its single authorized Guinea assessment completed extraction, current-country
  research, full-RRA mapping, and drafting, then failed closed with safe code
  `review_failed`; Render recorded a `ValidationError`. No result, assistant conversation,
  or DOCX was produced, so provider acceptance for the role-aware redesign remains
  unestablished. The unchanged deployment must not be rerun.
- The authorized Guinea production quality run on deployed commit `1ba44bf` completed
  successfully on 2026-08-31. The result and DOCX endpoints returned HTTP 200; the core
  result schema, 32 evidence records, reproducibility metadata, and application validation
  passed with zero issues. Browser screenshots, the 79 KB JSON response, and the 49,830-byte
  DOCX were saved. Current-country evidence was truthfully rated `reduced` because only two
  recent public sources were established.

The public service is an MVP, not approved for operational use. Use only approved historical, synthetic, or otherwise non-sensitive material. Do not submit confidential operational packages.

The review starts with three document buckets: the draft CPF/CEN, accompanying package documents, and an optional public RRA or supporting analytics. Country inference uses the recognized title when available and requires manual country confirmation when it is not. Review stage is selected explicitly: Early drafting / PCN, Concept review, Decision review, ROC / OC, Finalization, or Response to comments.

Every review performs bounded current-country public-web research. An uploaded public RRA changes the research window but never suppresses that current research. Retryable research failures can be retried using the retained review package; retry never exposes partial output.

Up to ten accompanying package documents are fully re-extracted and every retained
segment is supplied to the review within explicit limits of 400 segments, 300,000
characters, and a 160,000 estimated-input-token ceiling. If that detailed package review
cannot be completed, the assessment fails closed instead of silently sampling. A
recognized uploaded RRA or equivalent diagnostic is also extracted in full within the
configured safety bounds and is never silently reduced to sampled pages. Its diagnostic
map synthesizes drivers, resilience sources, and key risks using known, nonempty,
representative citations; it does not require the model to assign every RRA page to an
output theme. One sanitized retry remains available only for a schema-invalid map.
Other contextual material may be summarized at a higher level, with incomplete coverage
disclosed rather than treated as proof that content is absent.

Starting an assessment opens a dedicated Project Screener-aligned holding view with a compact elapsed timer, estimate, connected three-stage ticker, and rotating guidance. Completed results open with a default **Five-minute readout** and an authoritative **Detailed analysis** view. The reader-facing HTML and DOCX keep structured evidence internally while presenting concise question-led RRA/current-dynamics and FCV Strategy sections, linked priority measures, and one bounded basis/limitations disclosure. A streamed follow-on assistant uses the completed review and cited evidence, retains up to 20 messages for the review's existing 24-hour lifetime, and restores the review and conversation after refresh. Correction and rerun remains available as a secondary action.

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
summary, detailed output, assistant streaming and refresh restoration, and failure states,
plus the DOCX on success. Smoke output must remain clearly labelled synthetic and must
not be presented as country-quality evidence.
The detailed future-session protocol is in [`CLAUDE.md`](CLAUDE.md).

## Documentation

- [Current project status](docs/PROJECT_STATUS.md): completed work, deployment state, limitations, and next considerations.
- [Approved results, assistant, and full-RRA coverage design](docs/superpowers/specs/2026-08-31-results-assistant-rra-coverage-design.md): bounded implementation scope and acceptance criteria.
- [Approved role-aware source coverage design](docs/superpowers/specs/2026-09-02-role-aware-source-coverage-design.md): primary/package/context attention hierarchy and bounded RRA synthesis.
- [2026-09-02 role-aware source coverage validation](docs/validation/2026-09-02-role-aware-source-coverage-validation.md): provider-free tests, browser evidence, DOCX checks, and deployment checkpoint.
- [2026-09-02 Guinea quality validation on 361fe8c](docs/validation/2026-09-02-guinea-production-quality-361fe8c.md): the single provider-backed attempt, safe failure evidence, resource checks, and external artifacts.
- [2026-09-02 results, assistant, and full-RRA validation](docs/validation/2026-09-02-results-assistant-rra-coverage-validation.md): automated checks, smoke-browser evidence, deployment cycles, and current Guinea acceptance status.
- [2026-09-02 full-RRA map reliability fix validation](docs/validation/2026-09-02-full-rra-map-reliability-fix-validation.md): test-first implementation, security review, provider-free checks, and current deployment status.
- [2026-08-31 Guinea production quality-run validation](docs/validation/2026-08-31-guinea-production-quality-run.md): successful provider-backed run, screenshots, JSON/DOCX checks, and acceptance outcome.
- [2026-08-31 initial-review schema-retry validation](docs/validation/2026-08-31-initial-review-schema-retry-validation.md): test-first evidence, safety review, full provider-free verification, and deployment checks.
- [2026-08-30 Guinea production-fix validation](docs/validation/2026-08-30-guinea-production-fixes-validation.md): automated checks, Render deployment evidence, paid-run outcomes, and remaining acceptance limitation.
- [2026-08-30 pilot reliability validation](docs/validation/2026-08-30-cpf-pilot-reliability-validation.md): automated, Guinea structural, and browser evidence plus provider limitations.
- [Development instructions](CLAUDE.md): commands, repository map, safety constraints, and future-session checklist.
- `docs/validation/`: dated validation evidence.
- `docs/superpowers/`: historical designs and implementation plans.
