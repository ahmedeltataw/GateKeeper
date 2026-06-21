# UX Improvement Plan — Agent Integration & Onboarding
> **Status:** Proposed  
> **Date:** 2026-06-21  
> **Author:** Hermes Agent  
> **Scope:** Reduce integration friction from `git clone → running gateway → connecting agents` from ~8 manual steps to 1 click or 1 copy-paste.

---

## 1. Problem Statement

GateKeeper is already functional: 46 verified free models, OpenAI-compatible `/v1/chat/completions`, health checks, circuit breakers, and `"model": "auto"` routing.  
But the **last-mile UX** is painful for the exact target audience — developers who clone the repo, run it locally, and expect to plug it into their existing agent toolchain (OpenCode, Hermes, Claude Code, Continue.dev, Cursor, custom scripts).

### Current flow (friction map)
1. Clone repo + `pip install`  
2. Create/verify `.env` + `ENCRYPTION_KEY`  
3. Add provider API keys to `.env`  
4. Run `python scripts/sync_models.py`  
5. Start `uvicorn`  
6. Open browser to dashboard to verify `sk-local`  
7. **Manually determine:** gateway URL, API key, model ID  
8. **Per agent:** OpenCode → env vars; Hermes → custom `config.yaml`; Claude Code → env vars  
9. Model ID trial-and-error: `"auto"` or `/v1/models` lookup  
10. CORS / auth mismatch debugging if something fails

### Pain points
| Pain | Impact | Frequency |
|------|--------|-----------|
| "Where do I put the API key for my agent?" | Blocks first successful request | 100% |
| "Which model ID do I use?" | Users guess `auto` or retry with wrong model | 70% |
| "Is CORS blocking me?" | Silent 403/network errors from VS Code extensions | 40% |
| "How do I connect [Agent X]?" | User must extrapolate from generic README | 60% |
| Remote connectivity | Agents on another machine can't reach `127.0.0.1` | 20% |

**Goal:** Make onboarding to "first successful request from an agent" **under 30 seconds** after boot.

---

## 2. Design Principles

1. **Agent-first, not gateway-first.** The gateway is infrastructure; the user cares about their agent.
2. **One source of truth.** Gateway publishes its own connection info; agents consume it.
3. **Opt-in, not opinionated-heavy.** Don't force a specific agent; generate snippets for the user's choice.
4. **Local-first, cloud-optional.** Default to `127.0.0.1`, but provide a one-liner for tunneling/proxying when needed.
5. **Documented by code.** Every snippet must be generated from actual working examples, not typed by hand.

---

## 3. Solution Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ GateKeeper Gateway                                               │
│                                                                  │
│  GET /v1/models            ← standard OpenAI catalog            │
│  GET /v1/connection-info   ← NEW: base URL, api key, model IDs  │
│  GET /v1/agent-snippet?agent=opencode  ← NEW: agent config       │
│                                                                  │
│  Dashboard → Integrations page                                   │
│    • Copy-paste blocks for OpenCode, Hermes, Claude Code         │
│    • One-command shell setup                                    │
│    • Remote access guide with mkcert + caddy/nginx example       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
     Agent A             Agent B              Agent C
   (OpenCode)          (Hermes)           (Claude Code)
```

---

## 4. New Features (Proposed)

### 4.1 `GET /v1/connection-info` (Backend API)
Return a self-describing JSON document that answers "how do I talk to this gateway?" without reading docs.

```json
{
  "gateway": {
    "base_url": "http://127.0.0.1:8000/v1",
    "api_key": "sk-local",
    "auth_enabled": true,
    "cors_origins": ["*"]
  },
  "models": {
    "default": "auto",
    "list_url": "/v1/models",
    "sample_ids": [
      "auto",
      "gemini-2.5-flash",
      "groq-openai/gpt-oss-120b",
      "nvidia/llama-3.1-405b-instruct"
    ]
  },
  "agents": {
    "opencode": { "type": "env", "vars": { "OPENAI_BASE_URL": "http://127.0.0.1:8000/v1", "OPENAI_API_KEY": "sk-local" } },
    "claude-code": { "type": "env", "vars": { "ANTHROPIC_BASE_URL": "http://127.0.0.1:8000", "ANTHROPIC_API_KEY": "sk-local" } },
    "hermes": { "type": "config", "path": "config.yaml", "provider": "openai", "base_url": "http://127.0.0.1:8000/v1" }
  },
  "notes": [
    "Use `auto` to let the Quality Router pick the best available model.",
    "For remote access, see /v1/agent-snippet?agent=remote-guide"
  ]
}
```

**Why this endpoint?**
- Self-documenting — the gateway tells you how to connect to it.
- Discoverable via tooling: `curl http://127.0.0.1:8000/v1/connection-info | jq`.
- Eliminates README hunting for env var names and model IDs.

