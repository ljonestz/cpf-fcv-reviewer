# Local mAI Desktop integration

Approved scope: Desktop DEV testing, Sonnet 4.6, and existing institutional
research with explicit coverage limitations. Hosted Application access remains
outside this implementation. No automatic fallback to a direct paid provider.

Verified prerequisite: the current gateway accepts the Bedrock Converse request
shape, including `outputConfig.textFormat`; the Anthropic `output_config` shape
returned ordinary text and must not be used for this adapter.

- [x] Add failing contract tests for schema handling, safe failures, token refresh,
  local-only configuration, research qualification and provider isolation.
- [x] Implement one Desktop gateway using existing httpx/Pydantic dependencies;
  preserve complete-output and evidence validation. Return follow-on answers as
  one completed chunk until streaming compatibility has been verified.
- [x] Wire an opt-in development provider and loopback launcher. Reuse institutional
  recovery; qualify this research even if it meets the normal source threshold.
- [x] Run focused tests and the provider-free smoke suite; verify local startup.
- [x] Record evidence and remaining real-assessment/hosting prerequisites.

The Desktop SDK remains an optional local dependency. Use its existing environment
without resynchronizing it. Do not store Desktop tokens or commit local labels,
raw assessment content, or downloaded platform instructions.
