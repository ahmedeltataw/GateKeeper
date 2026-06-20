# Task 23 — Run/Deploy Docs + Isolated Deps — ✅ DONE (2026-06-18)

> **DONE.** `dashboard/README.md` + `dashboard/.env.example` written; root `.env.example` has
> `ADMIN_TOKEN`. Deps isolated and **uv-native**: `dashboard/pyproject.toml` (`package = false`) +
> `uv.lock` are the source of truth; `requirements.txt` kept only as a pip/Docker fallback.
> `run_dev.sh` at project root launches backend + dashboard together.

> **Phase 5** · depends on: 21 (scaffold)
> Reference: `docs/plan/DASHBOARD_ARCHITECTURE.md` §5, §2

## Objective
Make the panel runnable by a new user with two commands, and keep its dependencies isolated from
the gateway.

## Files to create/modify
- `dashboard/README.md` — what it is, env vars, run commands, troubleshooting.
- `dashboard/requirements.txt` — finalize pinned deps (`streamlit`, `httpx`, `pandas`, `plotly`).
- `dashboard/.env.example` — `GATEWAY_URL`, `ADMIN_TOKEN`.
- Root `.env.example` — add `ADMIN_TOKEN=` line (used by the gateway's `/admin/*`).

## Detailed spec
Document the two-process run model:
```bash
# gateway
uv run uvicorn src.api.server:app --host 127.0.0.1 --port 8000
# dashboard (isolated env)
cd dashboard && uv venv && uv pip install -r requirements.txt
uv run streamlit run app.py        # http://localhost:8501
```
- State clearly that `ADMIN_TOKEN` must match between gateway `.env` and `dashboard/.env`.
- Troubleshooting: gateway-down, 403 (token unset), 401 (token mismatch), port already in use.

## Acceptance criteria
- [ ] A new user can start gateway + dashboard from the README alone.
- [ ] `dashboard/requirements.txt` is separate; root `requirements.txt` has no Streamlit deps.
- [ ] Both `.env.example` files list `ADMIN_TOKEN`.

## Review checklist
- Commands use `uv run` (matches the project's environment workflow; avoids the hermes venv conflict).
- No secret values committed — only `.env.example` placeholders.

## Out of scope
Docker service for the dashboard (later module).
