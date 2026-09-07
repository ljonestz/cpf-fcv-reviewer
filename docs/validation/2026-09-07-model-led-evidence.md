# Model-led live-evidence validation

## Motivation and method
The user approved replacing exhaustive publisher and keyword gates with model-assessed relevance and source quality. Acceptance requires useful, traceable evidence linked to the CPF; passing technical tests alone is insufficient.

An additional authorized Guinea research-only diagnostic on d227b60 returned 17 candidates and 22 source-linked excerpts. Two dated Africa Center for Strategic Studies excerpts survived source validation but both failed the lexical FCV gate. Their topics were constitutional control and appointments to councils. Mongabay and BTI were also discovered outside the catalogue; Wikipedia comprised much of the other material. This supports replacing lexical decisions and broadening credible provenance, while excluding unsuitable discovery results before they consume the source budget.

The diagnostic also reported one normalization failure. This counter covers no accepted normalized claims as well as malformed output; it does not establish that the provider returned no structured content. No full review or deployment followed that diagnostic.

## Branch validation in progress
New controller regressions first failed five cases: semantically relevant governance evidence in three country requests, semantic rejection overriding keyword matches, and retention of grounded contextual excerpts. After replacing the lexical gate, the controller and provider-free smoke tests passed: 189 tests. Existing negative relevance tests now carry an explicit model relevance decision instead of relying on vocabulary.

Source-acceptance regressions, combined validation and live acceptance are in progress. No claim of parity with a native research-enabled LLM has been measured. Raw probe artifacts remain local and are not committed.

Public input provenance was rechecked before the planned assessment. The Guinea RRA is byte-identical to the World Bank catalogue PDF at https://documents1.worldbank.org/curated/en/099062823201039550/pdf/P176518079e36c0a109c7b0cab5df8028b9.pdf (SHA256 111e2a7883dadde3a15bb66947bb44cf8c3a691e590c8c84bdb6e3bdc4e30fed). The CPF's public provenance and SHA256 are recorded in 2026-09-07-paid-source-probes.md. Review-prompt, prompt-guardrail and narrative-quality tests passed: 61 tests.

## Subsequent source and browser checks
The complete provider-free suite passed 1,516 tests before the final punctuation-fallback regression. The exact browser runner passed synthetic preflight with eight screenshots, one assistant response restored after refresh, and both Word exports. The summary screenshot was visually inspected; no layout defect was apparent.

At the initial 90-second attempt budget, Guinea and Kenya timed out after discovery. Haiti completed with four findings from United Nations, IRC and UNICEF sources. The attempt budget was increased to 180 seconds within the existing 300-second total bound, without adding calls. Subsequent Guinea discovery found HRW, BTI and Amani Africa; normalization still returned no usable claims. Replaying those saved public citations through normalization, without repeating search, retained three dated findings from HRW and Amani with CPF-specific relevance. This replay is not a fresh end-to-end research pass. Kenya retained one normalized Crisis Group excerpt but initially discarded it for lacking a publication date. Offline replay now retains that excerpt as explicitly undated, unverified contextual reporting, not proof of current conditions.

The final robustness change removes a single-sentence punctuation requirement from exact-quote fallback and recognizes HRW/Amnesty publisher identities across countries. Unknown credible publishers continue through model-assessed provenance; the catalogue is not exhaustive. Explicit model quality rejection cannot be reversed by fallback, and fabricated or swapped quotations are rejected. After that change, 411 focused source/controller/smoke tests passed.

The full provider-backed public Guinea assessment remains the release acceptance gate. No deployment has occurred.

## Candidate checkpoint 9e7eb7e
Final complete suite: **1,517 passed**. Changed production modules and validation scripts pass Ruff; git diff whitespace checks pass. The candidate was committed and pushed to PR24. The full public Guinea CPF+RRA browser submission was rejected by automatic approval review twice, including after the byte-identical public catalogue URLs and hashes were supplied. No full assessment was submitted and no model calls for that full assessment occurred. The review requires the user's explicit authorization for the two-document transfer to the configured Anthropic API. No merge or deployment occurred. The candidate remains ready for that acceptance run; native-chat quality parity has not been established.

## Explicitly authorized full assessment
The user subsequently authorized the public Guinea CPF and RRA transfer and execution. The first browser attempt stopped at country confirmation before submitting an assessment; no review API call occurred. The runner now handles the normal confirmation input. Its exact updated flow passed provider-free smoke, including forced country confirmation, eight screenshots, one restored assistant exchange, and both Word exports. One full candidate assessment was then submitted locally on 03b4601 (application code 9e7eb7e). Final quality acceptance remains in progress.

## Authorized quality outcome and follow-up correction
The single full assessment on candidate 03b4601 failed. Research reached `research_reduced`,
which requires retained dated current-context evidence; it did not take the model-only fallback.
The result was not accepted or rendered. Safe initial repair codes were
`unknown_institutional_referral` and `stage_length_overreach` (four issues total). After the
bounded repair phase, `missing_registry_support` remained (three issues), followed by
`review_failed`. No rejected draft, raw model output, validation messages or values were
retrieved. The exact reason for the missing links therefore cannot be established from the
live content. The assistant follow-up and both Word exports were not reached.

The failure screenshot was captured and visually inspected at local-only
`output/20260907_guinea_quality_confirmed_1945/99-quality-failure-full.png`.
It clearly reports that the review stopped. Public inputs and live IDs remain uncommitted.

A synthetic regression demonstrates a matching defect class: the complete-draft repair
response can discard previously valid priority citations and rewrite unrelated content even
when only length/referral corrections were requested. The local fix projects that mechanical
response onto the original draft: only overlength same-ID actions and the flagged referral
list can change. All original priority evidence, assessment prose, locators, ordering and
other fields remain intact. Broader repair categories retain the existing behavior and final
validation remains enabled. Two regressions first failed and now pass; all **1,519 tests pass**.
No additional paid quality assessment has been started. This candidate is not production
accepted, and native-chat quality parity remains unmeasured.

The independent read-only review identified the same omission risk in a residual
`missing_registry_support` pass. The preservation boundary now covers that pass too:
already grounded priorities remain intact; only supplied registry IDs from the model's
same-ID candidate are added to an unsupported priority. A third regression covers three
omitted grounded priorities, an unsupported fourth priority, and rejection of fabricated
registry/new-source additions. It failed before this extension and passes afterward.
Final complete provider-free suite: **1,520 passed**. A focused command first encountered
the machine's invalid ambient SSL_CERT_FILE; using certifi for the provider-free suite
resolved the environment issue without changing application TLS behavior.

The corrected runner also passed provider-free browser smoke with eight screenshots,
one assistant exchange restored after refresh, and two valid Word downloads. The summary
PNG was visually inspected at `output/20260907_repair_preservation_smoke_2000/`.
Ruff reports only five pre-existing findings in review_engine.py and its existing test file;
the same five were confirmed against HEAD. No new lint findings or whitespace errors.
Production remains release 63b16da, unchanged. Another paid quality run remains pending
explicit authorization; there is no successful candidate quality artifact to export.
