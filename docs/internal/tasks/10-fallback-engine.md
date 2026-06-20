# Task 10 — Fallback Engine + Context Handoff

> **Phase 3** · depends on: 05, 06, 09, **11** · Reference: `IMPLEMENTATION_PLAN.md` §6, §7 (handoff), §3.2 (extension fields)
>
> ⚠️ **Build task 11 (rate limiter) before this one** — the fallback engine calls `rate_limiter.allow()`/`cooldown()`/`disable()` as core logic, so it can't be meaningfully completed while the limiter is a stub.

## Objective
Implement the 4-tier fallback chain with cooldowns and context handoff injection.

## Files to create/modify
- `src/core/fallback.py`

## Detailed spec
- `COOLDOWN = {"429":60,"5xx":30,"timeout":0,"401":None,"404":None}` (seconds; None=permanent disable).
- `try_with_fallback(request, task_type)` per §6:
  - **Tier 1:** preferred model across all its providers.
  - **Tier 2:** same strength, other models → on success inject context handoff, set `fallback_used=true`, `original_model`, append to `fallback_chain`.
  - **Tier 3:** one strength lower.
  - **Tier 4:** any available model with budget.
  - On `ProviderError`, apply `rate_limiter.cooldown(provider, COOLDOWN[code])`; permanent codes (401/404) disable key / mark model `removed` in registry.
  - If nothing works → raise `AllRateLimitedError` (→429) or `NoHealthyProviderError` (→503) appropriately.
- **Context handoff (§7):** inject a system message at index 1 using the exact template; only on Tier ≥2 switches.

## Acceptance criteria
- [ ] Tier 1 success returns with `fallback_used=false`.
- [ ] Forcing the primary to 429 falls through to a same-strength model with `fallback_used=true` and correct `original_model`/`fallback_chain`.
- [ ] 401 disables the key; 404 marks the model removed.
- [ ] Cooldowns applied with the right durations.
- [ ] Context handoff system message inserted at index 1 on tier ≥2.
- [ ] Exhaustion raises the correct exception → 429/503.

## Review checklist
- Tier order and transitions match §6.
- Handoff template text matches §7 verbatim; inserted after first system message.
- Permanent vs temporary cooldown handling correct.
