# Grounding fix deployment - 2026-09-10

Application release `992c35a0331125aa3963d2cf424a7d5c582391c4` (PR 36) is merged into main and live on the CPF public pilot.

- PR 35 documentation prerequisite merged first. Its squash caused a project-status-only conflict, resolved without changing tested code, prompts or tests. The resolved PR passed CI.
- Main CI run 34475496031: **1,619 passed in 26.90 seconds**, including real Gunicorn.
- The final squash retained a documentation `[skip render]` marker, so automatic deployment was skipped. The owner-authorized release was explicitly deployed through Render to the exact merged commit.
- Render deploy `dep-dah9u5p5efls738l2010` became live at **2026-09-10 12:15:05 UTC**.
- TLS-verified `GET /health`: HTTP 200, status ok, exact release SHA above, in-process queue, volatile storage. Homepage and `/static/app.js` also returned HTTP 200.
- Existing one-worker, 16-thread configuration and paid instance retained. Site stays open without authentication, as requested. No new paid assessment was submitted.

This deploy ships the source-grounded recommendation instructions and explicit assessment dates described in the [implementation record](2026-09-10-recommendation-grounding.md). Live model adherence remains untested on this release; the previous Guinea assessment belongs to release `3904935`. Storage is still volatile and reviews do not survive restarts.
