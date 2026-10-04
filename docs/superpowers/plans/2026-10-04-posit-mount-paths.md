# Posit mount-path compatibility

**Goal:** Run the existing reviewer below a hosting URL prefix without changing
its provider, access controls, storage or runtime requirements.

**Design:** Flask generates mount-aware assets and returned API links. The browser
uses the server-provided mount prefix for locally constructed API URLs and scopes
saved review identifiers by mount. Empty prefix preserves existing root hosting.
No forwarded-header trust or separate authentication layer is introduced.

- [ ] Reproduce prefixed asset/API and browser restoration/download failures.
- [ ] Update `templates/index.html`, `static/app.js` and `routes.py` with the
  existing Flask URL generator and one browser path helper.
- [ ] Run focused regressions, then a provider-free browser workflow mounted below
  a prefix. Verify root behavior with the existing suite.
- [ ] Commit/push on `feat/posit-connect-compatibility`, recording exact validation
  and remaining server-runtime, storage and model-access prerequisites.

This is one prerequisite for the authorized hosting/integration work, not a live
deployment or model integration. No paid calls or credentials belong in this change.
