# Approved registry bundles

The running application must fail closed unless it receives an unexpired,
owner-approved, non-confidential registry bundle. Synthetic bundles are permitted
only under `TESTING=true` and live only in `tests/fixtures`.

Do not derive policy language from model memory. Do not copy confidential source
documents into this repository. Before a Render deployment, record the approved
bundle owner, immutable version, approval date, expiry date, checksum, and the
policy-sensitive regression result. If the owner-approved bundle is unavailable,
do not create or deploy the Render service.