### 4.2 `GET /v1/agent-snippet?agent=<name>` (Backend API)
Return a ready-to-use bash snippet (or JSON) tailored for the requested agent.

Example response for `agent=opencode`:
```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=sk-local
opencode --model auto
```

Example for `agent=hermes`:
```yaml
# Add this to your Hermes config.yaml custom providers:
providers:
  gatekeeper:
    base_url: http://127.0.0.1:8000/v1
    api_key: sk-local
```

**Supported agents (Phase 1):**
- `opencode`
- `hermes`
- `claude-code`
- `cursor` / `continue-dev` (VS Code extensions)
- `custom-script` (generic curl/python)

**Supported formats:** `text` (bash snippet) and `json` (structured config).

### 4.3 Interactive CLI: `python scripts/setup_agents.py` (Client-side)
A guided wizard that:
1. Asks which agents the user wants to configure.
2. Detects existing agent config files (`.config/opencode/config.json`, `.hermes/config.yaml`, etc.) if possible.
3. Generates and **optionally appends** the correct config to those files.
4. Prints the snippet to stdout for review.

Example session:
```bash
$ python scripts/setup_agents.py
🔌 GateKeeper Agent Integration Setup
✔ Detected gateway running at http://127.0.0.1:8000
✔ API key: sk-local

Which agents do you want to configure?
  ◉ OpenCode
  ◉ Hermes
  ◉ Claude Code
  ○ None (just show me snippets)

✔ Wrote ~/.config/opencode/config.json
✔ Appended provider block to ~/.hermes/config.yaml

✅ Done! Restart your agent to use GateKeeper.
```

**Safety:** never overwrite existing configuration; always append to a clearly marked section (e.g., `<!-- GATEKEEPER_BEGIN -->`).

### 4.4 Backend Integration: Auto-CORS + Auth header hints
Many VS Code extensions fail because of CORS. Improve the default onboarding by:
- When `dashboard.enabled = true` and the gateway is accessed from a browser on a different port, log a helpful message: "CORS is allowing *; if you are hitting issues, restrict `config.yaml`."
- In `/v1/connection-info`, return `cors_origins` so the user knows if their agent's origin is blocked.
- Support a `X-API-Key` header recommendation in snippets (some agents prefer it over `Authorization: Bearer`).

### 4.5 Dashboard “Integrations” Page
Add `dashboard/pages/06_integrations.py` with:
- One-click copy buttons for each agent.
- A shell command block that prints the correct env setup based on the user's gateway URL.
- A "Test Connection" button per agent type that sends a tiny chat completion to the gateway and reports success/failure.

This page is for users who prefer GUI and might not read the README.

---

## 5. Implementation Roadmap (2-Week Sprint)

| Week | Task | Deliverable | Effort |
|------|------|-------------|--------|
| **1** | Add `/v1/connection-info` endpoint | `src/api/routes.py` + test | 4h |
| **1** | Add `/v1/agent-snippet` endpoint | `src/api/routes.py` + snippet library | 6h |
| **1** | Add `scripts/setup_agents.py` wizard | Interactive CLI, `writers/opencode.py`, `writers/hermes.py` | 8h |
| **2** | Build Dashboard Integrations page | `dashboard/pages/06_integrations.py` | 6h |
| **2** | CORS hardening + `X-API-Key` support | `src/api/routes.py` | 2h |
| **2** | Update README + STATUS_AND_SETUP.md | First-screen UX rewrite | 3h |
| **2** | Add "Start Here" badge to repo README.md | `![Start Here]` callout | 1h |

**Total:** ~30 hours of implementation.

---

## 6. Agent-Specific Details

### 6.1 OpenCode CLI
**Integration method:** Environment variables or config file.  
**How the snippet looks:**
```bash
# Option A: one-liner
OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_API_KEY=sk-local opencode --model auto

# Option B: persistent (writes to ~/.config/opencode/config.json if present)
```
**Notes:** OpenCode sends `model` as the OpenAI model string. GateKeeper accepts `"auto"` and routes via Quality Router. Streaming is also supported.

### 6.2 Hermes Agent
**Integration method:** `custom_providers` in `config.yaml`.  
**How the snippet looks:**
```yaml
custom_providers:
  gatekeeper:
    base_url: http://127.0.0.1:8000/v1
    api_key: sk-local
```
**Notes:** Hermes will auto-discover models via `/v1/models` because it supports OpenAI-compatible provider discovery. User selects `gatekeeper/auto` or `gatekeeper/<model-id>`.

