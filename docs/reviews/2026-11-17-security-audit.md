# Security Audit — duels-analyzer-1
Date: 2026-11-17
Agent: opencode (glm-5.3)
Repo: duels-analyzer-1
Scope: secrets, .gitignore hygiene, duplicate checkout

## Findings

| Severity | Finding | Where | Fix |
|---|---|---|---|
| medium | `.gitignore` contains no `.env`/secret entries at all. No `.env` exists on disk today and no secrets are tracked or in history, but a future `git add .` would commit any dropped secret file. | `.gitignore` | add `.env`, `.env.*`, `!.env.example` |
| low | This checkout duplicates `duels-analyzer` with a **diverged HEAD** (this one: cfcc6aa…) — likely the stale copy. | sibling directory | confirm which is canonical, delete the other |

## Checked out clean

- No secrets in tracked files or full git history; no Docker default violations.

Cross-ref: host-level summary at `/home/ubuntu/AUDIT-2026-11-17.md`.
