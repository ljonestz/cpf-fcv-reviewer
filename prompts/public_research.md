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

Return a strict JSON array only, with no markdown or surrounding explanation. Every object must
contain exactly these fields:

- `claim_id`: unique nonblank string
- `text`: nonblank source-grounded claim
- `publisher`: nonblank publisher or institution name
- `source_title`: nonblank title of the cited source
- `source_url`: public HTTP(S) URL or null
- `source_date`: ISO YYYY-MM-DD publication date
- `source_type`: nonblank source type
- `relevance`: nonblank explanation of relevance to the specified mode and question
- `context_kind`: exactly `structural_dynamic`, `current_development`, `resilience_factor`, or
  `implementation_condition`
- `relationship`: exactly `corroborates`, `qualifies`, `contradicts`, `unresolved`, or `establishes`
- `licensed_data_required`: boolean, and it must be false for every retained public claim
