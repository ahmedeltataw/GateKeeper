# Task 21 — Streamlit Scaffold + Auth Gate — ✅ DONE (2026-06-18)

> **DONE.** Scaffold built: `app.py` (auth gate + `st.navigation`), `config.py`, `api_client.py`,
> `session.py` (shared auth/client/error). Verified by clean-code-guard; deps isolated via
> `dashboard/pyproject.toml` + `uv.lock`.

> **Phase 5** · depends on: 20 (admin API)
> Reference: `docs/plan/DASHBOARD_ARCHITECTURE.md` §2, §4, §5

## Objective
Stand up the standalone Streamlit app skeleton in a top-level `dashboard/` package with an auth
gate and a typed API client — no page content yet beyond a placeholder.

## Files to create
```
dashboard/
├── app.py              # entrypoint: auth gate, then Streamlit multipage router
├── config.py           # GATEWAY_URL, ADMIN_TOKEN from env/.env (pydantic or os.environ)
├── api_client.py       # httpx wrapper: get_stats/get_providers/get_keys/... with Bearer token
├── components/__init__.py
├── requirements.txt    # streamlit, httpx, pandas, plotly — ISOLATED from gateway deps
└── README.md           # placeholder (filled in task 23)
```

## Detailed spec
- `config.py`: load `GATEWAY_URL` (default `http://127.0.0.1:8000`) and `ADMIN_TOKEN` from env.
- `api_client.py`: one method per `/admin/*` endpoint from task 20; injects
  `Authorization: Bearer <ADMIN_TOKEN>`; raises a clear error if the gateway is unreachable or
  returns `401/403` (panel shows a friendly setup message, not a stack trace).
- `app.py`: simple gate — prompt for the admin password/token locally; only render pages after it
  validates against the gateway (a cheap `GET /admin/providers` call = token check). Use
  `st.session_state` to persist auth within the session.
- **Dependency isolation:** `dashboard/requirements.txt` is separate; nothing here is added to the
  root `requirements.txt`.

## Acceptance criteria
- [ ] `cd dashboard && streamlit run app.py` boots and shows the auth gate.
- [ ] With a valid `ADMIN_TOKEN`, the gate passes and a placeholder home renders.
- [ ] With an invalid/missing token, the panel shows a clear message (no traceback).
- [ ] Gateway-down is handled gracefully (friendly error).
- [ ] No gateway deps polluted: root `requirements.txt` unchanged.

## Review checklist
- `api_client.py` is the only place that talks HTTP; pages never call httpx directly.
- Admin token never printed to the UI or logs.

## Out of scope
Actual page implementations (task 22).
