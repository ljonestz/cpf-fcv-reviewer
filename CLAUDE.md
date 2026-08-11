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
| Institutional language | Validated registry hydration | Owner-approved public guardrails and fail-closed tests | Public guardrails only; detailed OPCS policy belongs in a separate internal ITS track |
| Deployment | Local MVP plus controlled public Render prototype | Automated, loader, and deployment smoke checks | No production-readiness claim |

- A direct, current SharePoint RRA original takes precedence over derived copies. If no unambiguous current original is available, use an upload as the fallback. Operational SharePoint and ITS access are out of scope.
- The public prototype uses only product-owner-approved, non-confidential guardrails. OPCS-specific policy language remains outside the public bundle and belongs in a separately governed internal ITS version. Require a versioned, unexpired registry bundle with its integrity check and fail closed when it is unavailable. Never derive policy language from model memory or make policy, compliance, eligibility, endorsement, clearance, classification, allocation, access, or country-status determinations.
- Current-context research is public-web only. Do not use licensed sources, including ACLED.
- Output is English. French input has limited support and does not change the output language.
- Do not use the MVP with confidential operational packages.

## Worktrees

Use `.worktrees/` as the project-local directory for isolated Git worktrees.
