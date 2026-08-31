# Guinea production-fix validation record

Date: 2026-08-30

## Scope

This record covers the narrow production fixes and live Guinea browser checks completed
after the 2026-08-30 pilot-reliability work. It records safe operational evidence only.
It does not contain raw model output, document text, credentials, corrections, or live
assessment identifiers.

The stable FCV Project Screener was not modified, integrated with, or deployed through
this repository.

## Verified implementation

| Item | Verified state |
|---|---|
| Final code commit | `9816de4` - narrative-only exact-boundary raw evidence-ID sanitizer |
| Repository instructions | `4515ce5` - API-cost validation protocol |
| Render service | `cpf-fcv-review-prototype` |
| Deployment | Render reported `9816de4` live |
| Health/static check | `/health` returned `ok`; public page returned HTTP 200 and contained the assessment form |

The deployment also includes the preceding fixes for review-progress grammar, compact
timer copy, generated-review guardrails, referral validation, repair evidence context,
bounded mechanical repair follow-up, and DOCX export independence.

## Provider-free verification

| Check | Outcome |
|---|---|
| Focused sanitizer and repair tests | 61 passed |
| Provider-free smoke suite | 34 passed |
| Complete pytest suite | 1,063 passed in 14.93 seconds |
| Python compilation | Passed |
| `git diff --check` | Passed |
| Ruff | Unavailable or blocked by the Windows environment |

Smoke output is synthetic and is not treated as Guinea provider-quality evidence.

## Paid Guinea browser runs

Approved public Guinea CPF and RRA documents were used. Each run used real Chromium,
the deployed public service, manual country confirmation through the supported fallback,
full-page PNG capture, and a separate keep-awake page approximately every four minutes.

The runs progressively isolated repair reliability:

1. Earlier runs exposed missing repair evidence context, unsupported language, referral,
   and stage-length failures.
2. After bounded evidence context and targeted stage-length guidance, the fourth run
   still retained raw-ID, stage-length, and prohibited-language issues after repair.
3. Commit `90f962b` added one internal follow-up model call only for residual mechanical
   guardrail codes. The fifth run began with six validation issues and reduced them to
   one residual `raw_evidence_id_in_narrative` issue before failing closed.
4. Commit `9816de4` added a deterministic exact-boundary sanitizer for known evidence
   IDs in user-facing narrative only. Tests confirm that similar tokens are not altered
   and structured evidence IDs, locators, assessment IDs, priority IDs, and metadata are
   preserved.
5. The explicitly authorized sixth run exercised deployed commit `9816de4`. Extraction,
   source resolution, current-country research, evidence building, and mapping completed.
   The initial generated review then failed Pydantic/schema validation with safe failure
   code `review_failed`. Application validation and the bounded repair phase were not
   reached.

The sixth run was not repeated. Consequently, this record does not claim a successful
final Guinea result or DOCX export.

## Browser artifacts

The sixth run saved these non-overwriting full-page PNGs outside the repository:

- `GuineaCPFRRA/20260830_guinea_attempt6_intake_full.png` (`1440 x 1443`)
- `GuineaCPFRRA/20260830_guinea_attempt6_progress_initial_full.png` (`1440 x 1199`)
- `GuineaCPFRRA/20260830_guinea_attempt6_progress_research_full.png` (`1440 x 1199`)
- `GuineaCPFRRA/20260830_guinea_attempt6_progress_drafting_full.png` (`1440 x 1199`)
- `GuineaCPFRRA/20260830_guinea_attempt6_failure_full.png` (`1440 x 1304`)

No summary, detailed-result, or DOCX artifact exists for that failed run. HTML files are
not treated as screenshot evidence.

## Remaining acceptance limitation

The next step is an engineering fix for the initial generated-review schema failure,
supported by a narrow regression test and the no-cost validation ladder. Only a newly
deployed fix should be considered for another explicitly authorized paid Guinea run.
That run must reach a successful real-provider result, capture full-page summary and
detailed screenshots, download and inspect the DOCX, and confirm that no safe validation
codes remain. Until then, final Guinea provider acceptance is not established and the
prototype is not production-ready.

## Future-run cost protocol

Use the ladder in `CLAUDE.md`: targeted local checks, provider-free smoke, deployed
health/static checks, then at most one paid quality run per deployed fix cycle. Never
rerun unchanged code. If a paid run fails, diagnose only from safe validation codes,
add a regression test, and repeat the no-cost ladder before seeking approval for another
paid run.
