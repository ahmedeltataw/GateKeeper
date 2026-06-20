# Adding a New Model

GateKeeper uses a **plugin-based provider system**. Adding a new model — or a
whole new provider — is declarative: you describe the provider, register it, and
the gateway wires up routing, key handling, and discovery for you.

This guide covers the common case: a provider that exposes an **OpenAI-compatible**
`/chat/completions` endpoint. Most modern AI APIs do.

---

## Overview

There are four moving parts, and most are a few lines each:

1. **Provider module** — declares the provider (id, endpoint, key variable).
2. **Configuration** — the endpoint base URL.
3. **Environment** — the variable holding the provider's API key.
4. **Model registry** — one entry per model you want to expose.

Then you add a test (see [Running Tests](running_tests.md)) and you are done.

---

## Step 1 — Create the provider module

Add a new module in the providers package. For an OpenAI-compatible backend, you
reuse the generic OpenAI-compatible provider and just declare a **spec**:

```python
from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spec import ProviderSpec, register_spec

PROVIDER_ID = "acme"
HEALTH_MODEL = "acme-mini"  # a cheap/free model used only for health checks


class AcmeProvider(OpenAICompatibleProvider):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, provider_id=PROVIDER_ID, health_model=HEALTH_MODEL)


SPEC = register_spec(
    ProviderSpec(
        id=PROVIDER_ID,
        base_url="https://api.acme.example/v1",
        env_var="ACME_API_KEY",
        health_model=HEALTH_MODEL,
        provider_class=AcmeProvider,
    )
)
```

> **No custom logic needed?** A standard OpenAI-compatible provider can skip the
> subclass entirely — register the spec without `provider_class` and the gateway
> builds a generic provider for it.

Then make sure the module is imported when the providers package loads, so its
registration runs automatically.

### Non-standard APIs

If the provider does **not** speak OpenAI's format (different request/response
shape), implement a provider class that translates to and from the unified
format, and point the spec's `provider_class` at it. Follow these robustness
rules in your `chat()` implementation:

- Reject a missing API key **before** any network call.
- Map upstream HTTP errors to clear error codes (`401`, `404`, `413`, `429`, `5xx`).
- Wrap transport failures (timeouts, unreachable host) so callers never see a
  raw networking exception — this is what lets fallback work.

---

## Step 2 — Add the endpoint to configuration

Add the provider's base URL under the `providers` section of your configuration
file:

```yaml
providers:
  acme: { base_url: "https://api.acme.example/v1" }
```

The configuration file is the source of truth for endpoints at runtime.

---

## Step 3 — Add the API key

Add the provider's key variable to your environment, using the **exact** name
declared in the spec:

```bash
# .env
ACME_API_KEY=...
```

On first startup, GateKeeper imports provider keys it finds in the environment
and stores them encrypted. After that, manage keys from the dashboard.

---

## Step 4 — Register the models

Add one entry per model to the model registry. Each entry maps a **gateway model
id** (what your users type) to a **provider model id** (what the upstream API
expects):

```json
{
  "id": "acme-large",
  "display_name": "Acme Large",
  "provider_id": "acme",
  "provider_model_id": "acme-large-latest",
  "strength": "A",
  "use_cases": ["coding", "reasoning"],
  "context_window": 128000,
  "max_output_tokens": 8192,
  "rate_limits": {},
  "added_at": "2026-06-20",
  "last_verified": "2026-06-20"
}
```

- `provider_id` must match your spec id.
- `provider_model_id` is the exact id the upstream API uses.

Consider adding a [Model Card](../models/overview.md) so users know when to reach
for the new model.

---

## Step 5 — Test it

Write a test using the shared provider contract and run the suite. The contract
checks connectivity, authentication errors, unreachable endpoints, and payload
formatting with no network calls and no real key. See
[Running Tests](running_tests.md).

---

## Checklist

- [ ] Provider module created and registered
- [ ] Endpoint added to configuration
- [ ] API key variable added to the environment
- [ ] One or more models added to the registry
- [ ] Contract test passing
- [ ] (Optional) Model card written
