# Task 16 — Cache Layer

> **Phase 4** · depends on: 07 · Reference: `IMPLEMENTATION_PLAN.md` §11

## Objective
Add an exact-match response cache to cut duplicate upstream calls.

## Files to create/modify
- `src/core/cache.py` + wiring in `routes.py`/`fallback.py`.

## Detailed spec
- Exact-match key per §11: `md5(json({model, messages, temperature, max_tokens}, sort_keys=True))`.
- TTL default 300s (config `cache.ttl`), `max_size` default 1000 (LRU/FIFO eviction).
- `get(model, messages, params) -> response | None`; `set(...)`. Respect `cache.enabled`.
- **Do not cache streaming responses** (or cache only the fully-assembled final text — pick the simpler: skip streaming).
- Increment a `cache_hits` counter exposed to `/health`.
- Semantic cache is optional/out of scope (note only).

## Acceptance criteria
- [ ] Identical request within TTL returns the cached response without an upstream call.
- [ ] Different params (temperature/max_tokens/messages) produce a different key (miss).
- [ ] Eviction keeps cache at `max_size`.
- [ ] Expired entries (past TTL) are misses.
- [ ] `cache_hits` reflected in `/health`; `enabled:false` disables caching.

## Review checklist
- Key composition matches §11 exactly (sorted keys, those 4 fields).
- Streaming not cached incorrectly.
- TTL/max_size from config.
