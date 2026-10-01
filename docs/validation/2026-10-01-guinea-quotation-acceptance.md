# Guinea quotation acceptance - 2026-10-01

The single further assessment authorized by the owner failed safely on candidate
`a1f12f58fea780dd6230338801652e8351edf65c`. No findings were released. Paid testing
stopped after this admission; no replacement assessment, assistant request, hosting
change, merge or deployment occurred.

The [provider-free gates, input hashes and acceptance criteria](2026-10-01-provider-free-release-gates.md)
were recorded before submission. The actual runtime imported the target worktree,
reported the exact release and used the existing persistent SQLite store. The normal
four/day and two/client/hour limits were active. The existing renewed ledger retains
all four earlier reservations and now contains this fifth reservation; its new allowance
is consumed. Neither the ledger nor quota database was reset.

## Observed result

Submission occurred at 08:53:43 UTC. The browser runner finished normally with exit 1
after 589 seconds overall (approximately nine minutes after submission). Extraction,
source resolution, research, evidence construction, diagnostic mapping and review
generation all completed. Initial validation reported three blocking issues under
`unknown_institutional_referral` and `unsupported_cpf_response`. The single bounded
repair removed the referral issue, but two `unsupported_cpf_response` issues remained.
The application emitted `review_failed` and withheld the review. Advisory issues were
`missing_current_context_support` and `stage_length_overreach`.

The failure establishes that this candidate did not deliver an accepted Guinea review.
It does not establish whether the remaining responses were paraphrases, had incorrect
evidence links, or lost a valid correction during repair. Rejected values, messages and
model output were not retrieved or stored. No accepted JSON, Word exports or assistant
conversation was produced, so the factual, reference and analytical acceptance criteria
cannot be assessed from this case.

Four screenshots, health, browser status and allowlisted event diagnostics are saved
locally under `output/playwright/20260930_renewed_acceptance/runs/quality-09-guinea-reference-candidate/`.
The failure screen was inspected: it explains that no findings were released and that
a new submission consumes another allowance. There were no JavaScript, console or
resource errors. Private assessment identifiers remain in OS temporary storage.

## Provider-free diagnosis

Trace the quotation verification and bounded repair merge paths using synthetic inputs.
Preserve the approved exact-quotation requirement, original driver identity/status,
valid evidence links and call limits. Check whether a valid quoted correction survives
the existing row-identity matching logic. A synthetic reproduction, if found, would
prove that specific code defect; it would not prove the cause of this historical paid
failure. Do not weaken validation, release unsupported findings, or run another paid
assessment to investigate it.

Production acceptance remains unachieved. Cross-country model reliability, the revised
real assistant and the owner-deferred live durable-storage/restart/restore gate remain
open. Word visual pagination and local browser/state recovery now have provider-free
acceptance evidence in the linked record.

## Synthetic identity defect and narrow repair follow-up

Provider-free FakeGateway controls reproduced a code defect after the paid test.
With the same row ID, a verified replacement quote transfers to the original row and
passes the quotation guard. When repair changes the ID but preserves driver text,
`_merge_rra_assessments` appends a second row; the valid quotation survives there but
the invalid original remains. The quote-transfer step only looked up the original ID.
This proves that synthetic defect, not that it caused the paid Guinea failure.

The existing owner-approved identity/quotation design is preserved: only during
`unsupported_cpf_response` repair, restore the original ID when exact driver text is
unique in both original and repaired rows, the original ID itself is unique, and that
ID is absent from the candidate. Quote transfer also requires unique original and
repaired IDs. Ambiguous, changed-driver or colliding-ID cases receive no inferred identity.
The existing merge and literal source verification then transfer only a valid quote
and known evidence links. Original standing and analytical fields remain preserved.
No new dependency, prompt, schema, model call, retry or spending allowance is added.

Five permanent regression cases failed first: duplicated renamed rows and quote
cross-wiring through duplicate original/candidate IDs. After the narrow engine change,
all 143 reference/source/engine tests and 51 smoke/orchestrator tests passed (194 total).
Both ambiguous-driver identity controls remained fail-closed. Independent review found
the ID collision, which was reproduced and guarded before committing the fix.
The saved synthetic comparison is under
`output/20261001_provider_free_closure/quote-repair-diagnosis/`; the paid output remains
uninspected. This local fix still requires fresh model acceptance, which was not repeated.
