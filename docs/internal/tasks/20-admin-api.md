# Task 20 — Backend Admin API (`/admin/*`)

> **Phase 5** · depends on: 13 (key_manager), 14 (health), 04 (registry), 16 (cache)
> Reference: `docs/plan/DASHBOARD_ARCHITECTURE.md` §3–§4, `IMPLEMENTATION_PLAN.md` §16.1

## Why this task exists
Streamlit runs as a **separate process** and cannot call gateway functions in-memory. It needs
HTTP/JSON endpoints. This task adds them. It is the prerequisite for all other dashboard tasks.

## Files to create/modify
- `src/api/admin.py` (new) — `APIRouter` mounted at `/admin`.
- `src/api/server.py` — include the admin router when `config.dashboard.enabled`.
- `src/api/middleware.py` — allow admin-token auth on `/admin/*` (do not weaken chat auth).
- `src/core/key_manager.py` — add a small `get_key_metadata(provider_id) -> dict | None`
  (reading `health_status`/timestamps) to replace the broken call referenced below.

## Endpoints (all JSON; bearer `ADMIN_TOKEN`)
| Method | Path | Backed by |
|--------|------|-----------|
| GET | `/admin/stats` | health counters + `cache.get_hits()` |
| GET | `/admin/providers` | `health.get_all_statuses()` |
| GET | `/admin/keys` | `key_manager.list_providers_with_keys()` + `get_key_metadata()` — masked, no plaintext |
| POST | `/admin/keys` | body `{provider, api_key}` → `key_manager.set_key()` |
| DELETE | `/admin/keys/{provider}` | `key_manager.delete_key()` |
| GET | `/admin/models` | `registry.all_models()` |
| GET | `/admin/analytics` | per-provider `{requests, tokens, avg_latency_ms}` |

## Detailed spec
- `ADMIN_TOKEN` read from env/`.env`. If unset → all `/admin/*` return `403` with
  `{"error":"admin token not configured"}`.
- Auth: `Authorization: Bearer <ADMIN_TOKEN>`; mismatch → `401`.
- Keys are masked (`●●●●●`) **server-side**; plaintext keys never appear in any response or log.
- Respect `config.dashboard.enabled` (repurposed to gate `/admin/*`).

## Bug to fix
`src/api/dashboard.py:182` calls `key_manager.get_key_metadata()` which does **not** exist.
Implement that function in `key_manager` (used by `/admin/keys`); the old caller is removed in
task 24.

## Acceptance criteria
- [ ] `GET /admin/providers` returns live statuses with a valid token; `401` without; `403` if token unset.
- [ ] `POST /admin/keys` stores an encrypted key (verify ciphertext in SQLite) and it is usable by the gateway.
- [ ] No endpoint ever returns a plaintext API key.
- [ ] `key_manager.get_key_metadata()` exists and is unit-coverable.
- [ ] `dashboard.enabled:false` disables `/admin/*`.

## Review checklist
- Admin auth is a separate branch from chat `sk-local` auth; chat path unchanged.
- Uses existing `key_manager`/`health`/`registry`/`cache` APIs, no direct plaintext DB writes.
- No secrets in logs.

## Out of scope
Streamlit UI (task 21–22), password-login endpoint (later module).
