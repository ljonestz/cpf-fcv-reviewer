# Country detection repair - approved 6 October 2026

The owner approved adding the two reproduced country-name variants and increasing
the automatic detector's upload budget from 2 to 10 MiB. Scope is deterministic
preflight only; no review/model changes or provider-backed assessments.

The local six-CPF matrix reproduces the report: newer Niger succeeds; Ethiopia's
Federal Democratic Republic name and Guinea's mixed-language cover variant return
no match; Burkina Faso, Somalia and older Niger exceed 2 MiB. Synthetic probes on
live `99cba08` reproduce the name failures and size rejection. The existing 47
country-related tests pass, exposing a coverage gap. An in-memory experiment with
the approved changes detects all six files within unchanged extraction limits.

Add exact registry aliases `Federal Democratic Republic of Ethiopia` and
`Republique of Guinea`. Increase backend and frontend byte limits to `10 * 1024 *
1024`; update the oversized-file message. Preserve the title requirement, bounded
sample, canonical registry and manual confirmation when confidence is low. Keep
16 PDF pages, 256 segments, 100,000 characters, 8 MiB decompressed content and
512 archive members as currently configured. No filename inference or general
country-name guessing. Existing aliases remain supported.

Acceptance: failing alias/real-PDF-size/frontend regressions before implementation;
green focused and full suites; all six real local CPF files detect correctly;
manual entry above 10 MiB remains usable; independent review; Linux CI; exact Render
release verified; production detector-only synthetic checks. No raw documents or
live identifiers committed. Unclear/scanned/unusual titles may still need manual
entry; this is not a guarantee for every CPF layout.
