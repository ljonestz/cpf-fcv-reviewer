# Registry-controlled referral repair

Approved by the owner on 6 October 2026: app-controlled removal of unapproved
structured referral IDs, preserving approved original referrals and unrelated content.
This is a shared repair change, with no country-specific conditions.

The runtime already validates referrals against IDs from the integrity-checked registry
bundle. Pass that same allowlist to `ReviewEngine.repair`. Only when the supplied
issue set includes `unknown_institutional_referral` and an authoritative allowlist
is available, replace the repaired referral tuple with the original tuple filtered
to approved IDs. Preserve original order and multiplicity; never adopt model-added
IDs, infer aliases, or reconstruct registry language. None means unavailable, distinct
from an explicitly empty allowlist. Without an allowlist retain the existing fail-closed
validation behavior. All other validation, evidence, row identity and policy controls
remain. No extra model calls, retries, model changes or deployment settings.

Acceptance: test both diagnostic modes, retained unknowns, omitted approved originals,
model-added approved/unknown IDs, absent and empty allowlists, issue-gating, unchanged
review content, runtime registry wiring, and a retained policy failure. Run focused
unit/runtime tests then the full provider-free suite, smoke and independent review.
A further provider-backed assessment requires explicit authorization after the fix
is concrete and verified; the failed assessment must not be restarted automatically.
