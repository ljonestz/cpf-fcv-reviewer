# Recommendation grounding follow-up - 2026-09-10

## Problem and scope

The paid test on release `3904935` completed technically but generated unexplained numerical targets, overly firm proposed institutional actions, overbroad absence findings, time-sensitive claims exceeding retained evidence and lengthy recommendations. This follow-up implements the owner-approved changes without another provider-backed run.

## Intended behavior

- Reuse numerical targets only when the supplied evidence establishes them. Otherwise recommend indicators, baselines and target-setting rather than inventing quantities or deadlines.
- Distinguish existing commitments from proposed additions requiring feasibility or institutional agreement. Preserve direct, practical recommendations where warranted.
- Recognize relevant provisions already present in the CPF before identifying the precise remaining gap.
- Distinguish event date, publication date and assessment date. A verified historical quote or post-RRA development does not alone establish present conditions or comprehensive coverage.
- Keep recommended actions concise and within stage bounds, without repeating the diagnosis.

The repair remains confined to supplied issues and preserves unaffected content and priority identities. Follow-on assistance must not treat unsupported prior recommendations as primary evidence.

## Verification limits

Provider-free prompt contract tests check the instructions delivered to the model. Payload tests check application-owned date propagation. Neither proves that a live model will consistently make the intended judgments. No deterministic semantic verifier, extra model call, source-age rejection rule, authentication or hosting change is introduced. The deployed paid result remains historical acceptance evidence, not a demonstration of this candidate's behavior.

## Local verification

- New checks first failed for the missing prompt requirements and assessment-date payload, then passed after the edits.
- Focused prompts, review engine, research, follow-on and smoke checks: 356 passed.
- Independent read-only diff review found no blocking contradictions or overrestriction. Its trailing-blank-line finding was corrected.
- New test file passes Ruff. The touched existing Python files retain the same 17 pre-existing lint findings; no unrelated cleanup was included.
- Initial full-suite attempts were blocked by Windows access denial in pytest temporary-directory setup. The provider-free suite was rerun outside the restricted sandbox with a fresh test directory.

- The first completed full run had 1,598 passes, one platform skip and 20 runtime-setup failures caused by an inherited invalid SSL_CERT_FILE. A subsequent run used the previously validated local trust bundle with certificate verification enabled. No application change was made for these environment failures.

- With the valid trust bundle, the full run produced 1,617 passes, one Windows-only Gunicorn skip and one failure in an existing undated-source test that still made a real metadata HTTP request. The request exhausted its deadline. That test now injects an undated HTTP fixture through the existing metadata-client seam; both parameterizations passed (2/2) after the change. Production research behavior is unchanged by this test correction.
