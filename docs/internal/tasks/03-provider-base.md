# Task 03 — Provider Base Class

> **Phase 1** · depends on: 01 · Reference: `IMPLEMENTATION_PLAN.md` §12.1, §2.2, §2.3

## Objective
Define the shared provider abstraction and the internal request/response data types every provider speaks.

## Files to create/modify
- `src/providers/base.py`
- (optional) `src/core/types.py` for shared `ChatRequest`, `ChatResponse`, `ModelInfo`, `HealthStatus`, `ProviderError` if not co-located.

## Detailed spec
- `ProviderConfig` dataclass: `name, base_url, api_key, models: list[str], rate_limits: dict` (§12.1).
- `BaseProvider(ABC)`:
  - `__init__(self, config)` creates `httpx.AsyncClient(timeout=60.0)`.
  - abstract `async chat(self, request: ChatRequest) -> ChatResponse`
  - abstract `async list_models(self) -> list[ModelInfo]`
  - abstract `async check_health(self) -> HealthStatus`
  - `async close(self)` → `await self.client.aclose()`
- `ChatRequest` / `ChatResponse` types per §2.2 / §2.3 (Pydantic models recommended). Include extension fields on response: `provider`, `fallback_used`, `original_model`, `fallback_chain`.
- `ProviderError(Exception)` carrying a `code` attribute matching the fallback codes (`"429"`,`"5xx"`,`"timeout"`,`"401"`,`"404"`) used by §6.
- A helper for the OpenAI-format envelope (id `^chatcmpl-[a-z0-9]+$`, `object`, `created`, `usage`) so providers reuse it.

## Acceptance criteria
- [ ] `BaseProvider` cannot be instantiated directly (ABC enforced).
- [ ] A trivial subclass implementing the 3 abstract methods instantiates and `close()` works.
- [ ] `ProviderError` exposes `.code`.
- [ ] Response model serializes to valid `ChatResponse` JSON per §2.3 (required keys present).

## Review checklist
- Timeout is 60s; client is `AsyncClient`.
- `ProviderError.code` values align with §6 `COOLDOWN` keys.
- Extension fields present and optional with sane defaults (`fallback_used=False`).
