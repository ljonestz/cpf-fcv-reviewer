# Current-country public research

Conduct a bounded, source-linked current-country evidence check. This is not a diagnostic and
must not score risk, recommend policy action, or make policy, compliance, eligibility, clearance,
or endorsement determinations.

The request will specify exactly one mode. Follow that mode and do not combine them:

- `rra_update`: treat the named RRA as the historical baseline, focus on developments after its
  publication date, and re-test whether material structural findings still hold.
- `holistic`: assess structural dynamics and current developments separately when no RRA baseline
  is available. Never call the output an RRA.

Prioritize World Bank and other MDB sources, UN reporting, ICG or a comparable specialist source,
and established public analytics. Use trusted media only for genuinely recent developments. Use
public sources only. Do not use licensed event-level data, including licensed ACLED data. A public
analysis available without a licence may be used when it is otherwise suitable.

Distinguish source-supported fact from interpretation, identify source dates, represent credible
disagreement, and avoid overstating certainty in conflict-sensitive contexts.

Return a concise plain text cited synthesis, not JSON. Use the provider's citations for each
source-grounded narrative segment and preserve source titles, public URLs, and publication dates
when they are available. Keep the synthesis focused on the requested mode and country question.

Do not return a schema, field list, claim IDs, or surrounding JSON. The application will normalize
the cited synthesis into its structured research-claim contract in a separate step.
