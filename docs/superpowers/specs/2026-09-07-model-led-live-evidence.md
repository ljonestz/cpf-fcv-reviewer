# Model-led live evidence for CPF assessment

Approved by the user on 7 September 2026. The benchmark is the usefulness of a research-enabled LLM reviewing the CPF, with traceable sources and expert judgment.

## Design
Use CPF priorities and country context to focus broad public research. The existing model normalization call assesses source quality and FCV relevance; do not require specific FCV nouns and verbs. Admit credible institutional, reporting and analytical sources beyond the publisher catalogue when the quotation is grounded in a provider citation. Known publisher identity must match its host. Identify uncatalogued sources by host and disclose limited provenance verification. Wikipedia, social content and licensed data remain excluded. Do not broaden server-side metadata fetching to arbitrary hosts.

Keep source URLs, quotes, country attribution and date checks application-owned. Known unsuitable sources must not crowd out useful ones before normalization. A normalization fallback may retain source-grounded excerpts with qualified confidence; it cannot silently invent semantic relevance or claim full verification. Keep model-only background visibly distinct from retrieved evidence.

Use semantic relevance and its explanation to connect evidence to CPF objectives, delivery mechanisms, affected groups and practical revisions. A source reports a fact; the review explains the implication. Do not make a bibliography or claim count the success criterion.

## Validation
Regressions cover council capture without keyword matches, non-FCV material explicitly assessed irrelevant, credible sources outside the catalogue, fabricated quotes, publisher spoofing and Wikipedia. Run focused tests, the full provider-free suite and smoke. Then use bounded live research to inspect retained evidence and CPF relevance before a full public Guinea assessment. Kenya and Haiti test generality; they do not substitute for CPF-specific quality assessment. Compare final output qualitatively for concrete CPF links, useful revisions, traceable claims and appropriate uncertainty. Do not claim measured parity with native chat without a direct comparison.
