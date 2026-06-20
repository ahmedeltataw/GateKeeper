# Task 01 — Project Scaffold & Config Files

> **Phase 1** · depends on: — · Reference: `IMPLEMENTATION_PLAN.md` §1, §14

## Objective
Create the project skeleton, dependency manifest, and all static config/template files so later tasks have a place to write code.

## Files to create
- `requirements.txt` — exact contents from §14.4
- `.gitignore` — exact contents from §14.3 (`.env`, `*.db`, `server/data/`, `__pycache__/`, `*.pyc`)
- `config.yaml` — exact contents from §14.1 (server, auth, database, cache, rate_limiter, sticky_sessions, quality_router, providers[12], dashboard)
- `.env.example` — template from §14.2 (do **not** create a real `.env` with secrets; use `.env.example`)
- Package dirs with empty `__init__.py`: `src/__init__.py`, `src/api/__init__.py`, `src/core/__init__.py`, `src/providers/__init__.py`
- `tests/__init__.py`
- Ensure runtime dir exists at startup (don't commit it): `server/data/` is gitignored; create a `.gitkeep` if helpful but keep `server/data/*.db` and json out of git.

## Detailed spec
- `config.yaml` must list all 12 providers with the exact base URLs from §12.2 / §14.1.
- `requirements.txt` versions exactly as §14.4 (fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings, aiosqlite, cryptography, python-dotenv, pyyaml, python-json-logger, jinja2, aiofiles, pytest, pytest-asyncio).
- `.env.example` documents how to generate `ENCRYPTION_KEY` (the one-liner in §14.2) and lists all optional provider key vars as comments.

## Acceptance criteria
- [ ] `pip install -r requirements.txt` resolves with no errors.
- [ ] `config.yaml` parses as valid YAML and contains all 12 providers.
- [ ] `.gitignore` blocks `.env`, `*.db`, `server/data/`.
- [ ] No real secrets present anywhere; only `.env.example`.
- [ ] All `__init__.py` files exist and packages import: `python -c "import src.api, src.core, src.providers"`.

## Out of scope
Any Python logic (loaders, providers) — later tasks.

## Review checklist
- Base URLs match §12.2 exactly (watch the Cloudflare `{account_id}` placeholder).
- No `.env` with real keys committed; `.env.example` only.
- YAML keys/types match §2.2/§14.1 (host string, port int, enums correct).
