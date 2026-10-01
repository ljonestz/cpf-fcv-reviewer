# Provider-free gates and frozen Guinea acceptance - 2026-10-01

The owner accepted the staged sequence: close available provider-free gates, assess one
country, inspect it, and stop paid testing on failure. This authorizes one further local
assessment, not another batch or a hosting change. The four earlier renewed admissions
remain consumed. Application candidate is `a1f12f58fea780dd6230338801652e8351edf65c`;
its exact-head CI passed, with unchanged application source from the 1,715-test candidate.

## Provider-free acceptance

| Check | Evidence and result | Scope limit |
| --- | --- | --- |
| Persistent state, quota and backup restoration | Actual SQLite app reinitialization and native backup restore passed; review, uploaded bytes, events, assistant history, Word ZIPs and exhausted four/day quota persisted. | Local rehearsal; live hosting remains deferred. |
| Browser interruption and recovery | Target-source-guarded Edge run passed 6/6, one submission, same saved review restored in progress and completed; Word download saved and ZIP checked. | Edge offline emulation retained its established local stream. A local EventSource request abort exercised interruption handling; physical network loss is unverified. |
| Browser cleanup | Context, browser, Playwright, local server and worker all stopped; runner exited normally with no failure. | A prior wrong-worktree probe is excluded. Earlier interrupted records are preserved. |
| Word visual layout | Native Word read-only renders: current synthetic summary 1 page/detail 2 pages, historical Guinea summary 2 pages/detail 12 pages. All 17 pages inspected: readable, intact margins, usable headings/recommendations, no clipping or blank pages. Header/footer text and page numbers verified on every page. | Historical Guinea is a layout fixture with known factual defects, not new quality acceptance. |
| Artifact integrity | Root verified browser screenshot/download hashes, DOCX ZIP, PDF/page-image hashes and unchanged input DOCX hashes. Current detailed export visibly separates quote, source and analysis. | Layout is verified in installed Word 16, not every office suite. |

New ignored evidence is under `output/20261001_provider_free_closure/`:
`20261001_free_gate_signoff.json`, `browser-recovery-04/20261001_browser_recovery_04_target.json`
and `word-layout-04/20261001_word_layout-06.json` / `20261001_word_layout-07.json`.
No application edit or provider call was required to close these gates.

## Input set fixed before the new assessment

Reuse the verified public World Bank downloads in the repository's existing
`20260930_production-stress-test/sources/` corpus. Their bytes were checked again.

| Role | Filename | Physical pages | SHA-256 |
| --- | --- | --- | --- |
| Primary | guinea_cpf_fy27-33_strategic-overview.pdf | 7 | 69b57311a2a19a835cbe450d97e635ec6c50c1e6362b220585c90d2c9d05ecaa |
| Package | guinea_cpf_fy27-33_results-framework.pdf | 5 | 0ebebc2fa700ec54993342e17c595f758ce4e03676932df4197043ceeceffa85 |
| Diagnostic | guinea_rra_2023.pdf | 102 (101 readable previously) | 111e2a7883dadde3a15bb66947bb44cf8c3a691e590c8c84bdb6e3bdc4e30fed |

Official provenance remains in the saved corpus's `research/download_verification.json`.
Review stage: Decision Review. Registry: approved public v1.1.0 with all four Strategy shifts.
No special focus instruction to steer the model around known failures.

## Acceptance criteria fixed before submission

| Gate | Pass condition |
| --- | --- |
| Admission and completion | Exactly one new submission reserved in the existing ledger; existing SQLite counters retained; four/day and normal two/client/hour limits active. Complete within existing input/call/output bounds; no automatic replacement assessment. |
| Provenance and input | Runtime imports and assets resolve to the frozen worktree; actual release, registry and prompt versions recorded; all readable primary/package pages and diagnostic mapping coverage accounted for. |
| Source ownership | Every RRA CPF response is an exact verified quotation from its own cited primary/package evidence, or the allowed absence statement. Separate analysis must not attribute government prosecutions or other unsupported actions to CPF delivery. |
| References | Inspect every priority's source filename, physical page, exact anchor/excerpt and cited evidence; no invented or ambiguous repaired locator. |
| Dates and current context | RRA date is June 2023. Constitutional referendum and election are treated as separate events with source-supported dates. Undated/unverified current observations remain qualified in browser and both exports. |
| Recommendations | No invented numerical thresholds/commitments, including illustrative percentages. Proposals acknowledge existing provisions and are feasible for Decision Review and WBG roles. |
| Analytical coverage | All four approved Strategy shifts considered; sensitivity and active adaptation distinguished; gaps tied to Guinea and supplied sources, with no material contradiction between summary and detail. |
| Experience | Accepted result persists across refresh, desktop/mobile wraps, source/analysis separation is readable, both existing export paths work, no JavaScript errors. Reuse this result for further UI/export checks. |

Application validation alone is not factual acceptance. Inspect the accepted result against
the source documents before any further paid work. If the case fails, retain only safe
codes, allowlisted diagnostics and UI evidence; never inspect/save rejected model content.
One successful case would not close the historical Chad/Tajikistan/Afghanistan reliability
gaps or the deferred live durable-hosting gate. Routine production acceptance remains pending.
