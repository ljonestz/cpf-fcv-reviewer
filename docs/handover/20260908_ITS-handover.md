# CPF FCV Reviewer ITS handover

Prepared for ITS colleagues | 8 September 2026

## Purpose and starting point

The CPF FCV Reviewer helps country and FCV teams review draft Country Partnership Frameworks (CPFs) and Country Engagement Notes (CENs). It combines the draft, accompanying documents, an optional Risk and Resilience Assessment (RRA), and current public reporting to produce an evidence-linked advisory note. It supports expert review and practical drafting decisions; it does not determine policy compliance, eligibility or institutional clearance.

This guide provides a route from the repository to a local demonstration, explains the main components, and identifies decisions needed to incorporate the capability into the internal FCV Project Screener. The existing application is suitable for supervised use with public or approved non-sensitive documents. Internal operational deployment requires further quality acceptance and ITS hosting and access decisions.

Source: [ljonestz/cpf-fcv-reviewer](https://github.com/ljonestz/cpf-fcv-reviewer). The repository is public, as verified on 8 September 2026 after the owner changed its visibility. ITS colleagues can browse and clone it without a repository invitation. Service credentials and local assessment artifacts are not included.

This handover uses source baseline `2fc2b77`, fetched from GitHub main on 8 September 2026. The preceding application release is `27ef3aa`; the repository records its deployment and 1,527 passing provider-free tests. These are recorded release results, not a new full test run for this handover. Live Guinea acceptance predates the final Word presentation changes. See [production readiness](../PRODUCTION_READINESS.md) and [Word release validation](../validation/2026-09-08-word-export-presentation.md).

## What the user does

1. Upload a draft CPF or CEN, accompanying package documents, and optionally an RRA or other contextual material.
2. Confirm the country, choose the review stage, and optionally specify a review focus.
3. Follow progress while the app extracts documents, researches current public context, builds evidence and generates a structured review.
4. Read the five-minute readout or detailed analysis, inspect evidence and limitations, and download either version as an editable Word document.
5. Ask follow-on questions grounded in the completed review, or submit corrections and rerun.

The primary CPF/CEN remains the principal object of review. Package documents receive detailed attention; the RRA supplies diagnostic themes and contextual evidence. Current research complements the uploaded diagnostic. The output considers potential harm and practical adaptation to country conditions.

English is the output language; French input support is limited. Uploaded material and user instructions are treated as untrusted content. Explicit extraction and model-input limits apply; incomplete coverage must not be presented as complete analysis.

## Repository structure

| Location | Responsibility |
|---|---|
| README.md | Entry point, installation and demonstration commands |
| src/cpf_fcv_reviewer/ | Flask application and review pipeline |
| src/cpf_fcv_reviewer/templates/ | HTML intake, progress and results interface |
| src/cpf_fcv_reviewer/static/ | Browser JavaScript and styles |
| prompts/ | Version-controlled model instructions |
| registry_bundles/ | Public guardrails, Strategy grounding, checksums and provenance |
| tests/ | Regression checks and synthetic fixtures |
| scripts/ | Smoke demonstration and explicitly invoked validation utilities |
| docs/handover/ | This guide and historical technical handoffs |
| docs/validation/ | Dated evidence for particular releases |
| docs/superpowers/ | Historical designs and implementation records |
| requirements*.txt and pyproject.toml | Dependencies and development configuration |
| wsgi.py and hosting configuration | Service entry point, Gunicorn and Render settings |

The package layout is intentional. Keep prompts/ and registry_bundles/ alongside src/: the runtime resolves assets from the checkout. Installation is editable (-e .). A standalone wheel has not been qualified as an ITS distribution format; use a complete Git clone.

Virtual environments, generated package metadata, caches, review outputs and local worktrees are not source deliverables. Historical plans and validation records remain in Git for traceability. The README and documentation index distinguish current guidance from those records.

## How the components fit together

app.py constructs Flask, loads configuration and registers routes.py. It selects the volatile or SQLite session store and background processing path. runtime.py wires extraction, research, evidence, model and validation services; orchestrator.py coordinates review steps.

extraction.py, diagnostic_sources.py and diagnostic_map.py extract text and identify and map diagnostic evidence. research_controller.py, public_research.py, curated_research.py and fcv_readout.py handle current public context and qualified fallback behavior. evidence_builder.py prepares structured evidence.

review_engine.py and model_gateway.py implement model interactions. contracts.py defines structured data; validators.py applies evidence and output checks. registry.py verifies the guardrail bundle. Prompt and contract changes require relevant regression tests.

session_store.py, persistent_store.py and background.py manage state and execution. follow_on.py handles the bounded assistant. export_docx.py produces both Word views. The browser interface uses templates/index.html, static/app.js and static/styles.css.

FCV-AGENT also uses Flask, browser JavaScript, explicit prompts, tests and ITS handover notes. It places more logic in root files such as app.py and background_docs.py; this application separates that logic into a package. Reuse the capability and contracts without flattening the layout merely to match filenames.

## First local demonstration

Use Python 3.13 and run these PowerShell commands:

```powershell
git clone https://github.com/ljonestz/cpf-fcv-reviewer.git
cd cpf-fcv-reviewer
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/run_smoke.py
```

Open http://127.0.0.1:58422/ and use tests/fixtures/synthetic_en.txt as the primary input. Confirm Benin if requested and choose a review stage. This deterministic demonstration uses no model API key and does not establish country-analysis quality. Stop the server with Ctrl+C.

Run provider-free smoke tests separately:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py -q
```

The optional browser runner requires Playwright, which is not included in requirements-dev.txt. It is only needed for automated browser checks, not for using the application manually.

## Configuration for a real assessment

Real assessments require an authorized model account and can incur API charges. Supply configuration through the process environment or an approved secret manager. Do not assume that creating a .env file configures production. Never commit keys or session data.

| Variable | Meaning |
|---|---|
| ANTHROPIC_API_KEY | Required for the real model runtime; supply securely |
| ANTHROPIC_MODEL_ID | Defaults to claude-sonnet-4-5; changes need quality validation |
| REGISTRY_BUNDLE_PATH | Approved bundle path, currently registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json |
| REGISTRY_BUNDLE_SHA256 | Approved checksum from the matching .sha256 record |
| APP_ENV | Defaults to production; local development may explicitly use development |
| PERSISTENCE_PATH | SQLite file on durable storage for production |
| ALLOW_VOLATILE_PROTOTYPE | Explicit non-production exception; restart loses sessions |
| SESSION_TTL_SECONDS | Default 86400 seconds, also applying to assistant history |
| APP_RELEASE | Release label; RENDER_GIT_COMMIT takes precedence |
| RELIEFWEB_APP_NAME | Optional identity for the ReliefWeb research path |

Read config.py for research controls and registry_bundles/README.md for provenance. The bundle must pass integrity and validity checks. Its public-prototype approval is not institutional policy clearance.

After setting the environment, run locally with .\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run. Hosted Linux execution uses Gunicorn. The /health endpoint reports release, storage and queue mode; it does not validate analytical quality.

render.yaml is a deployment reference, not a dump of the live service. It names the historical fix/research-resilience-guided-journey branch and specifies a paid instance and persistent disk. The recorded public service uses volatile storage. ITS must select the intended branch, hosting and storage rather than deploy this file unchanged. This handover does not change the live service.

## Interfaces ITS can build around

These routes are prototype interfaces rather than a separately versioned integration API. Read routes.py and contracts.py when implementing a client.

| Interface | Use |
|---|---|
| POST /api/detect-country | Suggest the country from the primary document |
| POST /api/reviews | Create a review |
| GET /api/reviews/<id>/events | Stream progress through server-sent events |
| GET /api/reviews/<id>/result | Retrieve review state and results |
| GET /api/reviews/<id>/export.docx | Detailed Word output; ?view=summary selects the short readout |
| GET and POST /api/reviews/<id>/assistant | Restore history or request a streamed answer |
| POST /api/reviews/<id>/corrections | Submit corrections for a rerun |
| POST /api/reviews/<id>/retry-research | Retry an eligible research failure |
| DELETE /api/reviews/<id> | Reset the review |

Review creation uses multipart cpf, country and review_stage, with optional repeated package_documents and context_documents fields and review_focus. The response includes an assessment identifier and event and result URLs.

Treat identifiers as sensitive application handles. Current routes do not implement ITS single sign-on or per-user review authorization. Internal integration must enforce those controls; an unguessable identifier is not an authorization model.

## Integration decisions for ITS

First run the synthetic demonstration and review an output with the FCV team. Then decide whether to expose the capability as an internal service behind the existing screener or port its workflow into that application. A service boundary could preserve the package and tests; the choice depends on ITS architecture. This is a discussion recommendation, not an agreed design.

- Identity and ownership: connect institutional sign-on, authorize every review operation and establish the support owner.
- Model and network access: select an approved gateway and validate structured-output behavior; configure approved egress and institutional certificate trust without disabling TLS verification.
- Storage and execution: qualify durable storage, restart recovery, retention and deletion. The supplied deployment uses one instance and one Gunicorn worker with threads; multi-instance scaling is not established.
- Streaming and interface: preserve progress and assistant streams through the proxy, check route prefixes and browser URLs, and decide which interface elements join the main screener.
- Internal sources: implement permission-aware retrieval through the application source boundary. SharePoint integration is not currently implemented; the model must not be assumed to have internal access.
- Grounding and quality: govern internal policy material separately from the public bundle and preserve attribution, human review and visible limitations.

No changes to the stable FCV Project Screener are included.

## Acceptance and known limitations

The recorded Guinea run completed the review, assistant restoration and both Word exports. It also exposed a wrong RRA date: September 2022 instead of the cover date June 2023. Some delivery recommendations need expert validation. Current evidence came from two articles from one publisher, with reduced breadth disclosed. Cross-country quality acceptance remains necessary.

The public service uses volatile storage, so its nominal review lifetime does not survive restarts. SQLite persistence exists in code, but ITS must test its selected deployment and recovery behavior. These limitations are tracked in docs/PRODUCTION_READINESS.md; smoke tests do not resolve them.

For changes, run targeted tests and then the provider-free smoke suite. Full checks are python -m pytest -q and python -m ruff check . in the configured environment. Verify the deployed revision and health before an explicitly authorized model-backed assessment. Keep review documents, model content, assistant conversations, credentials and live identifiers outside Git.

## Handover checklist

1. Share the public GitHub link with ITS and agree the adoption revision.
2. Run the synthetic demonstration and smoke tests.
3. Review the folder map, routes, prompts, contracts and readiness record together.
4. Agree service integration versus porting, ownership, identity, model access and durable hosting.
5. Resolve the date issue and validate recommendation framing with country and FCV experts.
6. Qualify the internal environment using approved documents, restart checks and a broader country sample before operational rollout.

The Markdown guide is the maintainable source; the matching dated Word document is the shareable copy. Historical records provide traceability, while the README and this guide provide the recommended entry path.
