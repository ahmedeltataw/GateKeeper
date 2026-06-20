# Task 14 — Health Checks

> **Phase 3** · depends on: 05, 06 · Reference: `IMPLEMENTATION_PLAN.md` §10, §3.4

## Objective
Periodically probe each provider and expose status to the router and `/health`.

## Files to create/modify
- `src/core/health.py` + wiring in `server.py` (background task) and `routes.py` (`/health`).

## Detailed spec
- Background loop every 30s: for each provider with a key, send a tiny chat ping (`check_health()`), map result per §10: 200→`healthy`, 429→`rate_limited`, 401→`invalid`, 5xx→`error`, timeout→`unreachable`.
- Maintain `PROVIDER_STATUS[provider] = {status, last_check, cooldown_until?, rpd_remaining?}`.
- `get_healthy_providers(model_id)` returns providers for that model whose status is `healthy` (§10).
- Feed `/health` response (§3.4): providers map + `uptime_seconds`, `requests_total`, `requests_last_hour`, `cache_hits`, `fallback_count` (counters maintained in-process).
- Start loop on FastAPI startup; cancel cleanly on shutdown. Don't crash the app if a probe fails.

## Acceptance criteria
- [ ] Loop runs every 30s without blocking request handling.
- [ ] Status values exactly match the §10 set.
- [ ] `/health` reflects live provider statuses and the counters in §3.4.
- [ ] `get_healthy_providers()` excludes non-healthy providers.
- [ ] Shutdown cancels the loop without errors.

## Review checklist
- Probe is lightweight; respects rate limiter so it doesn't burn quota.
- Counters wired (requests_total, cache_hits from task 16, fallback_count from task 10).
- 401 marked `invalid` (manual fix), not retried endlessly.
