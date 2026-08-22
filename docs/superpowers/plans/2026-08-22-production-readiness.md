# Production Readiness Implementation Plan

> Follow test-driven development and verify each checkpoint before proceeding.

**Goal:** Make full-document reviews restart-safe and complete enough for production use without changing the established user journey.

**Architecture:** Flask stores expiring assessment payloads in SQLite on a Render persistent disk; a managed single-instance worker executes the existing orchestrator; durable state supports reconnectable SSE and post-restart results/downloads. Local/smoke mode retains in-memory execution.

**Stack:** Python 3.13, Flask, SQLite, Gunicorn, Render Blueprint, pytest, Playwright.

## 1. Persistence and queue contracts

- Add failing store-contract tests for non-destructive cursor events, TTL refresh, lineage deletion, and JSON/byte payload round trips.
- Implement a SQLite session store behind the existing API, field-based and TTL-bound.
- Add failing enqueue-contract tests covering create, retry, correction, and test/local inline behaviour.
- Implement transactional claims, restart recovery, a managed production worker, and an in-process adapter for tests/smoke.
- Verify the focused store/route suite.

## 2. Worker-safe assessment execution

- Add failing tests proving submission does no full extraction and invokes the queue once.
- Move the assessment handler into an app-buildable worker entry point; make status transitions idempotent and persist terminal failures.
- Replace route-created daemon threads with the configured queue.
- Add managed worker lifecycle, stale-job recovery, and bounded shutdown settings.
- Verify routes, orchestrator, app-factory, and end-to-end tests.

## 3. Reconnectable progress and durable download

- Add failing tests for cursor-based replay/reconnect and terminal replay.
- Update SSE to read persisted events without removing them and accept a safe cursor.
- Confirm result and DOCX endpoints can be served by a newly created app instance sharing Redis.
- Verify download headers and the existing temporary-anchor browser behaviour.

## 4. Alignment completeness and title quality

- Add failing review-engine tests for missing Strategy shifts, required RRA rows, evidence-safe fallback, and concise summary titles.
- Narrow the single repair prompt/schema to missing alignment rows while preserving valid narrative and evidence links.
- Deterministically normalize to the four canonical Strategy shifts and explicit `Not Assessable` rows when evidence is absent.
- Normalize/reject overly specific title summaries while retaining detailed actions in priority areas.
- Verify contracts, prompts, review engine, validators, narrative quality, output parity, and DOCX tests.

## 5. Render production configuration

- Add configuration tests for persistent/queue mode, 24-hour production retention, job recovery, and deployed release detection.
- Add a `render.yaml` defining a paid single-instance web service and persistent disk.
- Set health reporting to expose storage/queue mode and Render git commit without secrets.
- Validate the Blueprint and production startup configuration.

## 6. Acceptance validation

- Run the full pytest suite and JavaScript syntax check; record the known Ruff Application Control limitation if unchanged.
- Run deterministic smoke at 1280px and 390px, including upload, progress, result, and DOCX download without page navigation.
- Download a recent official CPF for an FCV-affected country from the World Bank, run a real-provider in-depth review, and check RRA/four-shift coverage and title quality.
- Save the detailed result as HTML and desktop/mobile summary screenshots outside git.
- Restart or redeploy the web service while preserving an accepted/completed assessment, then re-check result and DOCX retrieval.
- Update `docs/PROJECT_STATUS.md` and add a dated validation record.

## 7. Delivery

- Inspect status and staged diff, commit logical checkpoints, push the feature branch, and update PR 2.
- Deploy the Blueprint/services to Render.
- Verify live health/version and repeat the critical browser path before declaring production ready.