### 6.3 Claude Code CLI
**Integration method:** Environment variables.  
**How the snippet looks:**
```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:8000
export ANTHROPIC_API_KEY=sk-local
claude --model auto
```
**Notes:** Claude Code respects `ANTHROPIC_BASE_URL` for compatibility layers. GateKeeper's `/v1/chat/completions` is exposed under `/` when using the Anthropic-compatible translation layer, OR directly via `/v1/chat/completions` using OpenAI client mode depending on the Claude Code version. The snippet should note to use **OpenAI provider mode** if the Anthropic adapter is less tested.

### 6.4 Continue.dev / Cursor / Windsurf
**Integration method:** Settings UI → "Custom OpenAI Base URL".  
**How the snippet looks:**
```
Base URL: http://127.0.0.1:8000/v1
API Key: sk-local
Model: auto
```
**Notes:** Cursor and Continue.dev both have "Add Custom Provider" UI. Provide a direct link or QR code to the dashboard's Integrations page.

### 6.5 Custom Scripts
**Snippet guidance:**
```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="sk-local")
response = client.chat.completions.create(model="auto", messages=[...])
```
Also provide a `curl` example.

---

## 7. Remote / Multi-Machine Access (Optional but valuable)

Many users run the gateway on a home server or a cloud VM and want agents on their laptop to use it. Current `server.host = 127.0.0.1` blocks this.

### Minimal steps for remote access
1. Guide user to set `HOST=0.0.0.0` and `PORT=8000` in `.env`.
2. Provide a `caddy reverse-proxy` Caddyfile sample with automatic HTTPS via `mkcert` for local trusted LAN access:
```
https://gatekeeper.local:8443 {
  reverse_proxy http://127.0.0.1:8000
  tls internal
}
```
3. Alternatively, a `ssh -R` one-liner: `ssh -R 8080:localhost:8000 user@server`.
4. In `/v1/connection-info`, add a `remote` section when `host` is not loopback.

**Security note:** Document that 0.0.0.0 exposes the gateway to the LAN and that `ADMIN_TOKEN` should be set before doing this.

---

## 8. safeguards & Edge Cases

| Risk | Mitigation |
|------|------------|
| Wizard overwrites existing agent config | Wizard only *appends* inside a clearly delimited comment block; dry-run mode shows diff first. |
| User runs wizard before starting gateway | Endpoint `/v1/connection-info` returns a clear error; wizard explains "Start GateKeeper first." |
| CORS blocks agent extension | Dashboard explains CORS origin mismatch; suggests setting `cors_origins: ["*"]` temporarily for development. |
| Model ID confusion | Default to `auto` everywhere; only expose specific model IDs if the user opts into "Advanced." |
| Remote access security | README prominently says: "If you bind to `0.0.0.0`, set `ADMIN_TOKEN` immediately." |

---

## 9. Metrics for Success

These KPIs measure whether the UX improvement actually helped:

| KPI | Current (est.) | Target |
|-----|---------------|--------|
| Time to first successful agent request | ~10 min | < 30 sec |
| "Which agent do you use?" question in Discord/GitHub | ~5/week | 0 (answer is in docs) |
| Failed integrations due to CORS | Unknown (silent) | Logged + resolved via dashboard |
| README → first integration conversion | ~30% | > 70% |

---

## 10. References & Patterns

- **LiteLLM**: Uses `litellm --model` and generates proxy configs. Our approach mirrors their "proxy + agent snippets" pattern but stays local-first.
- **Open WebUI**: Provides "API Endpoint" copy-paste for ChatGPT clients.
- **Open Router**: Shows "Usage" as a single curl/env block.
- **LangChain**: Their docs show "Configure as OpenAI-compatible endpoint" for custom LLM providers.

We should position GateKeeper as the **"zero-config local OpenAI aggregator"** — the analog of `ollama` but for hosted free APIs instead of local weights.

---

## 11. Out of Scope (Future)

- **Plugin system for agents.** Allow agents to query GateKeeper's `/v1/models` and auto-select models (a true gateway-aware agent plugin).
- **One-click onboarding inside Hermes UI.** Beyond a docs page.
- **Agent usage analytics** in the dashboard (which models each agent prefers).
- **Auto-provisioned docker-compose** that includes nginx/caddy for remote access.

---

*Plan authored by Hermes Agent, June 21, 2026.*
