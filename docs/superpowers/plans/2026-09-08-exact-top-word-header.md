# Exact Top Edge Word Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reproduce the approved page-edge navy Word header reliably in both exports.

**Architecture:** Keep one default Word header paragraph and extend only its shading
through the side margins. Remove the separately generated even-page header so Word
uses the same default header on every page. Preserve all body and footer settings.

**Tech Stack:** Python 3.13, python-docx, OOXML, pytest, Microsoft Word render QA.

---

### Task 1: Encode and verify the default header

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py`
- Modify: `tests/test_docx_export.py`

- [x] **Step 1: Update the structural test**

Assert zero header distance, negative one-inch horizontal indents, a one-inch first-line
indent, and one default header reference with no even header reference.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `python -m pytest tests/test_docx_export.py -q -p no:cacheprovider --tb=short`
Expected: FAIL on the old quarter-inch distance and even header reference.

- [x] **Step 3: Implement the minimal header change**

Set `header_distance` to zero, retain the existing native paragraph shading and indents,
and remove creation of the separate even-page header.

- [x] **Step 4: Run focused and full tests**

Run the export/parity set and complete provider-free suite. Expected: all tests pass.

### Task 2: Render and accept or revert

**Files:**
- Create locally: `output/20260908_word_exact_top/*.docx`
- Modify: current README, project status, readiness, and validation records

- [x] **Step 1: Generate both Guinea reports from the saved assessment**

Use the current exporter styling against the preserved clean reports; do not rerun the model assessment or overwrite earlier files.

- [x] **Step 2: Render every page in Microsoft Word**

Expected: 3-page short report and 9-page full report with an identical top-edge banner
on every page, no clipping, and unchanged body content.

- [x] **Step 3: Apply the fallback if needed**

If any page differs, restore the plain non-color header and repeat tests and rendering.

- [ ] **Step 4: Merge, deploy, and verify**

Merge through a pull request, deploy the exact main commit, and confirm `/health` reports
that release.
