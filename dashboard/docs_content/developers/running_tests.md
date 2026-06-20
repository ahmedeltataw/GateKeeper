# Running Tests

GateKeeper ships with a full test suite. Before deploying a new model — or any
change — run the tests to confirm everything is stable.

The tests are **offline**: they use mocked transports, so you do **not** need
real API keys or a network connection.

---

## Prerequisites

Install the project dependencies (ideally in a virtual environment):

```bash
pip install -r requirements.txt
```

---

## Run the full suite

```bash
pytest
```

Quiet output:

```bash
pytest -q
```

A green run means the gateway, routing, and every provider contract pass.

---

## Run a single file

When you add a new model, run just its test first for a fast feedback loop:

```bash
pytest tests/test_provider_acme.py -q
```

---

## Run a single test

Use `-k` to match a test by name:

```bash
pytest -k "connectivity" -q
```

---

## Useful flags

| Flag | What it does |
| --- | --- |
| `-q` | Quiet, compact output |
| `-v` | Verbose, one line per test |
| `-x` | Stop at the first failure |
| `-k "expr"` | Run tests matching an expression |
| `--lf` | Re-run only the tests that failed last time |

---

## The provider contract (template test)

New providers do not need hand-written tests for the basics. GateKeeper provides
a reusable **contract** that every OpenAI-compatible provider can inherit. You
set three attributes and supply a builder; the contract supplies the tests.

```python
from src.providers.base import BaseProvider, ProviderConfig
from src.providers.acme import AcmeProvider
from tests.provider_contract import OpenAICompatibleProviderContract


class TestAcmeProviderContract(OpenAICompatibleProviderContract):
    provider_id = "acme"
    gateway_model_id = "acme-large"
    provider_model_id = "acme-large-latest"

    def make_provider(self, *, api_key="contract-test-key") -> BaseProvider:
        return AcmeProvider(ProviderConfig(
            name="acme",
            base_url="https://api.acme.example/v1",
            api_key=api_key,
            models=[self.gateway_model_id],
            rate_limits={},
        ))
```

Inheriting the contract gives you, for free:

- **Connectivity** — a successful response is translated to the unified format.
- **Authentication errors** — bad and missing keys are reported clearly.
- **Unreachable endpoint** — transport failures become clean, retryable errors.
- **Payload validation** — the request sent upstream is correctly formatted.

Run it:

```bash
pytest tests/test_provider_acme.py -q
```

---

## Before you deploy

1. `pytest` is fully green.
2. Your new model's contract test passes.
3. You have done one **live** smoke test with a real key (a single real request
   through the gateway) to confirm the credentials and endpoint actually work.

Only the live smoke test touches the network — everything else runs offline.
