# ITS handover cleanup validation

Date: 8 September 2026
Source baseline: `2fc2b77` on origin/main; documented app release `27ef3aa`.

## Scope

Documentation and repository hygiene only. No runtime source, prompts, tests, registry content or hosting configuration changed. README now leads to a current ITS guide and documentation index. Generated src/cpf_fcv_reviewer.egg-info metadata is removed from Git tracking; editable installation regenerates it. Local outputs, caches, packaging artifacts and SQLite files are ignored.

Historical design and validation records remain at their original paths to preserve links and provenance. A navigation page labels them as historical. The dated Word handover is a generated, local shareable copy of the Markdown guide, not an application assessment and not tracked in Git.

## Local workspace treatment

Two untracked source snapshots and an untracked historical diagnostic handoff were moved into an ignored .local-archive/20260908_workspace-cleanup folder. The original root CLAUDE.md was copied there before any checkout change. A 6-byte write-test file, root pytest cache and six verified empty output directories were removed.

The registered codex-selected-country-worktree was relocated through git worktree move to .worktrees/selected-country-research. Its files and Git registration were retained. Other worktrees contain unique commits, local changes or ignored outputs and were preserved. The historical Claude_Outputs archive and country assessment artifacts are not part of the ITS source package.

## Verification

- Authenticated GitHub CLI confirmed the repository exists. It was initially private; after the owner made it public during this session, a second check returned visibility PUBLIC and isPrivate false. Guidance was updated accordingly.
- git fetch origin established baseline 2fc2b77.
- Provider-free test command: python -m pytest tests/test_smoke_mode.py -q -p no:cacheprovider — 36 passed in 21.55 seconds.
- Setuptools package discovery returns cpf_fcv_reviewer after removal of generated metadata from tracking.
- Full Ruff check reports 121 findings in unchanged baseline source and tests. These are an existing lint backlog; no lint fixes are included.
- No model-backed assessment or deployment was performed.
- All 18 local links in the new navigation and guide resolved. git diff --check passed. Ignore rules were verified for generated metadata, output and the preservation archive.
