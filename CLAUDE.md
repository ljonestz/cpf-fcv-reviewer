# CLAUDE.md

## Project scope

This repository contains the CPF FCV Reviewer, an advisory prototype that is separate from the stable FCV Project Screener.

## Commands

- Test: `.\.venv\Scripts\python.exe -m pytest -q`
- Lint: `.\.venv\Scripts\python.exe -m ruff check .`
- Run:  `.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run`
- Export: use **Export Word note** for an active review, or `GET /api/reviews/<assessment_id>/export.docx`.
- Incident stop: stop the local server; do not retry, export, or share a review when a non-sensitive-input, policy, registry, or unexpected-output concern is identified. Do not put raw source content, model output, secrets, or user corrections in incident records.

## Safety and policy boundaries

- Do not make policy, compliance, eligibility, endorsement, or clearance determinations, or unsupported claims about OPCS requirements.
- Do not directly use confidential policy files; use only approved historical, synthetic, or non-sensitive inputs.
- Do not add durable review storage. Review state is session-only and in-memory: restart, expiry, and reset destroy it.
- Do not commit secrets, credentials, API keys, or `.env` files to Git.
- **Do not modify, integrate with, deploy through, or otherwise change the stable FCV Project Screener service.**

## MVP operating boundary

| Capability | MVP | Validation | Production |
| --- | --- | --- | --- |
| Review and export | Advisory review and DOCX note only | Synthetic fixtures, tests, and local browser smoke | Not approved for operational use |
| State | One-process volatile memory | Reset and expiry tested | No durable retention, audit, or identity controls |
| Sources | Upload fallback, public web, source-precedence interfaces | Synthetic adapters only | No operational SharePoint or ITS access |
| Institutional language | Validated registry hydration | Synthetic registry and fail-closed tests | Needs an OPCS-owner-approved versioned registry bundle |
| Deployment | Local MVP | No deployment validation | No Render deployment; no production-readiness claim |

- A direct, current SharePoint RRA original takes precedence over derived copies. If no unambiguous current original is available, use an upload as the fallback. Operational SharePoint and ITS access are out of scope.
- OPCS owns policy-sensitive language. Require an approved, versioned, unexpired registry summary with its integrity check; fail closed if it or a required entry is unavailable. Never derive policy language from model memory or make policy, compliance, eligibility, endorsement, or clearance determinations.
- Current-context research is public-web only. Do not use licensed sources, including ACLED.
- Output is English. French input has limited support and does not change the output language.
- Do not use the MVP with confidential operational packages.

## Worktrees

Use `.worktrees/` as the project-local directory for isolated Git worktrees.
