# CPF FCV Reviewer

An advisory application for evidence-linked FCV review of Country Partnership Framework (CPF) and Country Engagement Note (CEN) drafts. It combines uploaded documents and current public context to produce a five-minute readout, detailed analysis, editable Word exports and a follow-on assistant.

**Start here:** [ITS handover guide](docs/handover/20260908_ITS-handover.md) · [Documentation index](docs/README.md) · [Readiness](docs/PRODUCTION_READINESS.md)

## Access and status

This GitHub repository is **public**. ITS colleagues can browse and clone it without a repository invitation. Service credentials and local assessment artifacts are not included.

[Public prototype](https://cpf-fcv-review-prototype.onrender.com/) — use only public or approved non-sensitive documents. This supports expert judgment, not policy compliance or clearance decisions.

The documented application release is `27ef3aa` (8 September 2026); source baseline for this handover is `2fc2b77`. Recorded release validation includes 1,527 provider-free tests. The live Guinea acceptance preceded the latest Word presentation changes. See [project status](docs/PROJECT_STATUS.md) for evidence and chronology.

Readiness remains **supervised expert pilot**. Known issues include RRA date provenance, recommendation framing, limited source diversity and volatile storage on the public service. [Production readiness](docs/PRODUCTION_READINESS.md) explains these precisely.

## Run a synthetic demonstration

Use Python 3.13. From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/run_smoke.py
```

Open http://127.0.0.1:58422/ and upload `tests/fixtures/synthetic_en.txt`. This deterministic demonstration needs no model API key. It verifies the workflow, not analytical quality.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py -q
```

For real assessments, configure model access, the approved registry and storage as described in the [handover guide](docs/handover/20260908_ITS-handover.md). Real assessments incur model API costs.

## Folder map

| Folder | Contents |
|---|---|
| `src/cpf_fcv_reviewer/` | Backend pipeline, templates, browser assets and Word export |
| `prompts/` | Model instructions |
| `registry_bundles/` | Public guardrails, checksums and provenance |
| `tests/` | Regression tests and synthetic fixtures |
| `scripts/` | Demonstration and validation tools |
| `docs/` | ITS guidance, readiness, status and historical evidence |

Keep the complete checkout: prompts and registry assets are resolved relative to it. Generated outputs, environments, caches and local worktrees are not part of the handover source.

## Development and hosting

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
```

The last command requires real-runtime configuration. See [CLAUDE.md](CLAUDE.md) for maintenance rules and the provider-free-first validation process.

`render.yaml` remains a historical deployment reference with a branch and durable-storage configuration that do not describe the current volatile public service. Review its settings before provisioning a new deployment. This handover changes neither hosting nor app behavior.

The stable FCV Project Screener is separate. Future ITS integration is described in the guide; this repository does not modify that system. Internal policy documents, credentials, raw assessments and assistant conversations must remain outside Git.
