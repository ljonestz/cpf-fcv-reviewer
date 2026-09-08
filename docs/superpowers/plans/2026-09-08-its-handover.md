# ITS handover implementation plan

Goal: deliver the user-approved focused cleanup and Markdown plus Word ITS guide.

Architecture: retain the src package and runtime asset locations. Remove generated package metadata from version control, clarify current versus historical documentation, and preserve unique local development work.

- [x] Confirm GitHub baseline and repository access.
- [x] Update README, documentation navigation and ITS handover.
- [x] Stop tracking generated egg-info and ignore development artifacts.
- [x] Remove only confirmed disposable local cache/temp files; preserve unique work.
- [x] Generate the matching Word handover using the selected System Design template.
- [x] Verify links, package discovery, provider-free smoke tests and document rendering.
- [x] Commit, push and open a reviewable PR without changing app hosting.

The owner explicitly approved the original-checkout switch. The repository root now uses codex/its-handover; the original modified CLAUDE.md is preserved in the ignored local archive.
