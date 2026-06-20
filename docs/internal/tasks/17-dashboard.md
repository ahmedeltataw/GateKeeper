# Task 17 — Admin Dashboard (Jinja) — ⚠️ SUPERSEDED

> **SUPERSEDED 2026-06-18** by the Streamlit direction. This Jinja dashboard is implemented but
> deprecated; it will be retired in **task 24**. New work lives in **tasks 20–24** and
> `docs/plan/DASHBOARD_ARCHITECTURE.md`. Kept here for history/audit only.

> **Phase 4** · depends on: 07, 13 · Reference: `IMPLEMENTATION_PLAN.md` §16, §19

## Objective
A lightweight web dashboard (HTML/CSS/JS, no React) served by FastAPI to manage keys and view stats.

## Files to create/modify
- `src/api/dashboard.py` (routes) + `templates/` (Jinja2) + `static/` (css/js).

## Detailed spec (§16)
- Pages: `/dashboard` (stats: requests, tokens, provider statuses), `/dashboard/keys` (add/remove keys), `/dashboard/models` (registry view + classification), `/dashboard/analytics` (latency, tokens, per-provider breakdown).
- Auth: `scrypt`-hashed password set on first run (store hash, never plaintext). Username from `config.dashboard.username` (default `admin`). Session cookie or basic gate.
- Keys page calls key_manager (`set_key`/`delete_key`/`list_providers_with_keys`); keys shown masked `●●●●●`, never revealed.
- Respect `dashboard.enabled`.
- Stats pull from health/counters (task 14) and registry (task 04).

## Acceptance criteria
- [ ] First run prompts/sets a dashboard password (scrypt-hashed at rest).
- [ ] Login required for all `/dashboard/*` pages.
- [ ] Add a key via UI → encrypted in SQLite (verify ciphertext), usable by gateway.
- [ ] Keys never displayed in plaintext (masked).
- [ ] Models page lists registry; stats page shows provider statuses + counters.
- [ ] `dashboard.enabled:false` disables the routes.

## Review checklist
- Password scrypt-hashed; no plaintext password or API key anywhere in responses/logs.
- Uses key_manager API (task 13), not direct DB writes of plaintext.
- No heavy frontend deps (plain HTML/CSS/JS + Jinja2).
