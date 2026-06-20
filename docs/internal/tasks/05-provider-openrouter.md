# Task 05 — Provider: OpenRouter

> **Phase 1** · depends on: 03, 04 · Reference: `IMPLEMENTATION_PLAN.md` §12.2 (row 1), §13 (Provider 1), §2.3

## Objective
Implement the first, simplest provider. OpenRouter is fully OpenAI-compatible — this is the reference implementation other providers copy.

## Files to create/modify
- `src/providers/openrouter.py`

## Detailed spec
- Subclass `BaseProvider`.
- Base URL `https://openrouter.ai/api/v1`; auth `Authorization: Bearer <key>`.
- `chat()`: POST `{base_url}/chat/completions` with the OpenAI body. Map gateway `model` id → `provider_model_id` (e.g. `nemotron-3-ultra` → `nvidia/nemotron-3-ultra-550b-a55b:free`) via the registry.
- Pass through OpenAI params (temperature, max_tokens, top_p, penalties, stop, stream). Support both non-streaming and streaming (stream handled fully in task 08; here at least wire the flag).
- Translate provider response → unified `ChatResponse` (§2.3), set `provider="openrouter"`.
- Error mapping → `ProviderError(code=...)`: HTTP 429→"429", 5xx→"5xx", 401→"401", 404→"404", httpx timeout→"timeout".
- `list_models()`: return registry models for provider_id `openrouter` (optionally cross-check `GET /models?max_price=0`).
- `check_health()`: tiny chat ping; map status per §10.

## Notes (sequencing & data realism)
- **API key source:** the key comes from `.env` (`OPENROUTER_KEY`); `key_manager` bootstraps `.env` → encrypted SQLite at startup (task 13). Never hard-code keys. A minimal `provider_id → class` factory in `src/providers/__init__.py` should exist by this task (task 15 extends it) so routes/router can resolve OpenRouter.
- **Model IDs:** the §13 catalog is forward-dated and some ids may not resolve live. Before asserting a live call, verify each `provider_model_id` against OpenRouter's live free-model list. Treat schema/translation correctness (mockable) as the **hard** acceptance; live calls best-effort.

## Acceptance criteria
- [ ] With a valid key, a non-streaming chat returns a schema-valid `ChatResponse` with `provider="openrouter"`.
- [ ] 429/401/timeout produce `ProviderError` with correct `.code`.
- [ ] Gateway model id correctly maps to OpenRouter's `:free` provider_model_id.
- [ ] `check_health()` returns one of the §10 statuses.

## Review checklist
- Header auth correct; no key logged.
- id→provider_model_id mapping uses the registry, not hard-coded duplicates.
- Response envelope matches §2.3 (id pattern, usage block, finish_reason enum).
