# MVP validation record

## Scope and status

This record documents validation of the local, advisory CPF FCV Reviewer MVP. It is not a production-readiness assessment and does not authorize operational use, deployment, or connection to the stable FCV Project Screener.

- Validated commit: `13bf771`
- Validation timestamp: 2026-08-11 17:12:11 Europe/Paris (UTC+02:00); 2026-08-11 15:12:11 UTC
- Pre-documentation repository state: `git diff` and `git status --short` were clean.

## Verification status

| Check | Exact command and result |
| --- | --- |
| Tests and coverage | `$env:TASK15_COVERAGE_FILE='C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\20260811_task15_final_coverage.sqlite'; $env:COVERAGE_FILE=$env:TASK15_COVERAGE_FILE; .\.venv\Scripts\python.exe -m pytest --cov=cpf_fcv_reviewer --cov-report=term-missing --cov-fail-under=90 -q -p no:cacheprovider --basetemp 'C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\20260811_task15_final_temp'` — 297 passed; 94.79% coverage. |
| Ruff | `.\.venv\Scripts\python.exe -m ruff check --no-cache src tests` — passed. |
| JavaScript syntax | `node --check src\cpf_fcv_reviewer\static\app.js` — passed. |
| Secret scan | `rg -n --hidden -g '!*.docx' -g '!*.pdf' -g '!docs/superpowers/plans/**' -g '!docs/validation/**' '(ANTHROPIC_API_KEY\s*=\s*[^$]|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-ant-|password\s*=)' .` — `NO_SECRET_PATTERN_MATCHES`. The excluded plan and validation paths contain literal audit patterns; this validation document was manually reviewed. |
| Diff integrity | `git diff --check` — passed. |

A separate documentation-agent rerun using a worktree-local temporary directory failed because that environment denied temporary-directory and Coverage database creation. That non-authoritative environmental failure does not replace the successful release result above.

## Synthetic validation inputs

Automated validation used synthetic fixtures only: `synthetic_en.txt`, `synthetic_fr.txt`, and `synthetic_mixed.txt`. No raw fixture content, source content, model output, secrets, or user correction text is recorded here.

## Executable adversarial-scenario inventory

The original plan requires the following scenarios. Every named scenario has executable coverage; this inventory records exact test names and safe outcomes without reproducing test payloads.

