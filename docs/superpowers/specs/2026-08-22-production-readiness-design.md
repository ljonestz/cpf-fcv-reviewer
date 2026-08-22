# Production Readiness Design

**Date:** 22 August 2026

## Objective

Make the public CPF FCV reviewer reliable for full-length real CPFs: uploads return promptly, reviews survive web deploys and restarts, completed results and DOCX downloads remain available for the configured retention period, and the RRA and all four FCV Strategy shifts are explicitly assessed.

## Constraints

- Keep the existing Flask application, review pipeline, result contract, and browser journey.
- Treat embedded document text as the primary input. Ignore decorative images. Do not add OCR unless a supported document has no usable embedded text.
- Accept only public or non-sensitive inputs, retain them for a bounded period, and never log document content.
- Preserve one bounded model-repair attempt and deterministic safe fallback behaviour.
- Keep local tests and deterministic smoke mode provider-free.

## Architecture

### Fast web intake

The web service validates form fields, filenames, upload sizes, and lightweight file signatures. It stores the payload and returns an assessment ID immediately. Full PDF/DOCX extraction and country verification move to the worker so a long CPF cannot hold an HTTP request open at the Render edge.

The existing country-detection endpoint remains a bounded convenience for the guided UI. A confirmed country is accepted at submission; the worker performs the authoritative readable-document check.

### Durable state and queue

Production uses one private Render Key Value instance through `REDIS_URL`. Assessment payloads, event history, status, results, and traceable evidence share the existing retention TTL. Queue records use a reliable Redis-backed Python worker library so a deploy or worker restart does not silently lose an accepted job. Redis uses `noeviction` and has no public IP allowlist.

Local tests and smoke mode retain the in-memory store. The store and queue are selected by configuration, preserving the current unit-test seam.

The web service only enqueues. A separate Render background worker builds the same runtime services and executes the idempotent assessment handler. Retry requests and correction children use the same queue path.

### Event delivery

Events are persisted with the assessment rather than consumed destructively. The SSE endpoint reads events by cursor and emits keepalives while waiting. A reconnect therefore resumes safely and a second web process can serve the stream. Terminal events remain available until expiry.

### Text-first extraction

The worker uses the existing bounded extractors. PDFs are read from embedded text; images are not rendered or interpreted. DOCX, TXT, and Markdown continue through their existing text extractors. Scanned PDFs with insufficient embedded text fail with the existing safe unreadable-document response rather than triggering expensive implicit OCR.

### Complete RRA and FCV Strategy coverage

The main model result is validated against the available evidence. If RRA rows are required or any of the four Strategy shifts are absent, the single repair call receives only the missing alignment rows, the applicable diagnostic mode, and bounded cited evidence. It cannot rewrite the full narrative.

After that call, deterministic normalization guarantees exactly one row for each Strategy shift. Unsupported rows use the explicit `Not Assessable` status and explain the evidence gap; they do not invent alignment. RRA rows remain tied to identifiable diagnostic drivers and evidence.

Revision-summary titles are short thematic labels. Detailed actions and location suggestions remain in the priority-area fields, not in the title.

### Release and operations

A checked-in `render.yaml` defines the web service, worker, and private Key Value resource with identical analytical configuration. The worker receives a shutdown window and stops taking new jobs on termination. The health endpoint reports the deployed git commit when Render supplies it, plus persistent/volatile storage and queue mode.

## Retention and deletion

All assessment data expires after `SESSION_TTL_SECONDS` (24 hours in production). Explicit reset removes the complete correction lineage and queued jobs where possible. Completed DOCX files are generated from persisted validated JSON/evidence, so no separate long-lived export file is required.

## Failure behaviour

- Invalid or oversized uploads: reject before enqueueing.
- Unreadable/scanned primary document: persisted safe failure code.
- Provider/research failure: existing bounded retry or document-led fallback.
- Worker interruption: queue retry; handler safely replaces incomplete output.
- Missing assessment state: HTTP 410.
- Invalid persisted result/evidence: HTTP 409 without leaking content.

## Acceptance criteria

1. A full real CPF upload returns without an edge timeout and completes in the worker.
2. Restarting the web service during a queued/running/completed review does not lose accepted state or completed downloads.
3. Every successful result contains the four named Strategy shifts; RRA alignment is explicit when an RRA/equivalent is available.
4. Summary titles are concise themes rather than detailed drafting instructions.
5. DOCX download does not navigate away from the results page.
6. Desktop (1280px) and mobile (390px) flows pass in-browser.
7. Automated tests, deterministic smoke, real-CPF quality run, health/version, and retention checks pass before deployment is accepted.
