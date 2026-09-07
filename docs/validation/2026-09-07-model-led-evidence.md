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
