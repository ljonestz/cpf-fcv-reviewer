# Paid-run reliability release on 3ab6020 - 2026-09-03

## Scope and outcome

This release makes the controlled expert pilot more cost-conscious and reliable. The
default recent-news research path now makes one paid attempt before using the existing
curated institutional recovery path. One accepted recent item from a trusted source is
sufficient; the wider evidence target remains guidance rather than a hard submission
gate.

The release also fixes final repair normalization so model-cleaned RRA and FCV Strategy
narrative fields are not replaced by the original prohibited wording. Structural fields,
identifiers, evidence links, statuses, and confidence remain application-controlled.

## Verification

- Complete provider-free suite: **1,252 passed**.
- Final targeted configuration, repair, and smoke suite: **147 passed in 2.37 seconds**.
- Complete external smoke-browser runner: `BROWSER_QA_PASS screenshots=8
  assistant_messages_restored=4 docx=1`, with no console or page errors.
- Smoke DOCX integrity: 39,400 bytes, 19 ZIP entries, required OOXML parts present.
- `git diff --check`: passed; working tree was clean before integration.
- Pull request 3 merged to `main` as `3ab6020548c60206ea344a1b9808ae26e1906642`.
- Render deploy `dep-dacre6gn74is738peoeg`: live on the same commit.
- Public checks: `/health` returned `status=ok` and the exact release; `/` returned HTTP
  200 with the expected application title.

Synthetic smoke artifacts are gitignored under
`output/playwright/2026-09-03-paid-run-reliability-smoke-5c1711c/`.

## Remaining acceptance gate

No additional paid assessment was submitted in this release cycle. The deployed build
still requires one explicitly authorized Guinea paid run to verify real-provider recent
news recovery, final repair behavior, FCV-linked recommendation quality, and the exported
result. Do not resubmit the earlier failed assessment or run more than one paid assessment
for this deployed fix cycle.
