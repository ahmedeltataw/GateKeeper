# 🖥️ Dashboard Architecture — Streamlit Control Panel

> **Status:** 📝 Planned · not yet implemented
> **Decision date:** 2026-06-18
> **Supersedes:** the in-app Jinja dashboard (`src/api/dashboard.py` + `templates/dashboard/`) — see §6 Migration.
> **Reference spec:** `docs/plan/IMPLEMENTATION_PLAN.md` §16 (Admin Dashboard), §9 (key storage), §10 (health).

---

## 1. Decision

Build the admin dashboard as a **standalone Streamlit app** that talks to the gateway over its
existing HTTP API. Chosen by the project owner over Next.js and over evolving the current Jinja
dashboard.

**Consequence that drives this whole design:** Streamlit runs as a **separate process on a
separate port** (default `8501`). It is *not* served by FastAPI and shares no memory with the
gateway. Therefore the dashboard can only read/write gateway state through **HTTP endpoints**.
Several of those endpoints do not exist yet and must be added to the backend (see §3). This is the
main engineering cost of the Streamlit choice and the bulk of the new tasks.

```
┌────────────────────┐         HTTP/JSON          ┌─────────────────────┐
│  Streamlit app     │  ───────────────────────▶  │  FastAPI gateway    │
│  localhost:8501    │   admin API (Bearer +      │  localhost:8000     │
│  (dashboard/)      │   admin token)             │  src/api/*          │
└────────────────────┘  ◀───────────────────────  └─────────────────────┘
        │                                                   │
   browser UI                                       SQLite + registry + health
```

---

## 2. Top-level layout (flexible, module-per-file)

The Streamlit app lives in its **own top-level package** `dashboard/`, mirroring the project's
"one file per concern" principle so new pages drop in without touching existing ones.

```
dashboard/
├── app.py                  # Streamlit entrypoint: auth gate + page router
├── config.py               # reads GATEWAY_URL, ADMIN_TOKEN from env/.env
├── api_client.py           # thin typed wrapper over the gateway admin API (httpx)
├── components/             # reusable UI widgets (no business logic)
│   ├── __init__.py
│   ├── metric_cards.py
│   └── tables.py
├── pages/                  # ONE FILE PER PAGE — add modules here, nothing else changes
│   ├── __init__.py
│   ├── 01_overview.py      # requests, tokens, provider statuses
│   ├── 02_keys.py          # add/remove provider keys (masked)
│   ├── 03_models.py        # registry view + classification
│   └── 04_analytics.py     # latency, tokens, per-provider breakdown
├── requirements.txt        # streamlit, httpx, pandas, plotly — ISOLATED from gateway deps
└── README.md               # how to run the panel
```

**Why this is "future-proof":** a new module = a new file in `pages/` + (maybe) one new method in
`api_client.py` + (maybe) one new endpoint in the backend. No restructuring; `app.py`'s router
auto-discovers `pages/` (Streamlit native multipage convention).

> Dashboard dependencies stay in `dashboard/requirements.txt`, **never** added to the gateway's
> root `requirements.txt`. This preserves the gateway's "lightweight" principle and keeps the
> hermes/uv environment conflict surface small.

---

## 3. Backend admin API (new — required by Streamlit)

Because Streamlit cannot reach in-process functions, add a small **read-mostly admin router** to
the gateway, mounted under `/admin` and guarded by a bearer **admin token** (separate from the
`sk-local` chat key). All JSON, all consumed by `api_client.py`.

| Method | Path | Returns / Body | Backs page |
|--------|------|----------------|-----------|
| `GET`  | `/admin/stats` | `{requests_total, requests_last_hour, cache_hits, fallback_count, uptime_seconds}` | Overview |
| `GET`  | `/admin/providers` | `[{id, status, last_checked}]` (from `health.get_all_statuses()`) | Overview / Analytics |
| `GET`  | `/admin/keys` | `[{provider, masked:"●●●●●", health_status}]` (no plaintext) | Keys |
| `POST` | `/admin/keys` | body `{provider, api_key}` → `key_manager.set_key` | Keys |
| `DELETE`| `/admin/keys/{provider}` | `key_manager.delete_key` | Keys |
| `GET`  | `/admin/models` | `[ModelInfo…]` from `registry.all_models()` | Models |
| `GET`  | `/admin/analytics` | per-provider `{requests, tokens, avg_latency_ms}` | Analytics |

Auth: `Authorization: Bearer <ADMIN_TOKEN>`. Token set via `.env` (`ADMIN_TOKEN=…`); if unset,
`/admin/*` returns `403` and the panel shows a setup hint. Reuses the existing `AuthMiddleware`
pattern — add an admin-token check branch, do not weaken the chat auth.

**Backend gap to fix in passing:** `src/api/dashboard.py:182` calls
`key_manager.get_key_metadata()`, which does not exist (key_manager exposes
`set_key/get_key/delete_key/list_providers_with_keys/update_health`). The new `/admin/keys`
endpoint must use the real API (`list_providers_with_keys` + a small metadata read), and the old
broken call is removed with the Jinja dashboard (§6).

---

## 4. Auth model

- **Panel login:** Streamlit gate using the same scrypt-hashed password already stored in
  `dashboard_auth` (SQLite). The panel verifies by calling a new `POST /admin/login` that returns a
  short-lived session token, OR (simpler MVP) the panel itself holds the `ADMIN_TOKEN` from its env
  and only renders after a local password prompt. MVP picks the env-token approach; password-login
  via endpoint is a documented later module.
- **Transport:** admin token in `Authorization` header on every `api_client` call.
- **Never** render or log plaintext API keys; keys are masked server-side before they leave the
  gateway.

---

## 5. Run model

Two processes, two commands (documented in `dashboard/README.md`):

```bash
# 1) gateway (existing)
uv run uvicorn src.api.server:app --host 127.0.0.1 --port 8000

# 2) dashboard (new, isolated venv)
cd dashboard && uv run streamlit run app.py    # serves http://localhost:8501
```

`GATEWAY_URL=http://127.0.0.1:8000` and `ADMIN_TOKEN=…` come from `dashboard`'s env. Optional
`docker-compose` service `dashboard` can be added later (out of MVP scope).

---

## 6. Migration: old Jinja dashboard

The existing in-app dashboard is **deprecated** once `/admin/*` + Streamlit reach parity:

| Item | Action |
|------|--------|
| `src/api/dashboard.py` | Keep until parity, then **reduce** to just `init()` + scrypt auth helpers reused by `/admin/login`; remove HTML page routes. |
| `templates/dashboard/*` | Delete after parity (no longer served). |
| `static/css/style.css` | Delete or move into `dashboard/` if styles are reused. |
| `dashboard.enabled` (config) | Repurpose to gate the `/admin/*` router. |
| `key_manager.get_key_metadata` bug | Fixed by not relying on it; remove caller. |

Do **not** delete anything until the Streamlit panel verifiably covers that page (tracked per task
acceptance criteria).

---

## 7. Scope boundaries (MVP)

**In:** the 4 pages above, admin API, env-token auth, isolated deps, run docs.
**Out (later modules, drop-in):** live log streaming, request replay, model enable/disable toggles
from UI, password-login endpoint, docker service, charts beyond basic latency/tokens.
