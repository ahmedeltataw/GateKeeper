# Adding a New Model Provider

GateKeeper providers are **plugin-based**. Adding an OpenAI-compatible provider
is declarative: write one small module, add two config lines, drop in a test.
No core code changes.

This guide uses the **Z.ai** provider (`src/providers/zai.py`) as the reference
example.

---

## 1. Where the provider code goes

All providers live in `src/providers/`. The pieces:

| File | Role |
| --- | --- |
| `base.py` | `BaseProvider` ABC + `ProviderConfig` + OpenAI envelope helper |
| `openai_compatible.py` | Generic provider for any OpenAI `/chat/completions` backend |
| `spec.py` | `ProviderSpec` plugin registry (`register_spec`, `get_spec`) |
| `<your_provider>.py` | **Your new module** — usually ~10 lines |
| `__init__.py` | Factory + discovery; reads the spec registry |

### Case A — OpenAI-standard backend (the common case)

If the provider speaks OpenAI `/chat/completions` (Z.ai, Groq, Cerebras, …),
you do **not** write a custom class. Create `src/providers/<id>.py`:

```python
# src/providers/zai.py
from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spec import ProviderSpec, register_spec

_PROVIDER_ID = "zai"
_HEALTH_MODEL = "glm-4.5-flash"   # cheap/free model used only for health probes


class ZaiProvider(OpenAICompatibleProvider):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, provider_id=_PROVIDER_ID, health_model=_HEALTH_MODEL)


SPEC = register_spec(
    ProviderSpec(
        id=_PROVIDER_ID,
        base_url="https://api.z.ai/api/paas/v4",
        env_var="ZAI_API_KEY",
        health_model=_HEALTH_MODEL,
        provider_class=ZaiProvider,
    )
)
```

> A truly vanilla provider can skip the subclass and pass nothing for
> `provider_class`; `ProviderSpec.build()` constructs a generic
> `OpenAICompatibleProvider` for you. Subclassing only buys you a named type
> and a fixed `health_model`.

Then register the module so its `register_spec()` runs on import. In
`src/providers/__init__.py`, alongside the existing one:

```python
from src.providers import zai  # noqa: F401  (registers the "zai" spec)
```

That single import is the only edit to a shared file. The factory
(`create_provider`), discovery (`list_provider_ids`), and key bootstrap
(`provider_env_vars`) all read from the spec registry automatically.

### Case B — non-OpenAI wire format

If the API is not OpenAI-shaped (e.g. Gemini, Cohere), subclass `BaseProvider`
directly and implement `chat`, `list_models`, `check_health` (and optionally
`chat_stream`). Use `build_openai_envelope()` from `base.py` to return a unified
response. Point the spec's `provider_class` at your class. See
`src/providers/gemini.py`.

**Robustness rules for any custom `chat()`:**
- No API key → raise `ProviderError(..., "401")` before any network call.
- Map HTTP status → `ProviderError` code (`401`, `404`, `413`, `429`, `5xx`).
- Wrap transport failures: catch `httpx.TimeoutException` → `"timeout"` and
  `httpx.RequestError` → `"5xx"`, so an unreachable URL never leaks a raw
  `httpx` exception (this is what makes fallback work).

---

## 2. Updating the settings files

Three places, all data — no logic:

1. **`config.yaml`** — add the endpoint under `providers:`
   ```yaml
   providers:
     zai: {base_url: "https://api.z.ai/api/paas/v4"}
   ```
   Routing reads the base URL from here (the spec's `base_url` is the
   documented default; `config.yaml` is the source of truth at runtime).

2. **`.env` / `.env.example`** — add the key, using the **exact** `env_var` from
   the spec:
   ```bash
   ZAI_API_KEY=...
   ```
   On first startup, if the key database is empty, every provider key found in
   the environment is imported into encrypted SQLite. After that, manage keys
   from the dashboard or via the admin API.

3. **`models_registry.json`** — add the models this provider serves. Each entry
   maps a gateway model id to the provider:
   ```json
   {
     "id": "glm-4.6",
     "display_name": "GLM-4.6",
     "provider_id": "zai",
     "provider_model_id": "glm-4.6",
     "strength": "A",
     "use_cases": ["coding", "reasoning"],
     "context_window": 200000,
     "max_output_tokens": 8192,
     "rate_limits": {},
     "added_at": "2026-06-20",
     "last_verified": "2026-06-20"
   }
   ```
   `provider_id` must equal your spec id; `provider_model_id` is what the
   provider's API actually expects. Optional metadata overlays go in
   `models_schema.json`.

> **Docker note:** none of this requires a writable `.env`. Inject
> `ZAI_API_KEY` (and `ENCRYPTION_KEY`) as container environment variables — the
> bootstrap reads them directly.

---

## 3. Testing the new model

### 3a. Template (offline) tests — required

Every provider gets the standard contract for free. Create
`tests/test_provider_<id>.py` and subclass the contract:

```python
from src.providers.base import BaseProvider, ProviderConfig
from src.providers.zai import ZaiProvider
from tests.provider_contract import OpenAICompatibleProviderContract


class TestZaiProviderContract(OpenAICompatibleProviderContract):
    provider_id = "zai"
    gateway_model_id = "glm-4.6"
    provider_model_id = "glm-4.6"

    def make_provider(self, *, api_key="contract-test-key") -> BaseProvider:
        return ZaiProvider(ProviderConfig(
            name="zai", base_url="https://api.z.ai/api/paas/v4",
            api_key=api_key, models=[self.gateway_model_id], rate_limits={},
        ))
```

The inherited tests assert, with **no network and no real key** (an
`httpx.MockTransport` is injected):

- **Connectivity** — a 200 becomes a unified `ChatResponse`.
- **Auth errors** — backend 401 *and* a missing key raise `ProviderError("401")`.
- **Unreachable URL** — a transport failure raises `ProviderError("5xx")`,
  never a raw `httpx` error.
- **Payload validation** — the body sent is valid OpenAI JSON, carrying the
  *provider-side* model id and a `Bearer` auth header.

Run them:
```bash
pytest tests/test_provider_zai.py -q
```

### 3b. Live smoke test — before trusting it in production

The contract proves the wiring; it does not prove your key or the live endpoint
work. Verify against the real API once:

```bash
# 1. Put ZAI_API_KEY in .env, then start the gateway.
python -m src.api.server

# 2. Real call through the gateway (use a model id from models_registry.json):
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4.6","messages":[{"role":"user","content":"reply with: pong"}]}'

# 3. Health probe for the provider:
curl -s http://127.0.0.1:8000/admin/providers \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Expect a normal OpenAI-shaped completion and a `healthy` status. A `401` means a
bad/missing key; `unreachable`/`5xx` means a wrong `base_url` or network issue.

---

## Checklist

- [ ] `src/providers/<id>.py` with `register_spec(ProviderSpec(...))`
- [ ] import line added in `src/providers/__init__.py`
- [ ] `config.yaml` → `providers.<id>.base_url`
- [ ] `.env.example` (and `.env`) → the spec's `env_var`
- [ ] `models_registry.json` → at least one model with `provider_id: <id>`
- [ ] `tests/test_provider_<id>.py` subclasses the contract → `pytest` green
- [ ] live smoke test passes with a real key
