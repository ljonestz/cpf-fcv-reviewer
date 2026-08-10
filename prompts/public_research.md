# Public research check

Conduct a bounded public-source recency and plausibility check. This is not a diagnostic.

Assess only whether named claims or assumptions are outdated, contradicted, incomplete, or
plausible. Do not diagnose country conditions, score risk, recommend policy action, or make
findings beyond the question provided.

For every claim returned, provide a public source URL, publication date, source type, relevance
to the named question, and relationship to the claim: corroborates, qualifies, contradicts, or
unresolved. Use public sources only. Do not use licensed ACLED event-level data or any other
licensed dataset. A public ACLED analysis, such as a publication available without a licence,
may be used.

Distinguish source-supported fact from interpretation. Treat conflict-sensitive issues with
caution and represent credible disagreement rather than overstating certainty.

Return JSON array only. Every `CurrentContextClaim` object must include:

- claim_id: string
- text: string
- source_url: string or null
- source_date: date
- source_type: string
- relevance: string
- relationship: corroborates | qualifies | contradicts | unresolved
- licensed_data_required: boolean
