# Model-led live evidence implementation plan

**Goal:** Retain useful live evidence and support concrete CPF analysis across countries.
**Architecture:** Reuse search and normalization calls, replacing lexical relevance with semantic assessment and extending provenance handling. No new service or model call in the review pipeline.
**Tech stack:** Python, Pydantic, Anthropic SDK, pytest.

- [ ] Add failing source regressions in tests/test_public_research.py, then implement semantic fields and source acceptance in public_research.py. Owned by source_acceptance agent.
- [ ] Add failing relevance regressions in tests/test_research_controller.py, then replace the keyword gate in research_controller.py. Update intentionally obsolete keyword tests to explicit relevance decisions.
- [ ] Update prompts/public_research.md and prompts/review.md to require CPF-specific implications and distinguish source observations from analysis. Run prompt regression tests.
- [ ] Inspect combined diff and run focused tests, Ruff and full provider-free suite plus smoke.
- [ ] Run bounded live probes and inspect evidence quality. Perform a full public Guinea review only after useful live research is established and browser runner passes smoke preflight.
- [ ] Record validation, commit and push branch, update PR24; merge/deploy only after acceptance.
