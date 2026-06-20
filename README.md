<div align="center">

<a href="https://github.com/ahmedeltataw/GateKeeper">
  <img src="https://placehold.co/900x200/0a0a0f/F5A623?text=🧩+GateKeeper&font=source-sans-pro" alt="GateKeeper Banner" width="900">
</a>

# 🧩 GateKeeper

### The Ultimate Local-First LLM Gateway

**Take full control of your AI costs and operations — one endpoint, every provider.**

A self-hosted control plane that unifies free & paid LLM providers behind a single **OpenAI-compatible API** — with privacy, cost control, and self-healing routing built in.

---

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-00CEC0?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/ahmedeltataw/GateKeeper/pytest.yml?style=for-the-badge&label=tests&logo=github-actions&logoColor=white)](https://github.com/ahmedeltataw/GateKeeper/actions)
[![Local-First](https://img.shields.io/badge/local--first-100%25-6C5CE7?style=for-the-badge&logo=lock&logoColor=white)](#-security--privacy)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20compatible-FF6B35?style=for-the-badge&logo=openai&logoColor=white)](#-usage)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker)

<br>

**[Quick Start](#-installation)** · **[Features](#-features)** · **[Architecture](#-architecture)** · **[Providers](#-supported-providers)** · **[API Reference](#-usage)** · **[Contributing](#-contributing)**

</div>

---

## 🎯 Why GateKeeper?

> **The problem:** You scatter API keys across every tool, pay for redundant subscriptions, and have zero visibility into usage — while your prompts and keys leak to third parties.

> **The solution:** Point every app at **one local address**. GateKeeper routes, falls back, rate-limits, tracks quotas, and monitors health — **privately**.

| Without GateKeeper | With GateKeeper |
|:---:|:---:|
| 🔑 API keys in every `.env` | 🔐 **One encrypted vault** |
| 💸 Paying for 5+ subscriptions | 💰 **Free providers first, paid as fallback** |
| 💥 One dead provider = broken app | 🔄 **4-tier automatic fallback** |
| 🔍 No idea what's happening | 📊 **Real-time dashboard & analytics** |
| 🌐 Prompts sent to unknown servers | 🏠 **Local-first — nothing leaves your machine** |

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔐 Security & Privacy
- **AES-256-GCM** encrypted key vault (SQLite)
- **SHA-256** hashed client keys
- Local-first — **zero telemetry**
- Secrets auto-generated on first run

### 🔀 Smart Routing
- **4-tier fallback engine** with context handoff
- Per-task quality router (coding, search, reasoning, ...)
- Sticky sessions for conversation continuity
- Streaming support with pre-first-byte failover

</td>
<td width="50%">

### 🩺 Self-Healing
- Background **health probes** with passive-first strategy
- **Circuit breaker** with auto-blacklist
- Smart diagnostics: 413 shrink, 5xx backoff
- Auto-recovery when providers come back online

### 📊 Observability
- **Streamlit dashboard** with dark mode
- Per-provider latency, token, and request analytics
- Live usage vs. quota progress bars
- Cache hit rate tracking

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              Your Applications           │
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
           ┌────────────┬───────────────┼───────────────┬────────────┐
           ▼            ▼               ▼               ▼            ▼
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

> `run.bat` creates the venv, installs deps, generates your `ENCRYPTION_KEY`, starts the gateway, and opens the dashboard. **That's it.**

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

The gateway is now live at **http://127.0.0.1:8000** — interactive docs at [`/docs`](http://127.0.0.1:8000/docs).

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
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 3. Use With Your Favorite Tools

| Tool | Base URL | API Key |
|------|----------|---------|
| **OpenCode** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **Hermes Agent** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **OpenAI SDK** | `http://127.0.0.1:8000/v1` | `sk-local` |
| **curl / HTTP** | `http://127.0.0.1:8000/v1` | `sk-local` |

### 4. Launch the Dashboard (Optional)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔀 Supported Providers

<table>
<tr>
<th>Provider</th>
<th>Tier</th>
<th>Free Models</th>
<th>Highlights</th>
</tr>
<tr><td>🟣 <b>Groq</b></td><td>Free</td><td>Llama 3.3 70B, GPT-OSS 120B</td><td>Ultra-fast inference, generous RPM</td></tr>
<tr><td>🔵 <b>Google Gemini</b></td><td>Free</td><td>Gemini 2.5 Flash, Gemini 2.5 Pro</td><td>Huge context window, vision support</td></tr>
<tr><td>🟠 <b>OpenRouter</b></td><td>Free tier</td><td>50+ models (Llama, Gemma, Qwen...)</td><td>Aggregator — one key, many models</td></tr>
<tr><td>🔴 <b>Mistral</b></td><td>Free tier</td><td>Codestral, Mistral Large</td><td>Top coding model, European hosting</td></tr>
<tr><td>⚫ <b>GitHub Models</b></td><td>Free tier</td><td>GPT-4o, Phi-4</td><td>Free via GitHub account</td></tr>
<tr><td>🟢 <b>NVIDIA</b></td><td>Free tier</td><td>DeepSeek R1, Llama 3.3 70B</td><td>Enterprise GPU cluster</td></tr>
<tr><td>🟤 <b>Cerebras</b></td><td>Free tier</td><td>GPT-OSS 120B</td><td>Wafer-scale inference</td></tr>
<tr><td>🟡 <b>Cloudflare Workers AI</b></td><td>Free tier</td><td>Llama 3.2 11B Vision</td><td>Edge inference, neurons-based billing</td></tr>
<tr><td>🔵 <b>Zhipu (GLM)</b></td><td>Free tier</td><td>GLM-4 Flash</td><td>Chinese LLM leader</td></tr>
<tr><td>🟣 <b>Hugging Face</b></td><td>Free tier</td><td>100+ open models</td><td>Open-source model hub</td></tr>
<tr><td>🟢 <b>Aion Labs</b></td><td>Free tier</td><td>Aion Nemotron</td><td>Specialized inference</td></tr>
<tr><td>🔴 <b>Cohere</b></td><td>Free tier</td><td>Command R+</td><td>RAG-optimized, multilingual</td></tr>
</table>

---

## ⚙️ Configuration

All settings live in `config.yaml`. Key options:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `server` | `host` / `port` | `127.0.0.1` / `8000` | Bind address |
| `auth` | `api_key` | `sk-local` | Master API key |
| `auth` | `multi_tenant` | `false` | Per-client keys |
| `cache` | `enabled` / `ttl` | `true` / `300s` | Response cache |
| `rate_limiter` | `enabled` | `true` | Token-bucket rate limits |
| `circuit` | `failures_to_open` | `3` | Breaker threshold |
| `circuit` | `opens_to_blacklist` | `3` | Auto-blacklist after N opens |
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

> When you sell or share this gateway, each customer runs their **own** instance. Their keys and traffic never touch yours.

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

```
GateKeeper/
├── src/
│   ├── api/              # FastAPI server, routes, middleware
│   ├── core/             # Router, fallback, circuit breaker, health
│   └── providers/        # One adapter per upstream provider (12 total)
├── dashboard/            # Streamlit control panel
├── scripts/              # Helper scripts
├── tests/                # pytest suite
├── docs/                 # Documentation
├── config.yaml           # Server configuration
├── models_registry.json  # Model catalog
├── Dockerfile            # Container build
├── docker-compose.yml    # One-command deployment
└── run.bat               # Windows one-click launcher
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's a bug report, documentation improvement, or a new provider adapter — every bit helps.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the development workflow and coding standards.

### Quick Links

- 🐛 [Report a Bug](https://github.com/ahmedeltataw/GateKeeper/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/ahmedeltataw/GateKeeper/issues/new?template=feature_request.md)
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
