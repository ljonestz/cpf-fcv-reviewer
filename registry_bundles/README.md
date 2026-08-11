# Approved registry bundles

The running application must fail closed unless it receives an unexpired,
owner-approved, non-confidential registry bundle. Synthetic bundles are permitted
only under `TESTING=true` and live only in `tests/fixtures`.

The public Render prototype uses only the minimal product-owner-approved guardrails
in `cpf_fcv_reviewer_public_guardrails_v1.0.0.json`. This approval is limited to
the experimental public prototype and is not formal OPCS, Legal, or institutional
policy approval. Detailed OPCS-specific content must remain outside the public
bundle and follow a separate internal ITS governance track.

Do not derive policy language from model memory or copy confidential source
documents into this repository. Before deployment, record the approved bundle
owner, immutable version, approval date, expiry date, checksum, and the
policy-sensitive regression result. If the approved bundle is unavailable, do
not deploy the service.
