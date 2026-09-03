# Final controlled pilot gate on 1fd53d7 - 2026-09-03

## Scope and outcome

This record covers the post-review provider-free pilot gate for local code commit
`1fd53d7` on `fix/guinea-production-fixes`. It supersedes
`2026-09-03-controlled-expert-pilot-9baae0c.md` for current local pilot acceptance while
preserving that earlier record as historical evidence.

The post-review fix closes five finalization phrasing bypasses and ensures all-enabled
curated institutional timeout/provider failures propagate to `ResearchController` safe
categories rather than insufficiency. README identifies `a52505c` only as the deployed
baseline. No provider-backed assessment, paid API call, deployment, or push was performed;
the stable FCV Project Screener was not modified.

## Verification

- Complete provider-free test suite: **1,250 passed in 45.94 seconds**, using a unique
  non-OneDrive pytest basetemp.
- Python compilation, JavaScript syntax, and `git diff --check`: passed earlier in the
  coordinating verification.
- Ruff: unavailable because the worktree has no `.venv` and the configured Python 3.13
  runtime has no Ruff module.
- The complete existing external browser runner passed against local smoke mode with:
  `BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1`.
  It covered programmatic upload, result and detailed views, two assistant turns, refresh
  restoration, correction disclosure, mobile summary, and DOCX download, with no
  console/page errors. The local server was stopped afterward.

Artifacts are gitignored under:

`output/playwright/2026-09-03-controlled-pilot-smoke-1fd53d7/`

The folder contains eight full-page PNGs (`20260902-r4-01` through `-07` and `-09`) and
`20260902-r4-08-smoke-full-detailed-note.docx`. The DOCX was inspected as a valid ZIP/
OOXML package: 39,400 bytes, 19 entries, required document/content-type parts present,
40 nonempty XML paragraphs, 40 `python-docx` paragraphs, zero tables, and one section.

## Acceptance and limits

The current local pilot acceptance is provider-free and applies to `1fd53d7`; it does not
establish deployed or paid Guinea acceptance. The last deployed baseline remains
`a52505c74d72bc08d4f973436f8b8204c76b1d0b`. Production deployment, push, and any paid
Guinea run remain intentionally out of scope and unchecked.
