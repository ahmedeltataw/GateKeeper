# Task 07 — API Server, Routes & Middleware

> **Phase 1** · depends on: 02, 04, 05 · Reference: `IMPLEMENTATION_PLAN.md` §3, §4, §15, §17 (errors)

## Objective
Stand up the FastAPI app with the three core endpoints and middleware. After this task the gateway is runnable end-to-end with at least one provider.

## Files to create/modify
- `src/api/server.py`
- `src/api/routes.py`
- `src/api/middleware.py`

## Detailed spec
### server.py (§15)
- `FastAPI(title="Personal GateKeeper", version="1.0.0", docs_url="/docs", redoc_url="/redoc")`.
- CORS: if `host==127.0.0.1` → `allow_origins=["*"], allow_credentials=False`; else explicit origins + credentials True.
- `@app.on_event("startup")`: `await registry.load()`, `await key_manager.init()` (key_manager may be a stub until task 13 — guard import).
- `@app.on_event("shutdown")`: `await rate_limiter.save_state()` (guard until task 11).
- Register exception handler for `GatewayError` family → 404/429/503 per §17. Define exceptions: `GatewayError, NoHealthyProviderError, AllRateLimitedError, ModelNotFoundError`.
- Allow `python -m src.api.server` to launch uvicorn (host/port from config).

### routes.py (§3)
- `GET /health` (no auth) → §3.4 shape (providers status map can be from health checks or "unknown" until task 14; uptime/counters tracked in-process).
- `GET /v1/models` (+ `?task_type=` filter) → §3.1 list with extension fields.
- `POST /v1/chat/completions` → validate body (§2.2), resolve model (or `auto`), call provider via router (direct provider call acceptable here; full fallback arrives task 10), return §2.3. Honor `stream` (full SSE in task 08).
- `POST /v1/responses` → delegate to chat completions (Codex compat).

### middleware.py (§4)
- `CORSMiddleware` (configured in server), `AuthMiddleware` (Bearer check vs `auth.api_key` when `auth.enabled`; skip `/health`), `LoggerMiddleware` (`{time, ip, model, task_type}`; never log keys/bodies with secrets).

## Notes
- **Keys:** an end-to-end chat needs at least one provider key present in `.env`/`key_manager`. Until task 13 wires encrypted storage, keys resolve from `.env`.
- **Provider resolution:** use the `src/providers/__init__.py` factory (`create_provider`) to instantiate providers; don't import provider classes ad hoc in routes.

## Acceptance criteria
- [ ] `python -m src.api.server` starts on configured host/port.
- [ ] `GET /health` returns 200 without auth.
- [ ] `GET /v1/models` returns the registry list with extension fields; `?task_type=coding` filters.
- [ ] `POST /v1/chat/completions` with a real key returns a schema-valid response through OpenRouter.
- [ ] Auth: missing/invalid Bearer → 401 with `authentication_error` body; unknown model → 404 `not_found` (with available-models hint).
- [ ] Error bodies match §3.5 format.

## Review checklist
- Auth skips `/health` only; everything else under `/v1` protected when enabled.
- Error envelope exactly per §3.5 (`type`, `code`, `param`, `doc_url`).
- Startup/shutdown hooks guard not-yet-built components.
