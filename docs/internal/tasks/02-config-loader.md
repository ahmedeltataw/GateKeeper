# Task 02 — Config Loader

> **Phase 1** · depends on: 01 · Reference: `IMPLEMENTATION_PLAN.md` §14.1, §2.2

## Objective
Implement `src/core/config_loader.py` to read `config.yaml` + `.env` into a typed, validated config object used across the app.

## Files to create/modify
- `src/core/config_loader.py`

## Detailed spec
- Use Pydantic v2 models (or `pydantic-settings`) mirroring the `config.yaml` schema (§14.1): `ServerCfg`, `AuthCfg`, `DatabaseCfg`, `CacheCfg`, `RateLimiterCfg`, `StickyCfg`, `QualityRouterCfg`, `ProviderCfg`, `DashboardCfg`, and a root `AppConfig`.
- Apply defaults exactly per §2.2/§14.1 (e.g. `temperature` defaults belong to request schema, not here; here: `port=8000`, `cache.ttl=300`, `sticky.ttl=1800`, `auth.enabled=true`, etc.).
- Load order: read `config.yaml`; overlay env vars from `.env` via `python-dotenv` (env wins for `PORT`, `HOST`, `LOG_LEVEL`, `ENCRYPTION_KEY`).
- Expose a singleton accessor `get_config() -> AppConfig` (cached).
- Validate: `port` in 1024–65535; `log_level` in {DEBUG,INFO,WARNING,ERROR}; raise a clear error if `ENCRYPTION_KEY` missing when key manager is needed (defer hard failure to task 13 if simpler).

## Acceptance criteria
- [ ] `get_config()` returns a fully populated object from the repo's `config.yaml`.
- [ ] Env overrides work (set `PORT=9000` → config reflects it).
- [ ] Invalid values (bad port/log level) raise validation errors.
- [ ] `python -c "from src.core.config_loader import get_config; print(get_config().server.port)"` prints `8000`.

## Review checklist
- Defaults match §14.1 precisely.
- Env overlay precedence correct (env > yaml for the documented vars).
- No secrets logged or printed.
