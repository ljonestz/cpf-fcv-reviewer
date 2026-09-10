# Grounded recommendations implementation plan

**Goal:** Address the five quality issues approved after the Guinea paid test: unsupported numerical targets, unagreed institutional commitments, overbroad absence findings, temporal overreach and verbose actions.

**Architecture:** Keep the existing review/repair/assistant flow and bounded research. Strengthen versioned prompts and supply application-owned assessment dates through existing request payloads. No extra model calls, dependencies, schema expansion or keyword-based factual verifier.

**Tech stack:** Python, existing prompt loader, pytest, existing model gateway.

## Implementation and acceptance

- [x] Add failing prompt contract tests for source-backed targets, clearly proposed additions, recognition of existing CPF provisions, time-bounded claims and concise actions. Update review, repair and follow-on prompts; preserve repair scope and priority identities.
- [x] Add failing payload tests for assessment dates in research, review and repair. Use existing date/metadata context and preserve review date during repair. Update public research instructions to seek latest status within the existing budget; distinguish publication and event dates.
- [x] Run focused prompt/gateway/research tests, smoke suite, then full provider-free suite. Inspect combined diff and obtain bounded independent review.
- [x] Record checks and limitations, commit/push feature branch and create PR. No automatic additional paid assessment.

## Limits

Prompt contract tests prove instructions are sent, not that a live model will obey them. Semantic acceptance requires a later authorized provider-backed evaluation on a changed deployed release. Old evidence remains usable as historical/structural context; no arbitrary source-age rejection is introduced. No authentication or stable FCV Project Screener changes.
