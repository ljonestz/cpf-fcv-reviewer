# Local mAI external-research boundary - 4 October 2026

## Approved scope and implementation

The owner approved dedicated local API credentials and removing uploaded document
content from external research. In mAI Desktop mode, the runtime now constructs a
fresh research request containing only the selected country, the application review
date and the fixed holistic research mode. Existing public FCV research instructions
supply the topics. This allowlist applies before primary search, retries and
institutional recovery. It cannot be disabled by review notes or document content.

CPF excerpts, RRA excerpts, document titles, diagnostic dates and review focus are
not supplied to those research paths. Full extraction, the diagnostic map, review
evidence and review notes remain available to the mAI generation path. Research
therefore covers the existing 24-month public-country window instead of a window
tailored to an uploaded RRA. Document-specific comparison remains with mAI.

This restriction applies to both research choices in local mAI mode. The existing
direct-Anthropic public prototype path is unchanged; it must not be described as
keeping uploaded evidence within mAI. No prompt, source-quality, quotation,
reference, locator or date validator was weakened.

## Local credential handling

Use a dedicated Anthropic API key for local research, separate from Render's key.
Where available, use a dedicated workspace with an owner-chosen spending limit.
Keep the durable copy in an approved password manager. For testing, enter it into
a dedicated PowerShell 7 session with:

```powershell
$env:ANTHROPIC_API_KEY = Read-Host 'Paste your Anthropic API key' -MaskInput
$env:RESEARCH_PROVIDER = 'anthropic'
$env:RESEARCH_MODEL_ID = 'claude-sonnet-4-5'
```

The key is then available only to that process and programs launched from it; it
is not automatically available to another terminal, the current Codex tools or an
already running server. Environment variables are not an encrypted credential
vault. Stop the app and close the dedicated terminal after testing. Do not put a
literal key in a command, source file, chat, screenshot or OneDrive-synced file.
No new secret storage dependency or automatic credential retrieval was added.

Retain the previously verified mAI team, interpreter and trusted CA configuration
from the handover. The launcher does not load `.env` files. It checks for the
separate key before Desktop sign-in and starts no assessment on its own.

## Verification and limits

Six synthetic cases failed before the change because the recovery request still
contained uploaded text and review notes. They cover dated RRA, undated RRA and
ordinary context uploads with both local research configurations. After the change,
all 14 hybrid tests passed, including the six new cases. The new tests inspect both
search attempts and the recovery request and verify retained local document evidence.
The broader runtime, research-controller, Desktop and smoke batch passed 380 checks;
two registry tests could not create their temporary directory. Those two passed
after the parent directory was created and verified in the pytest Python process.
`git diff --check` passed. Full Linux suite/name-import lint results are tracked
in draft PR 43. The starting commit was `50a8651` on the existing clean branch.

The initial test command used the existing mAI interpreter, which has no pytest;
the tests ran with the existing workstation test interpreter instead. The first
broader hybrid run also encountered a stale inherited CA path and an incorrect
test expectation about when recognized RRA evidence enters the evidence pack.
Using the existing trusted bundle and checking the retained full diagnostic at
its actual stage resolved those test issues; certificate verification stayed on.

No API key was created, retrieved or stored. No paid research call, Desktop model
call, assessment, quota reset, merge, server restart or deployment occurred.
The running app has not adopted this change. Production readiness remains held,
including the unresolved real Guinea grounding acceptance and hosting gates.
This code boundary does not establish approval for handling confidential inputs.
