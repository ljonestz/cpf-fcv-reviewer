# CLAUDE.md

## Project scope

This repository contains the CPF FCV Reviewer, an advisory prototype that is separate from the stable FCV Project Screener.

## Commands

- Test: `.\.venv\Scripts\python.exe -m pytest -q`
- Lint: `.\.venv\Scripts\python.exe -m ruff check .`
- Run:  `.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run`

## Safety and policy boundaries

- Do not make unsupported claims about OPCS requirements, endorsement, compliance, or policy.
- Do not directly use confidential policy files; use only approved historical, synthetic, or non-sensitive inputs.
- Do not add durable review storage. Review state must remain volatile and in memory only.
- Do not commit secrets, credentials, API keys, or `.env` files to Git.
- Do not modify, integrate with, or otherwise change the stable FCV Project Screener.

## Worktrees

Use `.worktrees/` as the project-local directory for isolated Git worktrees.
