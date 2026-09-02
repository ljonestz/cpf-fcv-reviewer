# Guinea production-quality validation on a52505c - 2026-09-03

## Scope and methodology

One explicitly authorized provider-backed Guinea assessment was submitted to the public
CPF FCV Reviewer on deployed commit `a52505c74d72bc08d4f973436f8b8204c76b1d0b`.
The run used only the approved public Guinea CPF and 2022 RRA PDFs, selected the
finalization stage, and supplied no accompanying package documents.

The cost-controlled validation sequence was:

1. Verify the complete provider-free suite and provider-visible schema transform locally.
2. Deploy the exact branch head and confirm it through `/health`.
3. Run a visible deterministic smoke assessment covering summary, detailed view, assistant,
   and the download control without provider calls.
4. Submit exactly one paid Guinea assessment in a visible Playwright browser.
5. Reuse the completed assessment for result-contract, evidence-link, event, responsive
   layout, log, and DOCX checks. Do not submit a second assessment.

## Outcome

The assessment completed successfully. It progressed through extraction, public research,
evidence construction, full-RRA mapping, review drafting, application validation, and
rendering, then emitted `run_complete`. The post-drafting Pydantic failure observed on
deployed commit `361fe8c` did not recur.

The successful result contains 58 evidence records, four priority areas, five RRA
driver-to-response rows, and four FCV Strategy rows. All cited evidence identifiers resolve,
RRA citations reach page 56, reproducibility metadata validates, and the six limitations
are explicit. The model identifier is `claude-sonnet-4-5`.

Current public research exhausted the configured attempts without establishing a sufficient
independent baseline. The application correctly used the `document_led` tier and disclosed
that the analysis relies primarily on the submitted CPF and dated 2022 RRA. This is a
truthful limitation, not a silent substitution of old evidence for current evidence.

## Retry, failure, and log evidence

The replayed event stream ended in `run_complete` and contained no `run_failed` or
`repair_failed` event. One bounded application repair began with five issues in the
existing allowlist: `raw_evidence_id_in_narrative` and `stage_length_overreach`. The
repaired result then passed validation.

Render logs for the assessment window contained no `review_run_failed`,
`follow_on_assistant_failed`, traceback, or application error. Exactly one assessment
submission marker was created, and no second assessment was submitted.

## Result and DOCX validation

The result endpoint returned HTTP 200 and passed the current `ReviewResult` contract.
Every evidence mapping key matches its embedded evidence identifier, every referenced
identifier is present, and the character-integrity check found no Unicode replacement
characters.

The DOCX endpoint returned HTTP 200. The 47,218-byte file is a valid ZIP/OOXML package
with all required parts, 91 paragraphs, 21 headings, one section, and no tables. It contains
the required overall, RRA, priority, and limitations headings and does not expose an
evidence register or assistant transcript. DOCX-to-page rendering remains unavailable
because LibreOffice is not installed, so structural rather than page-image acceptance is
claimed.

## Browser and visual evidence

A visible provider-free smoke run completed before the paid submission. The production
runner then programmatically uploaded both approved PDFs in a separate visible Chromium
window. Saved production screenshots cover intake, initial holding, research, mapping,
drafting, validation, summary, detailed analysis, recovered result, and 375-pixel mobile
summary.

The desktop summary and detailed screenshots and the mobile screenshot were opened in the
visible in-app browser and inspected. They show a coherent single-column structure with no
obvious clipping, overlap, broken cards, or horizontal-layout failure.

Artifacts are stored outside the repository at:

`C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\GuineaCPFRRA\20260903_schema_diag_quality_a52505c\`

The folder contains 11 unique PNGs, one submission marker, and the validated DOCX. No raw
model response, input document, secret, or live assessment identifier is tracked in Git.

## QA-runner findings

The paid assessment succeeded, but the reused external runner stopped during post-result
assistant validation because its Playwright `wait_for_function` call used an obsolete
positional-argument signature. A recovery pass then exposed a second stale helper
assumption, `EvidenceLocator.pages`, which the current contract replaced with
`EvidenceLocator.page`. Neither defect affected the application or caused another paid
assessment.

The completed assessment was recovered from safe access logs and validated without
re-uploading documents or invoking the review provider again. The interrupted assistant
turn stored no partial history, confirming the fail-safe persistence behavior. Full
two-turn production assistant acceptance was not completed in this cycle and must not be
represented as passed.

Future paid runners should be exercised against the deterministic smoke service before
submission, use keyword arguments for the current Playwright API, validate against the
current locator contract, and persist the transient assessment handle outside Git as soon
as creation succeeds.

## Substantive quality observations

The output is evidence-linked, Guinea-specific, and substantively connects the CPF jobs
strategy to mining-revenue governance, land tenure, transition risk, social trust, and
institutional commitment. It distinguishes strong One WBG jobs alignment from weaker
anticipation, differentiation, and conflict-sensitive delivery.

Two issues remain for a future provider-free design cycle:

- The three top readouts total 818 words before priority-card content. The Five-minute
  view is therefore longer than its label and should receive an explicit concision budget.
- All four finalization recommendations comply mechanically with the 60-word and
  `fine_tuning` rules, but several propose binding commitments, conditionality, or
  substantial delivery changes. Expert review should decide whether semantic
  stage-calibration needs a narrower validator or prompt rule.

These observations do not invalidate the schema-reliability fix, but they limit claims that
the current narrative is fully production-polished.

## Acceptance conclusion

Production acceptance is established for the repaired review-schema generation path,
result rendering, evidence integrity, and DOCX structural export on `a52505c`. The prior
post-drafting failure is resolved.

Acceptance remains conditional for current-country evidence richness, Five-minute
concision, semantic finalization-stage calibration, two-turn production assistant behavior,
and visual DOCX pagination. Do not run another paid Guinea assessment on this unchanged
deployment.
