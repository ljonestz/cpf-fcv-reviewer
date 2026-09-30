# Production-readiness repair plan

User authorization: address the 30 September audit findings; retain public access;
cap new paid assessments globally at four per UTC day. The existing four-run
validation allowance is exhausted. No further paid acceptance run is authorized.

Use the existing single-instance Flask/SQLite worker design, not a new queue service.
Full readable primary text is required within explicit extraction/model-input limits.
Historical diagnostic conditions must not be presented as verified current facts.

- [ ] CA-01 / OPS-01: bound development execution to one worker; apply serialized
  admission to create, correction and research-retry routes; persist global/client
  quotas in SQLite, bound pending jobs and assistant usage, and cap simultaneous SSE
  viewers. Preserve queued jobs across restarts and fail interrupted paid work safely.
- [ ] CA-02 / CA-05: supply every primary segment without truncation; use the package
  aggregate bounds for package extraction; fail closed on full serialized input
  overflow. Make primary/package readable-text coverage application-owned.
- [ ] CA-03 / CA-04: reject unsupported stages before session/job/provider work and
  log only safe exception types/codes for assistant/export failure paths.
- [ ] CA-06: use actual runtime release, loaded registry version and prompt version
  in metadata, retaining hashes.
- [ ] QA-01 / QA-02: preserve section ownership and real locators, distinguish
  historical conditions from present context, acknowledge existing CPF provisions,
  and prohibit unsupported absence/current-state claims. Add synthetic regressions.
- [ ] QA-03: recognize Gambia title/country variants and cover dates with days;
  retain conservative publication provenance and fail closed on conflicts.
- [ ] UX: provide safe actionable failure guidance and a concise management view
  with the full authoritative measures available in the detailed view.
- [ ] Verify targeted regressions, full provider-free suite, compile/diff checks,
  synthetic browser upload/result/assistant/refresh/export flows and saved screenshots.
  Use Linux CI for Gunicorn stream capacity; exercise SQLite restart/backup restoration.
- [ ] Record issue-by-issue acceptance and remaining operational requirements; commit
  and push reviewed changes, create a PR. Prepare concrete durable Render settings
  before any final deployment approval or missing hosting decision.

Ownership: coordinator owns runtime, engine/validators, routes, admission, worker,
configuration, deployment and acceptance. Luna agents own disjoint diagnostic
recognition, reproducibility helper, and readout/export changes. No stable FCV Project
Screener changes; no internal policy content or raw documents/results in Git.

Checks are test-first for demonstrated defects. Provider-free checks establish
mechanical correctness; they cannot certify new model output quality. Four daily
admissions bound full-assessment starts, not exact dollars; separate assistant caps,
bounded internal calls and provider-account budget controls are necessary.
