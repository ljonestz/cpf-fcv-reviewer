# Controlled expert-pilot hardening design

## Goal

Make the public CPF FCV Reviewer reliable enough for a controlled expert pilot by fixing the observed current-research recovery gap and making every priority recommendation visibly and materially FCV-related. This does not claim ITS production readiness.

## Scope

1. Wire the existing bounded World Bank/ReliefWeb recovery gateway into the production research controller using the configuration already present.
2. Add privacy-safe terminal research classifications that distinguish provider failure, malformed output, rejected sources, insufficient coverage, and budget exhaustion without logging content, prompts, URLs, or identifiers.
3. Strengthen the existing review prompt and `why_it_matters` schema description so every priority states an evidenced direct or indirect FCV causal link and priorities are ordered by FCV materiality, evidence strength, and stage-appropriate actionability.
4. Show the first FCV-link sentence from `why_it_matters` on each Five-minute summary card.
5. Validate that revision-summary links preserve priority-area order and tighten the existing finalization overreach guard for new binding commitments, conditionality, institutional architecture, or delivery systems.

No new recommendation field, dependency, general-news source class, or scoring framework will be added.

## Data flow and behavior

Primary public-web research remains the first route. If it does not establish sufficient admissible evidence within the bounded attempts, the controller invokes the existing curated institutional recovery once within the remaining budget. The result remains `full`, `reduced`, or `document_led`; document-led fallback stays available and transparent.

Review generation continues to use the existing `PriorityArea` contract. The prompt requires the opening sentence of `why_it_matters` to explain how the issue affects an evidenced FCV driver, risk, resilience source, distributional tension, legitimacy concern, conflict-sensitive delivery choice, or relevant FCV Strategy implication. Broader development issues qualify only when this causal connection is explicit. The summary renders that sentence under an `FCV relevance` label.

Priority order is authored by the model and checked structurally: `revision_summary` must link to `priority_areas` in the same order. No keyword score will attempt to rank substantive FCV importance mechanically.

## Error handling and privacy

Research telemetry uses a small allowlist of terminal reason codes and counts only. User-facing prose remains generic. Curated recovery failures do not expose endpoint responses and do not prevent a valid document-led result when uploaded evidence is usable.

Finalization-stage recommendations that introduce major new commitments or delivery architecture enter the existing repair/fail-closed path rather than being presented as fine-tuning.

## Verification and pilot acceptance

- Add focused regression tests for production recovery wiring, safe terminal classifications, prompt/schema FCV requirements, summary order, summary rendering, and finalization overreach.
- Run the focused tests, full provider-free suite, compilation, and `git diff --check`.
- Exercise the complete external QA runner against smoke mode: programmatic upload, result, assistant, refresh restoration, and DOCX download.
- Deploy only the verified commit and confirm it through `/health`.
- Run at most one authorized paid Guinea assessment for that deployed fix cycle.
- Accept the pilot build only when recovery wiring is demonstrably active, every visible priority has a supported FCV link, recommendations fit the selected stage, and the result/assistant/export flow passes.

A transparent `document_led` result remains valid for users, but it does not by itself establish acceptance of the current-research capability.
