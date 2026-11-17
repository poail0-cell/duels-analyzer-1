# Security Audit — duels-analyzer-1
Date: 2026-11-17
Agent: opencode (glm-5.3)
Repo: duels-analyzer-1
Scope: secrets, .gitignore hygiene, duplicate checkout

## Findings

| Severity | Finding | Where | Fix |
|---|---|---|---|
| medium | `.gitignore` contains no `.env`/secret entries at all. No `.env` exists on disk today and no secrets are tracked or in history, but a future `git add .` would commit any dropped secret file. | `.gitignore` | add `.env`, `.env.*`, `!.env.example` |
| low | **Correction (verified 2026-11-17).** This is **not** a duplicate checkout of `duels-analyzer`: it has its own remote (`poail0-cell/duels-analyzer-1`) and its own code (`app.py`/`backend.py` vs the other repo's `main.py`). It is a fork/refactor sharing the upstream README and streamlit URL. | sibling directory | decide which fork to keep, then archive the other |

## Checked out clean

- No secrets in tracked files or full git history; no Docker default violations.

Cross-ref: host-level summary at `/home/ubuntu/AUDIT-2026-11-17.md`.
