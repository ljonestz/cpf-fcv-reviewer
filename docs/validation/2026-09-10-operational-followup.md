# CPF operational follow-up - 2026-09-10

## Scope and decisions

The owner deferred authentication for the small shared-link pilot and authorised
remaining review follow-up. No access protection, paid model assessment, deployment,
or stable FCV Project Screener change is included here.

Retain Claude's extraction/archive bounds, recovery and stopped-screen changes subject
to focused checks. Retain gthread with 16 candidate request threads; no gevent migration.
Restore the approved simplified evidence presentation: the 31 August approved design
explicitly removed evidence-status, traceability and per-card evidence disclosures from
the reading flow. Claude's claim that their absence was accidental drift is contradicted
by that design. Structured evidence remains available for validation and assistant grounding.

## Verified live hosting

Render MCP and a no-cost /health request on 10 September established:

- CPF service srv-d9tju52jobas73d6jvk0, main, live commit 2fc2b77.
- Paid 0.5 CPU / 512 MB instance, one instance, auto-deploy on commit.
- Start command still explicitly sets gthread, one worker, four threads.
- Health status ok, storage volatile, queue in_process.
- Two sampled memory readings approximately 106-107 MiB; these idle samples are not a load test.

The paid upgrade has not enabled durable review storage. A 24-hour expiry remains a
maximum retention period, not a restart-survival guarantee. render.yaml describes a
candidate durable deployment with a disk and SQLite path; it is not a live settings dump.
Its auto-deploy and thread settings also differ from the dashboard.

Before releasing the candidate, replace the dashboard start command with:

```text
gunicorn --config gunicorn.conf.py --worker-class gthread --workers 1 --threads 16 --bind 0.0.0.0:$PORT wsgi:app
```

An explicit dashboard --threads 4 overrides the new config-file default even after merging.
The 16-thread mitigation has a bounded pilot capacity; an idle-only 90-second SSE check
is not an unconditional stream lifetime and does not reduce steady-state viewer occupancy.
No production load test was run. Durable storage and restart validation remain a distinct
hosting step, rather than an assumed consequence of paying for the instance.

## Verification

Added GitHub Actions on Ubuntu and Python 3.13 because Windows lacks Gunicorn and WSL
is not installed. The workflow runs the provider-free suite without model credentials.
Initial run 34463939400 on 073d882: 1,607 passed in 27.71 seconds, including Gunicorn.

Strengthened the concurrency test: all eight streams must connect and health requests
must succeed with HTTP 200. Previously a quick OSError/HTTP 503 could pass the latency
assertion. Two targeted regressions failed before the fix and passed afterwards; Ruff
on the changed concurrency test passed. The test reads the candidate Blueprint command;
it does not certify live dashboard settings.

Focused Luna max review identified a worker fallback defect: after a late failure,
_fail_closed could emit run_failed while retaining a saved result and evidence. The
coordinator independently reproduced this with the real SQLite store and result route,
then added cleanup before the terminal failure. The result endpoint no longer serves the
saved review after fallback. The regression failed before the change; nine worker and
persistent-app tests passed afterwards, with Ruff clean on those changed files.
If storage itself remains unavailable, best-effort cleanup still cannot guarantee a
persisted terminal state; this change does not claim to solve a continuing disk failure.

The panel delegate did not return usable progress and was interrupted. The coordinator
implemented the narrow restoration of the approved design. The worker delegate supplied
the finding/reproduction; implementation was completed locally after interrupting it.
No independent final acceptance by a delegate is claimed.

The panel contract failed before the restoration; all 41 frontend contract tests passed
afterwards. The existing browser runner passed in deterministic synthetic mode with eight
full-page screenshots, two restored assistant messages and two valid DOCX downloads.
Artifacts: output/playwright/20260910_operational_smoke (ignored, synthetic only).
The coordinator inspected the detailed desktop and mobile screenshots. No model calls.
The normal image viewer was blocked by Windows Application Control; screenshots were
viewed through a read-only in-memory JPEG conversion without altering the source PNGs.

Implementation checkpoint: ece8880. The strengthened suite on 02561ed passed 1,609 tests
in Linux run 34464319061. The combined implementation ece8880 passed **1,610 tests in 23.32 seconds** on Linux
Python 3.13, including real Gunicorn: [run 34465367930](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/34465367930).
No skipped Gunicorn test remains in this Linux validation. git diff --check passed.
Draft PR 33 now targets main and includes Claude's operational fixes with these corrections;
the unrelated generated egg-info changes have been restored to main's content.

## Remaining acceptance

Research breadth and country-specific proposal feasibility require expert quality acceptance;
no additional fatal presentation checks or broad architectural changes are justified here.
Authentication is owner-deferred. No merge or deployment is claimed by this record.
