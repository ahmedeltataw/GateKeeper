<div align="center">

# 🧩 GateKeeper: The Ultimate Local-First LLM Gateway

**GateKeeper: Take full control of your AI costs and operations with a local-first gateway.**

A local-first gateway that unifies free & paid LLM providers behind one OpenAI-compatible API — with privacy, cost control, and self-healing routing built in.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Local First](https://img.shields.io/badge/local--first-100%25-success)
![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20compatible-orange)

</div>

---

## Project Overview

**GateKeeper** is a self-hosted control plane for large language models. It runs
entirely on your own machine and exposes a single **OpenAI-compatible** endpoint
(`/v1/chat/completions`, `/v1/models`) that fans out to dozens of providers —
Groq, Google Gemini, OpenRouter, Cloudflare, GitHub Models, Mistral, NVIDIA, and
more.

Instead of scattering API keys across every tool and paying for redundant
subscriptions, you point your apps at **one local address** and GateKeeper
handles routing, fallback, rate limits, quotas, and health — privately.

> **Local-first means your prompts, keys, and usage data never leave your
> computer.** No middle-man server, no telemetry, no cloud account required.

> **Why "GateKeeper"?** The name says exactly what it does: it stands at the gate
> between your apps and every LLM provider, **guarding your tokens and your
> privacy**. Every key, quota, and prompt passes through GateKeeper — and nothing
> slips past it to the cloud. It is the gatekeeper for your tokens and your data.

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔑 | **Encrypted key vault** | Provider keys are encrypted at rest with **AES-256-GCM** in a local SQLite database — never stored in plaintext. |
| 🔀 | **Smart routing & fallback** | Each request is routed to the best provider for the task; on failure it transparently fails over to the next, so a single dead provider never breaks a call. |
| 🩺 | **Self-healing health monitor** | A background task continuously probes providers and **auto-disables** unhealthy or rate-limited ones, re-enabling them once they recover. |
| 📊 | **Quota & usage tracking** | Per-client, per-model usage counters (requests + tokens) measured against subscription quotas, with live progress bars in the dashboard. |
| 🎨 | **Dark-mode dashboard** | A clean Streamlit control panel for keys, models, provider health, and usage analytics. |
| 🧠 | **OpenCode support** | A dedicated `/v1/opencode/models` endpoint serves a model list in the exact shape OpenCode expects. |
| 👥 | **Multi-tenant ready (SaaS)** | Issue API keys per client; each key sees only the models its plan entitles it to. |
| 🛡️ | **Circuit breaker** | Repeatedly failing models are temporarily blacklisted to protect latency and provider budgets. |

---

## 🚀 Installation

**Requirements:** Python 3.12+ and at least one free provider API key
(e.g. [Groq](https://console.groq.com/keys),
[Gemini](https://aistudio.google.com/apikey),
[OpenRouter](https://openrouter.ai/settings/keys)).

### Windows — one click

```bash
git clone <repo-url>
cd "free models"
run.bat
```

`run.bat` creates the virtual environment, installs dependencies, prepares your
`.env`, starts the gateway, and opens it in your browser. That's it.

### macOS / Linux

```bash
git clone <repo-url>
cd "free models"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.server:app --host 127.0.0.1 --port 8000
```

The gateway is now live at **http://127.0.0.1:8000** (interactive docs at `/docs`).

### First-run setup

On first launch, **`run.bat` generates your `ENCRYPTION_KEY` automatically** and
saves it to a local `.env` — no external key file, no manual step. The key never
leaves your machine.

You only need to supply **at least one provider key** (e.g. `GROQ_KEY`,
`GEMINI_KEY`, `OPENROUTER_KEY`) — either in `.env` or later from the dashboard.

> On macOS/Linux, generate the key once with:
> ```bash
> python scripts/ensure_env_key.py
> ```

---

## 📖 Usage

### 1. Add provider keys

Either set them in `.env` (auto-imported on first run), or add them at runtime
from the **dashboard → Keys** page. Keys are encrypted immediately and only
decrypted in memory at request time.

### 2. Call it like OpenAI

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{"model": "or-gpt-oss-120b", "messages": [{"role":"user","content":"Hello!"}]}'
```

### 3. Connect to OpenCode

Point OpenCode at the gateway as a custom OpenAI-compatible provider:

| Setting | Value |
|---|---|
| **Base URL** | `http://127.0.0.1:8000/v1` |
| **API Key** | your client key (e.g. `sk-local`) |

Fetch the model list in OpenCode's format:

```bash
curl http://127.0.0.1:8000/v1/opencode/models \
  -H "Authorization: Bearer sk-local" -o opencode_models.json
```

The list is **automatically filtered to the models your key is entitled to** —
regular keys see shared (Auto) models, enterprise keys also see their dedicated
allocations.

### 4. Launch the dashboard (optional)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Manage keys, inspect provider health, and watch live **usage vs. quota** bars.

---

## ⚙️ Configuration

### Adding API keys (recommended: the control panel)

The easiest and safest way to add provider keys is the **dashboard → Keys** page:

1. Launch the dashboard (see step 4 above) and open **Keys**.
2. Pick a provider, paste its API key, and save.
3. The key is **encrypted with AES-256-GCM the moment it's saved** and written to
   a local SQLite vault. It is only ever decrypted in memory, at request time —
   it is never logged, echoed back, or stored in plaintext.

You can also pre-seed keys via `.env` (`GROQ_KEY=...`, `GEMINI_KEY=...`); they are
imported into the encrypted vault on first startup, after which `.env` is no
longer needed for them.

### Server settings

`config.yaml` controls host/port, auth, caching, rate limits, circuit breaker,
and quota enforcement. Highlights:

| Key | Purpose |
|-----|---------|
| `auth.multi_tenant` | Issue per-client keys, each scoped to its plan's models |
| `usage.enforce` | Enforce daily request/token quotas (returns HTTP 429 when exceeded) |
| `circuit.*` | Failure thresholds before a model is paused/blacklisted |

---

## 🔒 Security & Privacy

GateKeeper is **local-first by design**. Your data stays on your machine.

- **Nothing leaves your computer.** The gateway runs on `127.0.0.1`. Prompts,
  responses, API keys, and usage counters are processed and stored **locally** —
  there is no vendor backend and no telemetry.
- **Keys encrypted at rest.** Provider keys live in a local SQLite database,
  encrypted with **AES-256-GCM**. The decryption key (`ENCRYPTION_KEY`) is read
  from your `.env` and held only in memory.
- **Client keys are hashed.** Tenant API keys are stored as **SHA-256 hashes** —
  the raw key is never written to disk.
- **Secrets stay out of version control.** `.env`, `*.key`, and `*.db` are
  git-ignored by default; nothing sensitive is ever committed.
- **You own the data.** The only outbound traffic is the request **you** make to
  the upstream LLM provider you configured — exactly as if you had called that
  provider directly.

> When you sell or share this gateway, each customer runs their **own** instance.
> Their keys and traffic never touch yours.

---

## 🗂️ Project structure

```
free models/
├─ src/
│  ├─ api/          # FastAPI server, routes, middleware, admin endpoints
│  ├─ core/         # registry, router, fallback, circuit, health, usage, tenant
│  └─ providers/    # one adapter per upstream provider
├─ dashboard/       # Streamlit control panel (keys, models, analytics)
├─ scripts/         # helpers (ensure_env_key.py, sync_models.py)
├─ tests/           # pytest suite
├─ docs/            # public docs (docs/internal/ holds dev notes)
├─ config.yaml      # server, auth, cache, rate-limit, quota settings
├─ requirements.txt # runtime deps (requirements-dev.txt for tests)
├─ run.bat          # Windows one-click launcher
├─ LICENSE          # MIT
└─ CONTRIBUTING.md
```

---

## 🧪 Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

---

## 📄 License

MIT — see `LICENSE`.
#   G a t e K e e p e r  
 