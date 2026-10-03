# Provider-free quotation and policy repair diagnosis - 2026-10-02

The owner authorized diagnosis and repair after the failed Guinea repeat. This work
made no model/provider calls and did not change Render, admission limits or retry counts.
It fixes reproducible application defects in the interaction between policy/date cleanup
and verified CPF quotations. It does not establish the precise cause of the rejected
paid draft, which was not retrieved.

## Method and findings

The review engine, validators, runtime repair caller, prompts and existing regression
tests were traced together. Synthetic drafts were passed through the real repair engine
and source validator with a fixed local gateway. Four new cases failed before the fix;
the existing combined quotation/policy path served as a passing comparison.

| Reproduced defect | Why it matters | Repair |
| --- | --- | --- |
| Policy cleanup copied a valid replacement quotation but retained only the old source links. | A correct quotation from another supplied page became unverifiable in the repaired row. | Transfer quotation and known source links together through the existing exact-source verifier. |
| Policy cleanup could replace a verified quotation with a paraphrase. | Fixing wording created a new quotation failure. | Preserve the original when a replacement is unsupported or comes only from contextual evidence; final validation still blocks unresolved policy wording. |
| Policy cleanup selected a candidate from duplicate row IDs even though quotation repair rejected ambiguous identity. | One repair path bypassed the other path's protection against assigning a quotation to the wrong row. | Require unique original and candidate RRA row IDs before transferring cleaned fields. |
| Policy-only quotation repair received no primary/package source passages. | The model was asked to replace wording without the evidence needed to select an exact alternative. | Supply located primary/package records when policy/date cleanup affects a CPF quotation, within the existing input budget. |

One small shared quotation-transfer helper serves the existing quotation-repair branch
and the policy/date cleanup branch. Existing analysis, status, confidence, valid evidence
links and source-role checks remain. The same rule covers diagnostic-date corrections
because they pass through the same quotation field. Unrelated policy cleanup still
receives no additional document passages.

Repair prompt v3.0.9 now says to select another exact supported passage and keep its
source link when quoted wording is flagged. It explicitly forbids paraphrasing the
quotation or treating quotation verification as an exemption from the policy guard.
The fixed absence disclosure remains limited to already unassessable/absence rows.
Review prompt v3.0.8 and the approved registry are unchanged.

## Public-source control

The verified public Guinea strategic overview contains classification wording on physical
page 5 that matches the existing policy guard. This establishes a real source-selection
conflict the app must handle; it does not identify the wording in the rejected paid draft.

Three local controls used actual page 5 and page 7 passages with synthetic assessment
rows. The verified page 7 replacement retained its citation and cleared the quotation
and policy checks. An unsupported paraphrase and a context-only candidate were rejected,
preserving the original quotation and its unresolved policy failure. These are controlled
repair tests, not a new Guinea assessment or factual acceptance of generated analysis.

The ignored script and JSON are under `output/20261002_quote_policy_repair/`:
`20261002_public_quote_policy_control.py` and its matching `.json`. The source SHA-256
is `69b57311a2a19a835cbe450d97e635ec6c50c1e6362b220585c90d2c9d05ecaa`.
The script guards the imported worktree and records the engine/source hashes.

## Verification

- Seven new engine/source cases cover policy-only and combined repair, unsupported
  paraphrases, context-only evidence, duplicate identities and publication provenance.
  Four failed before the implementation change; the others extend boundary coverage.
- Reference/source/engine/policy checks passed 159 cases before the final two boundary
  cases were added. The final reference/runtime set passed all 173 cases: 171 in the
  corrected local environment and two registry startup tests in an approved unsandboxed run.
- Prompt, smoke and orchestrator checks passed 100 cases. The new prompt contract and
  version checks failed before the prompt update. No browser layout changed.
- All three public-passage controls passed with zero provider calls. `git diff --check`
  passed. Exact code commit `54cdf2a888f0fa6854039b76f230f4751c4f7faf` then passed
  all **1,730** provider-free Linux tests, including Gunicorn concurrency, in 27.12 seconds.
  Python name/import checks also passed in [CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37000380354).

Local test setup initially encountered an inherited invalid certificate setting and
Windows temporary-directory permissions. Tests used the existing trusted CA without
disabling TLS; the two remaining temporary-directory tests passed outside the sandbox.
The local Ruff executable is blocked by Windows Application Control, so its name/import
check is delegated to existing Linux CI. These workstation issues were not application
failures and caused no application/configuration workaround.

## Remaining acceptance

The repaired synthetic controls establish these code defects and their correction.
The earlier paid failure cannot be attributed conclusively to them from safe aggregate
codes alone. Model selection of relevant quotations, unsupported policy wording,
source-target reliability, fresh factual acceptance, the real assistant, cross-country
reliability and owner-deferred durable hosting remain acceptance concerns. No paid rerun,
merge or deployment is implied by this repair. PR 39 remains draft.
