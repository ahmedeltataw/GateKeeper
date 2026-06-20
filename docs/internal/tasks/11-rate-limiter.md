# Task 11 — Rate Limiter (Token Bucket)

> **Phase 3** · depends on: 02, 04 · Reference: `IMPLEMENTATION_PLAN.md` §8

## Objective
Per-provider token-bucket rate limiting with persistence across restarts.

## Files to create/modify
- `src/core/rate_limiter.py`

## Detailed spec
- `TokenBucket` per §8: tracks `rpm/rpd/tpm` (and where relevant `rps/tpd/neurons/concurrent`); `refill()` resets minute bucket every 60s, day bucket every 86400s.
- `RATE_LIMITS` defaults per §8 for all 12 providers (openrouter, gemini, groq, mistral, github_models, nvidia, cerebras, cloudflare, zhipu, huggingface, aion, cohere).
- API: `allow(provider, model) -> bool` (checks + reserves), `consume(provider, tokens)`, `cooldown(provider, seconds)` (None=permanent), `save_state()` / `load_state()` to/from `server/data/rate_limits.json` (path from config `rate_limiter.state_file`).
- Handle the special quotas: groq TPM is the binding constraint; cloudflare neurons; zhipu concurrent=1; mistral rps=1.
- Respect `rate_limiter.enabled` (if false, `allow` always true).

## Acceptance criteria
- [ ] Buckets initialize from §8 defaults.
- [ ] `allow()` returns false when the relevant bucket is exhausted; true after refill window.
- [ ] `cooldown(provider, 60)` blocks that provider for 60s; `None` blocks permanently.
- [ ] State round-trips through `rate_limits.json` (save on shutdown, load on startup).
- [ ] `enabled:false` disables limiting.

## Review checklist
- Limit values match §8 exactly per provider.
- Minute/day refill math correct; no negative balances.
- Concurrent/neurons/rps special cases handled, not silently ignored.
