# Task 12 — Sticky Sessions

> **Phase 3** · depends on: 07, 10 · Reference: `IMPLEMENTATION_PLAN.md` §7

## Objective
Keep a conversation on the first successful model for 30 minutes to avoid personality/quality jumps.

## Files to create/modify
- `src/core/sticky.py` (or inside `fallback.py`/`router.py` if cohesive) + wiring in `routes.py`.

## Detailed spec
- `session_cache: dict[str, {"model_id":..., "time":...}]` per §7.
- `get_sticky_model(session_id)` → returns model_id if `time()-entry.time < sticky.ttl` (default 1800s), else None.
- `set_sticky_model(session_id, model_id)` updates entry.
- Session id derivation: stable hash of the conversation (e.g. first system+user message, or a client-supplied header if present). Document the choice.
- Router flow: if sticky model exists and is healthy/in-budget, prefer it before Quality Router selection; otherwise select normally and set sticky on first success.
- Respect `sticky_sessions.enabled` and `context_handoff` flags.

## Acceptance criteria
- [ ] Repeated requests in the same session reuse the same model within TTL.
- [ ] After TTL expiry, a fresh selection occurs.
- [ ] When the sticky model is unavailable, fallback runs and (if `context_handoff`) injects handoff, then updates sticky to the new model.
- [ ] `enabled:false` disables stickiness.

## Review checklist
- TTL default 1800; session id derivation deterministic and documented.
- Interaction with Quality Router + fallback is correct (sticky preferred, not bypassing budget checks).