| Plan scenario | Executable test(s) and asserted outcome | Status |
| --- | --- | --- |
| Direct SharePoint original versus derived copy | `test_direct_sharepoint_original_beats_derived_markdown`; `test_direct_original_wins_and_ambiguous_originals_abstain`; `test_runtime_resolve_sources_prefers_direct_original`: direct current original is selected; ambiguous originals abstain. | Covered |
| No RRA, limited framing, and grouped priority questions | `test_no_rra_uses_limited_mode_and_grouped_diagnostics_without_alignment_rating`: forces limited framing, retains grouped diagnostics and responses, and rejects alignment ratings. | Covered |
| Strong narrative with weak results framework, and inverse | `test_contrasting_narrative_and_results_framework_gaps_remain_distinct_and_traceable`: retains both contrasts as separate traceable findings. | Covered |
| Uncertain regional and cross-border country relevance | `test_uncertain_cross_border_relevance_is_retained_as_cautious_confirmation_with_limitation`: retains cautious confirmation and a limitation. | Covered |
| Scanned PDFs, dense tables, incomplete extraction, unsupported figures | `test_empty_pdf_pages_dense_docx_tables_and_inline_figures_are_preserved_or_warned`: preserves table locators and emits missing-text and figure warnings. | Covered |
| English, French, and mixed input; English output; French evidence excerpts | `test_synthetic_language_fixtures_cover_english_french_and_mixed_inputs`; `test_review_output_is_always_english`; `test_french_evidence_remains_verbatim_while_review_output_is_english`; parameterized `test_complete_synthetic_local_workflow`: enforces English output while preserving evidence excerpts. | Covered |
| Prompt injection in upload and user guidance | `test_uploaded_and_guidance_prompt_injections_are_isolated_as_untrusted_content`; `test_review_prompt_treats_documents_and_guidance_as_untrusted_content`: treats both channels as untrusted content rather than instructions. | Covered |
| Stale, malformed, unapproved, or tampered registry bundles | `test_synthetic_bundle_is_allowed_only_in_tests`, registry invalid-content/date tests, `test_runtime_rejects_registry_hash_mismatch`, and `test_registry_loader_rejects_a_tampered_or_wrong_expected_hash` reject unavailable, invalid, test-only, expired/invalid-date, and mismatched-hash bundles. | Covered |
| Public-source disagreement, missing dates, licensed ACLED | `test_public_contradiction_is_retained_with_its_qualifying_relationship`; `test_unsafe_or_incomplete_current_context_sources_are_rejected`; `test_rejects_claims_requiring_licensed_data`: retains disagreement as qualification and rejects incomplete or licensed-data claims. | Covered |
| Restricted, sensitive, and highly sensitive excerpts | `test_sensitivity_categories_are_explicit_and_withheld_recommendations_are_not_drafting_advice`; `test_withheld_content_is_not_rendered_as_draft_language`: preserves sensitivity handling and blocks withheld drafting advice. | Covered |
| Timeout, schema failure after one repair, source failure, and DOCX failure | `test_failure_event_exposes_only_a_stable_error_code`; `test_invalid_repair_is_attempted_once_then_fails_without_partial_result`; `test_source_failure_exposes_only_stable_safe_event_code`; `test_docx_rendering_failure_returns_only_a_safe_error`: returns stable safe failures without partial or sensitive output. | Covered |
| Concurrent sessions, expiry, reset, and cross-session access | `test_two_concurrent_sessions_remain_isolated`; `test_expired_session_is_purged`; `test_reset_removes_active_review`; `test_unknown_assessment_id_returns_safe_expired_response_without_creating_state`: preserves isolation and returns a safe 410 for unknown IDs. The MVP has no identity layer, so this tests identifier isolation rather than authenticated authorization. | Covered |
| Logging attacks using raw text, filenames, corrections, or findings | `test_raw_filename_correction_and_generated_finding_are_not_written_to_application_logs`; `test_log_redaction_never_returns_content`; `test_metadata_never_retains_raw_content`: excludes the named content classes from logs and metadata. | Covered |
| Policy determinations | `test_determination_language_is_blocked`, `test_determination_language_is_case_insensitive`, and `test_determination_patterns_do_not_match_obvious_substrings` block determinations without false substring matches. | Covered |
| Finalization overreach | `test_finalization_overreach_is_rejected_by_full_review_validation` and `test_finalization_rejects_wholesale_redesign` return the stage-overreach validation issue. | Covered |
| User steering | `test_hostile_user_steering_cannot_bypass_policy_or_stage_validators`: hostile steering remains subject to policy and stage validators. | Covered |

## Browser smoke

Recorded manual synthetic smoke evidence states that, on desktop, the purpose and all three steps were visible; exactly country, review stage, and primary document were visible by default; optional inputs were initially hidden and expanded from the disclosure; submission hid the intake and showed the workspace; and completion showed the dedicated final-results view. Evidence expanded, practical options and limitations were visible, a correction rerun returned to results, DOCX download triggered, and reset restored the landing view. The recorded browser console had zero warnings and zero errors. At 640px, the steps and fields stacked with no horizontal overflow. This documentation update did not rerun the browser smoke.

## Known limitations

- Validation used synthetic fixtures and fake adapters.
- No operational SharePoint access or live-model validation was performed.
- Output is English; French input support is limited.
- Storage is volatile and limited to one process.
- The registry used for validation is synthetic and is not a production approval.
- The MVP has no identity layer; unknown assessment identifiers receive a safe 410, but authenticated authorization was not validated.
- LibreOffice was unavailable: DOCX received a structural audit and browser-download check, but no visual render.
- No Render deployment was created or validated.
