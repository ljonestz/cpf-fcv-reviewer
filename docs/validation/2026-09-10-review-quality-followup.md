# Review-quality follow-up - 2026-09-10

## Scope and baseline

Implementation commit: `3a19740`, on `codex/review-quality`, based on Claude's
`510b85e` (`claude/production-readiness-review-6evrz7`). The owner selected the
remaining review-quality bugs first: diagnostic date provenance and priority loss
in repair. Authentication, hosting, thread configuration and evidence-panel
presentation are unchanged by this follow-up. Nothing was deployed or merged.

## Method and resulting behavior

- Extract the selected diagnostic's publication month from bounded frontmatter:
  physical PDF cover page or an explicit publication statement on the first four
  pages; bounded opening segments for flowing documents. Preserve the supporting
  document location and date quote. Conflicting dates, unreadable covers without
  other publication evidence, filename dates and mission dates do not establish
  publication. File creation metadata is not treated as publication evidence.
- Refresh provenance from the full diagnostic extraction, before research. Carry
  the same application-owned provenance through evidence metadata, review requests,
  repair requests and the stored result. Unknown dates are explicit. Older stored
  reviews without the new optional metadata remain readable.
- Keep month precision. ISO day 01 is a storage convention, not a verified day.
  The review and repair prompts are version 3.0.3. A fatal diagnostic_date_conflict
  check covers explicit English diagnostic-publication date constructions, while
  distinguishing reported-event dates and preventing matches across unrelated
  narrative fields. The existing bounded repair handles this code; a residual
  conflict cannot publish a partial result.
- Reconcile repaired priorities by original identity and order. Restore omitted
  priorities and summary links. Preserve document targets and unaffected evidence;
  allow required evidence repairs to remain subject to validation. Restoring an
  invalid omitted priority deliberately leaves its error visible rather than
  making the error disappear by dropping the priority.
- Preserve corrected dates in RRA/Strategy assessment narrative without accepting
  unrelated evidence changes from the repair. Existing narrow mechanical repair
  handling remains in place.

## Verification

Python **3.13.7**, using the repository's pytest source-path configuration:

```powershell
$env:SSL_CERT_FILE = (& 'C:\WBG\Python313\python.exe' -c 'import certifi; print(certifi.where())')
& 'C:\WBG\Python313\python.exe' -m pytest -q --tb=short -p no:cacheprovider --basetemp <fresh-local-temp-directory>
```

Final result: **1,606 passed, 1 skipped in 89.06 seconds**. The skip is
`tests/test_stream_concurrency.py`: Gunicorn is unavailable on this Windows host.
This follow-up does not claim to revalidate Linux stream concurrency.

- New tests were observed failing before the corresponding fixes: incorrect or
  unsupported diagnostic dates, missing provenance in review/repair requests,
  omitted priorities, altered valid evidence, standalone mission dates, and lost
  corrected assessment-row text.
- Full provider-free smoke runs cover successful date repair with priority and
  summary preservation, and residual date-conflict failure without a published
  result. Both use synthetic documents and stubbed model/research gateways.
- Read-only extraction of the approved local Guinea RRA's frontmatter returned
  **June 2023, cover, physical page 1**. No raw document content or generated
  assessment was saved. This is source-date verification, not a paid live review.
- Ruff comparison against `510b85e` for the changed Python files and the new test:
  **12 existing findings, 12 current findings, no added findings**. The overall
  repository lint gate remains affected by pre-existing debt.
- `git diff --check` passed.

The first local baseline attempt had temporary-directory permission errors and an
invalid inherited SSL_CERT_FILE. The final run used a valid certifi bundle and ran
outside the Windows sandbox with a fresh temporary directory. TLS verification was
not disabled. No application code was changed to accommodate those environment errors.

## Limits and coordination

The date extractor is conservative and text-based; it does not add OCR or establish
publication dates from arbitrary prose. The date guard is not a general factual
verifier. Live model behavior and cross-country analytical acceptance still require
a separately authorized quality run after an appropriate release decision.

Luna max subtasks were dispatched for extraction, repair and a bounded review, but
returned no progress or visible edits before interruption. The coordinating agent
reclaimed ownership, implemented and directly tested the work. No delegated
acceptance or independent review is claimed.

The recorded live release remains the earlier release in PROJECT_STATUS. Public
access protection, repair-independent readiness issues and confirmation of the
inherited evidence panels remain separate work.
