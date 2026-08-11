# CPF FCV Reviewer

CPF FCV Reviewer is an advisory MVP for structured review of Country Partnership Framework (CPF) and Country Engagement Note (CEN) packages through an FCV lens. It supports expert judgment; it does not make policy, compliance, eligibility, endorsement, or clearance determinations.

**Do not modify, integrate with, deploy through, or otherwise change the stable FCV Project Screener service.** This repository is separate from that service.

## Capability boundary

| Capability | MVP implementation | Validation evidence | Production status |
| --- | --- | --- | --- |
| Review purpose | Evidence-linked, advisory FCV review with practical options | Synthetic English, French, and mixed-language fixtures | Not approved for operational use |
| Document and state handling | Session-only, in-memory review state | Reset and expiry behaviour tested; browser reset smoke-tested | No durable storage, retention, audit, or identity controls |
| Sources | Uploaded documents, approved-registry material, and public-web research interfaces | Synthetic adapters and fixtures only | No operational SharePoint access; no live source validation |
| Institutional language | Registry-controlled exact language with validation | Synthetic registry and fail-closed tests | Requires an OPCS-owner-approved, versioned, unexpired bundle |
| Export | Validated result can be downloaded as a DOCX review note | Structural export and browser-download checks | Not a production records or document-management workflow |
| Deployment | Local MVP only | Local automated and browser checks | No Render deployment or production readiness claim |

## Data, source, and policy boundaries

- Review state is volatile and held only for one running process. A restart, session expiry, or **Start a new review** reset destroys it. Do not treat the service as a record system.
- When a current Research and Risk Assessment (RRA) is available, a direct SharePoint original takes precedence over a derived copy. An upload is the fallback when no unambiguous current original is available. Operational SharePoint and ITS access are outside this MVP.
- OPCS owns policy-sensitive language. The application requires an owner-approved, versioned, unexpired registry bundle with an integrity check, and fails closed when that bundle or a required entry is unavailable. It must not invent, paraphrase, or make unsupported policy claims.
- Current-context research is public-web only. Licensed sources, including ACLED, are not a dependency and must not be used.
- Output is English. French input has limited support and may be handled as source material; it does not change the output language.
- Use only approved historical, synthetic, or otherwise non-sensitive material. Do not submit confidential operational packages.

## Local operation

Use the project virtual environment from the repository root:

```powershell
# Tests
.\.venv\Scripts\python.exe -m pytest -q

# Lint
.\.venv\Scripts\python.exe -m ruff check .

# Local MVP server
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
```

To export a completed review, use the interface's **Export Word note** action. The equivalent endpoint is `GET /api/reviews/<assessment_id>/export.docx`; it is available only while that volatile review session remains active.

## Incident stop

If a non-sensitive-input, policy-boundary, registry, or unexpected-output concern arises, stop the local server immediately, do not retry the review with the same material, and do not export or share the result. Preserve no raw source content, model output, secrets, or user corrections in issue reports. Record only the safe error category and escalate through the applicable internal process.

## Development

Project-specific commands and the expanded safe-use boundary are documented in `CLAUDE.md`. The executed MVP validation record is in `docs/validation/2026-08-10-mvp-validation.md`.
