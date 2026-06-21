# 🧩 GateKeeper

> **The Ultimate Local-First LLM Gateway** — Take full control of your AI costs and operations, one endpoint, every provider.

A self-hosted control plane that unifies free & paid LLM providers behind a single **OpenAI-compatible API** — with privacy, cost control, and self-healing routing built in.

<div align="center">

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-00CEC0?style=for-the-badge)](LICENSE)
[![Local-First](https://img.shields.io/badge/local--first-100%25-6C5CE7?style=for-the-badge&logo=lock&logoColor=white)](#-security--privacy)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20compatible-FF6B35?style=for-the-badge&logo=openai&logoColor=white)](#-usage)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker)

</div>

**[Quick Start](#-installation)** · **[Features](#-features)** · **[Architecture](#-architecture)** · **[Providers](#-supported-providers)** · **[Contributing](#-contributing)**

---

## 🎯 Why GateKeeper?

| Without GateKeeper | With GateKeeper |
|:---|:---|
| 🔑 API keys scattered in every `.env` file | 🔐 **One encrypted AES-256-GCM vault** |
| 💸 Paying for 5+ subscriptions | 💰 **Free providers first, paid as fallback** |
| 💥 One dead provider = broken app | 🔄 **4-tier automatic fallback engine** |
| 🔍 Zero visibility into usage | 📊 **Real-time dashboard & analytics** |
| 🌐 Prompts sent to unknown servers | 🏠 **Local-first — nothing leaves your machine** |

---

## ✨ Features

### 🔐 Security & Privacy
- **AES-256-GCM** encrypted key vault (SQLite) — keys never stored in plaintext
- **SHA-256** hashed client API keys — raw key never written to disk
- **Secrets auto-generated** on first run — no manual setup
- **Zero telemetry** — no analytics, no phone-home, no cloud dependency

### 🔀 Smart Routing
- **4-tier fallback engine** with context handoff
- Per-task quality routing (coding, search, reasoning, …)
- Sticky sessions for conversation continuity
- Streaming support with pre-first-byte failover

### 🩺 Self-Healing
- Background **health probes** with passive-first strategy
- **Circuit breaker** with auto-blacklist
- Smart diagnostics: 413 → shrink, 5xx → backoff
- Auto-recovery when providers come back online

### 📊 Observability
- **Streamlit dashboard** with dark mode
- Per-provider latency, token, and request analytics
- Live usage vs. quota progress bars
- **LRU cache** with hit rate tracking

---

## 🏗️ Architecture

```text
                    ┌─────────────────────────────────────────┐
                    │         Your Applications                │
                    │   (OpenCode, Hermes, scripts, agents)   │
                    └──────────────────┬──────────────────────┘
                                       │
                               OpenAI-compatible
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │            🧩 GATEKEEPER                 │
                    │         127.0.0.1:8000/v1               │
                    │                                         │
                    │  ┌─────────┐ ┌──────────┐ ┌──────────┐ │
                    │  │  Auth   │ │  Cache   │ │  Rate    │ │
                    │  │Middleware│ │  (LRU)   │ │ Limiter  │ │
                    │  └────┬────┘ └────┬─────┘ └────┬─────┘ │
                    │       │           │            │        │
                    │  ┌────▼───────────▼────────────▼─────┐  │
                    │  │        Quality Router (auto)       │  │
                    │  │   task_type → best model chain     │  │
                    │  └────────────────┬──────────────────┘  │
                    │                   │                      │
                    │  ┌────────────────▼──────────────────┐  │
                    │  │      4-Tier Fallback Engine        │  │
                    │  │  T1: same model → other provider   │  │
                    │  │  T2: same strength, other model    │  │
                    │  │  T3: one strength lower            │  │
                    │  │  T4: any available with budget     │  │
                    │  └────────────────┬──────────────────┘  │
                    │                   │                      │
                    │  ┌────────────────▼──────────────────┐  │
                    │  │  Diagnostics · Circuit · Health    │  │
                    │  └────────────────┬──────────────────┘  │
                    └───────────────────┼─────────────────────┘
                                        │
          ┌───────────┬─────────────────┼──────────────┬───────────┐
          ▼           ▼                 ▼              ▼           ▼
    ┌──────────┐ ┌──────────┐  ┌────────────┐  ┌──────────┐ ┌──────────┐
    │  Groq    │ │  Gemini  │  │ OpenRouter  │  │ Mistral  │ │  + 8 more│
    │ 🟢 free  │ │ 🟢 free  │  │ 🟡 free tier│  │ 🟡 free  │ │ providers│
    └──────────┘ └──────────┘  └────────────┘  └──────────┘ └──────────┘
```

---

## 🚀 Installation

### Prerequisites
- **Python 3.12+**
- At least one free API key:
  [Groq](https://console.groq.com/keys) ·
  [Gemini](https://aistudio.google.com/apikey) ·
  [OpenRouter](https://openrouter.ai/settings/keys)

### Windows — One Click

```bash
git clone https://github.com/ahmedeltataw/GateKeeper.git
cd GateKeeper
run.bat
```

> `run.bat` creates the venv, installs deps, generates your `ENCRYPTION_KEY`, starts the gateway, and opens the dashboard.

### macOS / Linux

```bash
git clone https://github.com/ahmedeltataw/GateKeeper.git
cd GateKeeper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.server:app --host 127.0.0.1 --port 8000
```

### 🐳 Docker

```bash
docker compose up -d
```

>The gateway is now live at **http://127.0.0.1:8000** — interactive docs at [`/docs`](http://127.0.0.1:8000/docs).

---

## 📖 Usage

### 1. Add Provider Keys
Via the **dashboard → Keys** page (recommended), or in `.env`:

```env
GROQ_KEY=gsk_...
GEMINI_KEY=AIza...
OPENROUTER_KEY=sk-or-...
```

> Keys are **encrypted with AES-256-GCM** the moment they're saved and only decrypted in memory at request time.

### 2. Call It Like OpenAI

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "Hello!"}]}'
```

### 3. Use With Your Favorite Tools

| Tool | Base URL | API Key |
|------|----------|---------|
| **OpenCode** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **Hermes Agent** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **OpenAI SDK** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **curl / HTTP** | `http://127.0.0.1:8000/v1` | `sk-local` |

> 👉 Full walkthrough — auto-setup, discovery endpoints, and per-agent config — in
> **[Integrate with OpenCode & AI Agents](#-integrate-with-opencode--ai-agents)**.

### 4. Launch the Dashboard (Optional)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔌 Integrate with OpenCode & AI Agents

GateKeeper is **self-describing**: it tells your agent how to connect to it, so
you never hand-copy base URLs or model ids. Three ways in — fully automatic,
ask-the-gateway, or manual.

### Option A — 30-second auto-setup (recommended)

`scripts/setup_agents.py` fetches the gateway's live connection details and
writes the correct config for each agent in place. JSON configs are merged
(existing providers preserved), text configs are confined to a
`GATEKEEPER_BEGIN/END` marker block, and existing
files are backed up to `*.gatekeeper.bak` before any write.

```bash
# Preview the exact config for OpenCode + Claude Code (writes nothing):
python scripts/setup_agents.py --print --agents opencode,claude-code

# Write it for real, no prompts:
python scripts/setup_agents.py --agents opencode --yes

# Point at a remote gateway, dry-run first:
python scripts/setup_agents.py --url http://192.168.1.20:8000 --dry-run
```

| Flag | Effect |
|------|--------|
| `--agents` | Comma list: `opencode,hermes,claude-code` (default: all) |
| `--print` | Print snippets only — write nothing |
| `--dry-run` | Show the resulting file contents — write nothing |
| `--yes` | Skip the per-file confirmation prompt |
| `--url` | Gateway root URL (default `http://127.0.0.1:8000`) |

### Option B — ask the gateway directly

Any tool can pull connection details from the public discovery endpoints — no
auth required, and the client key is only echoed on a loopback bind.

```bash
# Everything an agent needs: base URL, key, sample model ids, per-agent configs
curl http://127.0.0.1:8000/v1/connection-info

# A ready-made snippet for one agent (text or json):
curl "http://127.0.0.1:8000/v1/agent-snippet?agent=opencode&format=json"
```

`/v1/connection-info` returns:

```json
{
  "gateway": {
    "base_url": "http://127.0.0.1:8000/v1",
    "api_key": "sk-local",
    "auth_enabled": true
  },
  "models": { "default": "auto", "list_url": "/v1/models" },
  "agents": {
    "opencode":    { "type": "env", "vars": { "OPENAI_BASE_URL": "http://127.0.0.1:8000/v1", "OPENAI_API_KEY": "sk-local" } },
    "claude-code": { "type": "env", "vars": { "ANTHROPIC_BASE_URL": "http://127.0.0.1:8000", "ANTHROPIC_API_KEY": "sk-local" } }
  },
  "notes": ["Use `auto` to let the Quality Router pick the best available model."]
}
```

### Option C — manual OpenCode config

Add GateKeeper as a custom OpenAI-compatible provider in
`~/.config/opencode/config.json` (Windows: `%USERPROFILE%\.config\opencode\config.json`):

```json
{
  "provider": {
    "gatekeeper": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1",
        "apiKey": "sk-local"
      }
    }
  }
}
```

Then select a model as **`gatekeeper/<model-id>`** — for example
`gatekeeper/auto`, `gatekeeper/groq-llama-3.3-70b`, or `gatekeeper/mistral-codestral`.
The OpenCode-shaped model list is served at `GET /v1/opencode/models`.

| Setting | Value |
|---------|-------|
| **Base URL** | `http://127.0.0.1:8000/v1` |
| **API Key** (GateKeeper client key) | `sk-local` — from `auth.api_key` in `config.yaml` |
| **Model** | `auto`, or any **Model ID** from [Model Cards](#-model-cards) |

> The **GateKeeper API key** is your gateway's *client* key (`auth.api_key`,
> default `sk-local`) — **not** a provider key. Provider keys stay encrypted in
> the vault and never leave your machine.

### Any OpenAI-compatible agent (Cursor, Continue.dev, SDKs)

GateKeeper speaks the OpenAI wire format, so any tool with a custom-endpoint
setting works — point it at the base URL + key above and pick `auto`:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="sk-local")
resp = client.chat.completions.create(
    model="auto",  # or a specific Model ID, e.g. "mistral-codestral"
    messages=[{"role": "user", "content": "Refactor this function..."}],
)
print(resp.choices[0].message.content)
```

---

## 🧪 Live Health Check

Before trusting the catalog, smoke-test every active model against your real
keys. The probe sends one tiny completion per model and feeds the result into
the circuit breaker, so broken or no-access models are auto-quarantined.

```bash
# One-shot report: per-model PASS/FAIL + latency + a by-provider summary
python scripts/live_smoke_report.py
```

The boot probe ships **enabled** — it runs the same `smoke` path across the
catalog at launch and quarantines failures before any user hits them. Tune or
disable it in `config.yaml`:

```yaml
probe:
  enabled: true        # smoke-test + auto-quarantine on boot
  concurrency: 3       # keep low to spare provider rate budget
  timeout_seconds: 5
```

Then watch the result live:

```bash
curl http://127.0.0.1:8000/health        # -> "catalog_probe": { healthy, failed, blacklisted }
curl http://127.0.0.1:8000/admin/quarantine -H "Authorization: Bearer $ADMIN_TOKEN"
```

> A model is only **blacklisted** after it fails on repeated boots; a single
> transient failure (a `429` rate limit, a timeout) just opens the breaker and
> is retried — so a brief provider hiccup never permanently drops a good model.

---

## 🔀 Supported Providers

| Provider | Tier | Free Models | Highlights |
|----------|------|-------------|------------|
| 🟣 **Groq** | Free | Llama 3.3 70B, GPT-OSS 120B | Ultra-fast inference, generous RPM |
| 🔵 **Google Gemini** | Free | Gemini 2.5 Flash, Gemini 2.5 Pro | Huge context window, vision support |
| 🟠 **OpenRouter** | Free tier | 50+ models | One key, many providers |
| 🔴 **Mistral** | Free tier | Codestral, Mistral Large | Top coding model, EU hosting |
| ⚫ **GitHub Models** | Free tier | GPT-4o, Phi-4 | Free via GitHub account |
| 🟢 **NVIDIA** | Free tier | DeepSeek R1, Llama 3.3 70B | Enterprise GPU cluster |
| 🟤 **Cerebras** | Free tier | GPT-OSS 120B | Wafer-scale inference |
| 🟡 **Cloudflare Workers AI** | Free tier | Llama 3.2 11B Vision | Edge inference |
| 🔵 **Zhipu (GLM)** | Free tier | GLM-4 Flash | Chinese LLM leader |
| 🟣 **Hugging Face** | Free tier | 100+ open models | Open-source model hub |
| 🟢 **Aion Labs** | Free tier | Aion Nemotron | Specialized inference |
| 🔴 **Cohere** | Free tier | Command R+ | RAG-optimized, multilingual |

---

## 🃏 Model Cards

The catalog ships **73 model entries**; the ones below are **live-verified** —
each returned a real completion through the gateway's own smoke probe
(`src/core/smoke.py`, driven by `scripts/live_smoke_report.py`) on
**2026-06-21** with the keys configured in this deployment. Entries that 401 /
404 / time out are auto-quarantined by the circuit breaker and never reach a
request (see [Live Health Check](#-live-health-check)).

> **Tier legend** — `S` frontier · `A` high-capability · `B` balanced · `C` fast/lightweight.
> Call any model by its **Model ID**, or use `auto` to let the Quality Router pick.

### ⚡ Groq — ultra-fast inference (9 live)

| Model ID | Tier | Context | Max out | Best for |
|----------|:----:|--------:|--------:|----------|
| `groq-llama-3.3-70b` | A | 128K | 32K | Coding, search, reasoning, data |
| `groq-gpt-oss-120b` | A | 128K | 32K | Coding, search, reasoning |
| `groq-qwen3-32b` | A | 128K | 16K | Reasoning, coding, search |
| `groq-qwen3.6-27b` | A | 128K | 8K | Coding, reasoning |
| `groq-compound` | A | 128K | 8K | Agentic reasoning + search |
| `groq-gpt-oss-20b` | B | 128K | 32K | Coding, reasoning, search |
| `groq-compound-mini` | B | 128K | 8K | Fast reasoning |
| `groq-llama-4-scout` | B | 128K | 8K | Search, vision, coding |
| `groq-llama-3.1-8b` | C | 128K | 8K | High-volume search & light coding |

### ⚫ GitHub Models — free via GitHub PAT (7 live)

| Model ID | Tier | Context | Max out | Best for |
|----------|:----:|--------:|--------:|----------|
| `gh-deepseek-r1-0528` | S | 128K | 4K | Deep reasoning, coding |
| `gh-deepseek-v3-0324` | S | 128K | 4K | General + coding |
| `gh-gpt-4.1` | A | 128K | 4K | Coding, search, reasoning, data |
| `gh-gpt-4o` | A | 128K | 4K | Coding, creative, **vision**, data |
| `gh-llama-3.3-70b` | A | 128K | 4K | Coding, search, data |
| `gh-deepseek-r1` | A | 128K | 4K | Reasoning, coding |
| `gh-gpt-4o-mini` | B | 128K | 4K | Cheap coding, search, data |

### 🔴 Mistral — top coding model, EU-hosted (5 live)

| Model ID | Tier | Context | Max out | Best for |
|----------|:----:|--------:|--------:|----------|
| `mistral-large` | S | 128K | 8K | Frontier general, reasoning, data |
| `mistral-codestral` | A | **256K** | 8K | Code generation & completion |
| `mistral-medium` | A | 128K | 8K | Coding, search, reasoning |
| `mistral-pixtral` | A | 128K | 8K | **Vision** + coding |
| `mistral-small` | B | 128K | 8K | Coding, search, creative |

### 🟠 OpenRouter — one key, many providers (5 live)

| Model ID | Tier | Context | Max out | Best for |
|----------|:----:|--------:|--------:|----------|
| `or-nemotron-3-super-120b` | S | 128K | 8K | Reasoning, coding |
| `or-gpt-oss-120b` | A | 128K | 8K | Coding, search, reasoning |
| `or-auto` | B | 128K | 8K | Default free auto-pick |
| `or-gemma-4-31b` | B | 128K | 8K | Creative, search |
| `or-nemotron-3-nano-30b` | B | 128K | 8K | Data, search |

### 🟤 Cerebras — wafer-scale inference (2 live)

| Model ID | Tier | Context | Max out | Best for |
|----------|:----:|--------:|--------:|----------|
| `cb-gpt-oss-120b` | A | 8K | 8K | Coding, search, reasoning |
| `cb-glm-4.7` | A | 8K | 8K | Reasoning, coding |

### 🔵 Others (4 live)

| Model ID | Provider | Tier | Context | Best for |
|----------|----------|:----:|--------:|----------|
| `glm-4.5-flash` | Z.ai (GLM) | A | 128K | Coding, reasoning, search |
| `gemini-2.5-flash-lite` | Google Gemini | B | **1M** | Long-context, search, **vision** |
| `nv-llama-3.3-70b` | NVIDIA | A | 128K | Coding, search, data |
| `hf-llama-3.3-70b` | Hugging Face | A | 128K | Coding, search, data |

### 🎯 Quick picks by task

| Task | Recommended `model` |
|------|---------------------|
| **Coding** | `mistral-codestral` (256K), `groq-gpt-oss-120b`, `gh-gpt-4.1` |
| **Deep reasoning** | `gh-deepseek-r1-0528` (S), `or-nemotron-3-super-120b` (S) |
| **Frontier general** | `mistral-large` (S), `gh-deepseek-v3-0324` (S) |
| **Vision / multimodal** | `gh-gpt-4o`, `mistral-pixtral`, `gemini-2.5-flash-lite` |
| **Longest context** | `gemini-2.5-flash-lite` (1M), `mistral-codestral` (256K) |
| **Fastest / cheapest** | `groq-llama-3.1-8b`, `groq-llama-4-scout` |
| **Just give me the best** | `auto` — the Quality Router decides |

---

## ⚙️ Configuration

All settings live in `config.yaml`:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `server` | `host` / `port` | `127.0.0.1` / `8000` | Bind address |
| `auth` | `api_key` | `sk-local` | Master API key |
| `auth` | `multi_tenant` | `false` | Per-client keys |
| `cache` | `enabled` / `ttl` | `true` / `300s` | Response cache |
| `rate_limiter` | `enabled` | `true` | Token-bucket rate limits |
| `circuit` | `failures_to_open` | `3` | Breaker threshold |
| `circuit` | `opens_to_blacklist` | `3` | Auto-blacklist |
| `usage` | `enforce` | `false` | Return 429 on quota exceeded |
| `diagnostics` | `max_remediation_attempts` | `2` | Auto-repair retries |

---

## 🔒 Security & Privacy

GateKeeper is **local-first by design**. Your data stays on your machine.

| Layer | Protection |
|-------|-----------|
| **Provider keys** | AES-256-GCM encrypted at rest in SQLite |
| **Client keys** | SHA-256 hashed — raw key never written to disk |
| **Network** | Binds to `127.0.0.1` — no external access |
| **Telemetry** | Zero — no analytics, no phone-home |
| **Secrets** | `.env`, `*.key`, `*.db` git-ignored by default |
| **Data flow** | Only outbound traffic is to providers **you** configured |

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the full test suite
pytest -q

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

### Project Structure

```text
GateKeeper/
├── src/
│   ├── api/            # FastAPI server, routes, middleware
│   ├── core/           # Router, fallback, circuit breaker, health
│   └── providers/      # One adapter per provider (12 total)
├── dashboard/          # Streamlit control panel
├── scripts/            # Helper scripts
├── tests/              # pytest suite
├── docs/               # Documentation
├── config.yaml         # Server configuration
├── models_registry.json
├── Dockerfile
├── docker-compose.yml
└── run.bat
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's a bug report, documentation improvement, or a new provider adapter.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the development workflow.

- 🐛 [Report a Bug](https://github.com/ahmedeltataw/GateKeeper/issues/new)
- 💡 [Request a Feature](https://github.com/ahmedeltataw/GateKeeper/issues/new)
- 🔧 [Add a Provider](CONTRIBUTING.md#adding-a-new-provider)
- 📖 [Read the Docs](docs/)

---

## 📄 License

MIT License — see **[LICENSE](LICENSE)** for details.

---

<div align="center">

**Built with ❤️ by [Ahmed Eltatawy](https://github.com/ahmedeltataw)**

If you find GateKeeper useful, consider giving it a ⭐ — it helps others discover the project!

</div>
