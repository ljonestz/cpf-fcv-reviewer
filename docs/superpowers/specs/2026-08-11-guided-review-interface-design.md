# Guided CPF FCV Review Interface Design

**Date:** 2026-08-11
**Status:** Approved direction, pending written-spec review
**Scope:** Usability and presentation refinement for the existing local MVP

## Objective

Make the CPF FCV Reviewer immediately understandable to a first-time, non-technical user while retaining the familiar visual language of the FCV Project Screener. The interface must remain simple, require only essential inputs, and keep analytical detail available without placing it all on screen at once.

The stable FCV Project Screener remains a separate service. This work may echo its restrained World Bank/FCV visual language but must not modify, integrate with, or depend on that service.

## Chosen approach

Use a guided single-page intake followed by a dedicated results view. The intake form and results are separate interface states; completed results do not appear beneath the landing form.

This approach was selected over:

- a multi-step wizard, which adds clicks and navigation state for a short intake; and
- a split-screen workspace, which is denser and less obvious to occasional users.

## Landing view

The landing view has one purpose: help the user start a review confidently.

### Information hierarchy

1. A plain-language title: strengthen the FCV framing of a CPF or CEN.
2. One sentence explaining that the tool provides an evidence-linked advisory review and practical options.
3. A compact three-step cue:
   - add the draft;
   - add context; and
   - review findings and options.
4. The intake card.
5. A concise advisory and volatile-storage notice.

### Inputs

Show only three essential inputs by default:

- country;
- review stage; and
- primary CPF or CEN file.

Place supporting documents, analysis guidance, and detected priority questions inside one clearly labelled optional disclosure. Do not add new required inputs or introduce a wizard.

Use plain helper text, mark required fields with an asterisk, and provide one primary action: **Run FCV review**.

## Progress and transition

After submission, replace the intake card with a focused progress view. Show the current phase in plain language and retain the advisory boundary. Do not expose internal step names, raw errors, model details, or source content.

On completion, replace the progress view with the dedicated results view. Browser history and refresh behaviour must not create durable storage; the existing volatile assessment identifier remains session-only.

## Results view

The results view should read like a short review note rather than a technical dashboard.

### Primary content

Present content in this order:

1. executive judgment;
2. diagnostic heading;
3. findings;
4. practical options;
5. responses to confirmed priority questions, when present; and
6. limitations.

Each finding is a simple card with a plain sensitivity label. Supporting evidence is collapsed by default and expands to show only the validated document locator and excerpt. Practical options show the target location without technical metadata.

### Actions

Keep three clear actions:

- **Export Word note**;
- **Add a correction**; and
- **Start a new review**.

Adding a correction opens a compact correction area within the results state. The rerun remains visibly labelled as based on user-provided correction and returns to the dedicated results view. Starting a new review performs the existing reset-and-purge action before returning to the landing view.

## Visual system

Use the existing restrained FCV/World Bank-inspired visual language:

- deep navy header and primary actions;
- cyan accent for progress, section cues, and selected states;
- white cards on a pale neutral background;
- dark, high-contrast body text;
- generous spacing and short line lengths; and
- familiar sans-serif typography.

Avoid decorative imagery, dense dashboards, icon-heavy navigation, excessive badges, modal chains, or animation. The visual relationship to the stable screener is stylistic only.

## Accessibility and responsive behaviour

All controls require explicit labels, visible focus states, keyboard operation, and meaningful status announcements. Colour is not the only carrier of meaning. The three-step cue may stack on narrow screens, and paired fields become a single column. Results remain readable without horizontal scrolling.

## Failure and empty states

Use the existing safe failure labels. Explain what the user can do next without exposing exception text. An unreadable document returns the user to a recoverable intake state. Missing optional material is described as a review limitation, not as a blocking error.

## Verification

Add or update tests for:

- essential-versus-optional intake controls;
- landing, progress, and results state transitions;
- dedicated results rendering without the intake form;
- recommendations, priority responses, and limitations;
- expandable validated evidence;
- correction rerun and new-review reset;
- keyboard-accessible controls and status regions; and
- narrow viewport layout.

Complete a synthetic browser smoke test covering the full path and confirm no console warnings or errors.

## Out of scope

This refinement does not add production identity, operational SharePoint access, durable storage, analytics, deployment, or any connection to the stable FCV Project Screener. Render deployment remains Task 16 and requires separate action-time approval.
