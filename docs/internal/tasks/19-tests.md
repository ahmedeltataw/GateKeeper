# Task 19 — Test Suite

> **Phase 4** · depends on: 09, 10, 11, 15 · Reference: `IMPLEMENTATION_PLAN.md` §1 (tests/), §5, §6, §8

## Objective
Automated tests for the core logic, using mocked providers (no live API calls in CI).

## Files to create/modify
- `tests/conftest.py`, `tests/test_router.py`, `tests/test_fallback.py`, `tests/test_providers.py`, `tests/test_rate_limiter.py`

## Detailed spec
- `conftest.py`: fixtures for a loaded test registry, a fake provider (returns canned `ChatResponse` or raises `ProviderError(code=...)`), and an app/client fixture (`httpx.AsyncClient` against the FastAPI app). `pytest-asyncio` configured.
- `test_router.py` (§5/§9): Quality Router picks strongest task-appropriate model; `model:"auto"` routing; explicit model respected; skips over-budget providers.
- `test_fallback.py` (§6/§10): tier transitions on 429/5xx/timeout; permanent disable on 401/404; context handoff injected at index 1 on tier ≥2; `fallback_used`/`original_model`/`fallback_chain` correct; exhaustion → 429/503.
- `test_providers.py`: OpenAI-compat envelope correctness (§2.3); Gemini request/response translation (§ task 06); Cloudflare translation; error-code mapping.
- `test_rate_limiter.py` (§8): bucket exhaustion/refill; cooldown durations; state save/load round-trip; special quotas (concurrent, neurons, rps).

## Acceptance criteria
- [ ] `pytest` passes locally with no live network calls (providers mocked).
- [ ] Router, fallback, providers, rate-limiter behaviors covered per above.
- [ ] Tests assert schema validity of responses (§2.3) and error envelopes (§3.5).
- [ ] Deterministic (no reliance on wall-clock without fake/controlled time).

## Review checklist
- No real API keys / live calls in tests.
- Fallback tier and cooldown assertions match §6.
- Rate-limiter math assertions match §8 values.
