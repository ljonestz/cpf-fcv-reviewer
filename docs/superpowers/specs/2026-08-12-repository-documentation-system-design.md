# Repository Documentation System Design

## Goal

Create a durable, low-maintenance documentation system that lets a future human or agent understand the CPF FCV Reviewer, operate it safely, verify its state, and resume work without reconstructing history from chat logs.

## Source-of-truth hierarchy

1. `README.md` is the concise public entry point.
2. `CLAUDE.md` is the authoritative instruction set for coding agents and future development sessions.
3. `docs/README.md` is the documentation index and reading order.
4. `docs/PROJECT_STATUS.md` records the current implementation and deployment state.
5. `docs/SESSION_HANDOFF.md` is the single living pickup note and an explicit exception to the normal no-overwrite rule.
6. `docs/ARCHITECTURE.md` and `docs/OPERATIONS.md` define stable technical and operational knowledge.
7. `docs/DECISIONS.md` is an append-only decision log.
8. Dated specifications, plans, validation records, and handoffs are immutable historical evidence.

When documents conflict, code and executable tests establish implementation behavior; the most recent dated validation record establishes what was actually verified; `PROJECT_STATUS.md` states the present interpretation.

## Documentation components

### Public entry point

Update `README.md` with the project purpose, public-versus-internal boundary, safe-use constraints, quick start, live-prototype status, and links into the documentation system. It must remain concise and must not expose secrets, assessment identifiers, internal OPCS content, or raw model output.

### Agent instructions

Update `CLAUDE.md` with a mandatory session-start reading sequence, repository map, architecture invariants, verification commands, documentation maintenance rules, and the prohibition on changing the stable FCV Project Screener.

### Canonical knowledge pages

- `docs/ARCHITECTURE.md`: components, request lifecycle, storage lifecycle, API surface, trust boundaries, key-file map, and testing map.
- `docs/OPERATIONS.md`: local setup, configuration names without secret values, registry integrity, Render deployment verification, rollback principles, validation workflow, and incident stop.
- `docs/PROJECT_STATUS.md`: dated current state, completed work, latest verified commit, deployment caveats, limitations, and prioritized remaining work.
- `docs/SESSION_HANDOFF.md`: branch, last verified commit, worktree condition, most recent checks, immediate next actions, and authoritative links. Future sessions update this file in place.
- `docs/DECISIONS.md`: append-only records for decisions that must not be silently reversed.

### Historical evidence

Create a dated Render/Benin validation record without embedding public source text, model output, live assessment identifiers, or secrets. Mark the earlier local MVP validation record as historical and link to the newer record. Index existing Cowork/registry handoffs without modifying their contents.

## Maintenance protocol

Every substantive session must:

1. Read `CLAUDE.md`, `docs/README.md`, `docs/PROJECT_STATUS.md`, and `docs/SESSION_HANDOFF.md` before changing code.
2. Verify branch and worktree state instead of trusting the handoff blindly.
3. Update `PROJECT_STATUS.md` when capabilities, deployment state, limitations, or priorities change.
4. Update `SESSION_HANDOFF.md` at the end of the session.
5. Append to `DECISIONS.md` only for durable architectural or governance choices.
6. Add a new dated validation record for meaningful validation; never rewrite historical results except to add a clear supersession pointer.
7. Keep documentation claims tied to a commit and an executable verification result.

## Safety boundaries

- The public prototype remains separate from the stable FCV Project Screener.
- Public documentation may identify the approved public guardrail bundle and checksum, but must not contain internal OPCS policy content.
- Never document secret values, deploy hooks, raw uploaded content, raw model responses, correction text, or volatile assessment identifiers.
- The separate internal ITS version remains a future, separately governed track.
- External validation artifacts remain outside Git; repository records contain safe summaries and paths only where appropriate.

## Verification

Documentation changes must pass link/path review, contradiction and placeholder scans, `git diff --check`, the full Python test suite, Ruff, and JavaScript syntax validation. A final independent review checks technical accuracy, pickup usability, and information-safety boundaries.
