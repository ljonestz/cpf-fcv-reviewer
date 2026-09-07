# Paid research-only probes, 7 September 2026

## Authorization and inputs

The user authorized three bounded probes (Guinea, Kenya, Haiti), followed by a full
Guinea review and deployment only if quality checks passed. Each probe used one
research attempt with the service model `claude-sonnet-4-5`; no knowledge fallback,
curated recovery, complete review, or follow-on assistant call ran.

Guinea used 12,000 characters extracted from the existing seven-page CPF. Its bytes
match the World Bank disclosed PDF exactly: SHA-256
`69b57311a2a19a835cbe450d97e635ec6c50c1e6362b220585c90d2c9d05ecaa`.
Public catalogue: https://documents.worldbank.org/curated/en/099052826164524577
The initial automatic approval review blocked transmission pending provenance;
the byte comparison resolved that concern and the retry was approved before any
model call. Kenya and Haiti used labelled research-only focus questions, not CPFs.

## Results on application commit 0b65e0f

| Country | Candidates | Cited excerpts | Unapproved publisher excerpts | Country mismatches | Accepted current claims |
|---|---:|---:|---:|---:|---:|
| Guinea | 15 | 20 | 20 | 8 | 0 |
| Kenya | 16 | 20 | 20 | 2 | 0 |
| Haiti | 18 | 14 | 7 | 0 | 0 |

Guinea and Kenya ended with no usable normalized claims. Haiti retained three
sources and four claims before the FCV-relevance filter excluded those claims.
All three outcomes were document-led. This is a failed live-evidence acceptance,
not production readiness. No full Guinea review, merge, or deployment followed.

Local results: `output/20260907_183042_live-probes/`. Raw outputs are not committed.
The initial runner printed the correct failure outcomes but did not propagate its
return code to the shell; that runner-only issue is corrected. Initial counters do
not retain rejected URLs/quotations. A diagnostic capture was added to the local
runner to preserve public source metadata and quotes without credentials or requests.
Any additional paid request requires authorization; it is not an automatic retry.
