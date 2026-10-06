# Registry-controlled referral repair - 6 October 2026

## Problem and approved change

The early-drafting/in-depth Niger CPF plus RRA quality trial on `c525c9e`
failed with `unknown_institutional_referral` before and after bounded repair.
See the separate [failed-trial record](2026-10-06-niger-rra-release-test.md).
The owner approved app-controlled removal of unapproved structured referral IDs.
This shared fix has no Niger-specific condition and applies in both diagnostic modes.

Runtime passes IDs from the approved registry bundle into repair. Only for the named
referral issue, with an authoritative allowlist, repair keeps approved original IDs
in their existing order and removes unknowns. It rejects model-added IDs, preserves
approved originals the model omits, and leaves unrelated content and validation intact.
Without the allowlist, existing fail-closed behavior remains. No new model call,
retry, model change or hosting configuration was introduced.

Independent review also identified a registry hash/read race: the file was checked
then read again for parsing without the loader's existing hash-verification option.
A synthetic race test reproduced acceptance of changed second-read bytes. Passing
`expected_hash` to the loader now verifies the exact bytes it parses; invalid bytes
still fail closed. The earlier hash/error behavior is preserved.

## Verification

- A local synthetic probe reproduced unknown-reference retention and loss of an
  approved original reference before modification. Actual rejected provider values
  were not inspected or saved.
- Adding the allowlist parameter alone exposed ten semantic regression failures,
  with two boundary cases already passing. Runtime wiring independently failed.
- The hash/read-race test failed before the loader correction.
- All **14 final referral/integrity regression cases passed**, covering both modes,
  omitted/retained/invented references, unavailable/empty registry, issue gating,
  unchanged content and continued policy-language rejection.
- Focused suite before the final loader line: **484 passed**, including all 38 smoke
  tests. Final full provider-free suite: **1,683 passed, one Windows Gunicorn skip**.
- The final Edge QA wrapper checks form settings before submission and persists
  session handoff immediately after creation. Provider-free browser preflight
  finished with exit 0: eight PNGs, two assistant messages restored and two valid
  Word exports. Summary/detail/mobile PNGs were inspected. Local ignored artifacts:
  `output/playwright/20261006-referral-fix-preflight-1`.
- Independent final review found no remaining focused issue; coordinating inspection
  and `git diff --check` passed. New tests and changed source pass Ruff excluding an
  unchanged pre-existing B904 in `review_engine.py`, also reproduced on origin/main.
- Initial sandbox runs could not access pytest-created temporary directories; the
  approved execution context passed the focused and full suites. This was a local
  test-environment issue, not the application failure.

## Release boundary

This record describes a verified candidate. Linux CI, exact deployment and another
provider-backed Niger CPF plus RRA run are separate acceptance steps. No successful
full Niger RRA assessment or real Word export is claimed by these synthetic checks.
A further paid trial requires explicit authorization under the repository validation
ladder. Public-pilot, expert-review and volatile-storage limitations remain.
