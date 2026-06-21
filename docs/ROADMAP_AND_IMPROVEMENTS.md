# GateKeeper — Roadmap, Catalog Expansion & Hardening Plan
> **Status:** Draft for review  
> **Date:** 2026-06-21  
> **Target:** Transform GateKeeper into a production-grade, self-healing gateway of modern free LLMs with zero-budget operation and best-in-class UX for agents.

---

## 0. Executive Summary

GateKeeper already has a strong foundation: 46 verified free models across 10 providers, a Quality Router, 4-tier fallback, circuit breakers, encrypted key vault, and 21/21 passing tests. The next phase focuses on three goals:

1. **Modernize the catalog** — add newly released 2025-2026 frontier models (Gemini 3.x, DeepSeek V4, GLM 5.x, Qwen3, Kimi K2.x, OpenCode Zen models, Groq Compound, etc.) that were missing from the June 2026 verification pass.
2. **Boot-time model probe + auto-quarantine** — at startup, proactively probe every registered model; any model that fails health/smoke tests is automatically disabled (not deleted), so the user never experiences a broken model.
3. **Hardening & competitive edge** — observability, smarter routing, budget tracking, OpenRouter fallback rotation, Streamlit dashboard, auto-sync catalog, and local LLM support via llama.cpp / Ollama-style backends.

All changes must preserve the **zero-cost, no-credit-card** constraint.

---

## 1. New Models Catalog (2025-2026 Additions)

### 1.1 Guiding Principles
- Every model below is **doc-verified as of June 2026** against provider pages / `free-llm-api-resources` (GitHub).
- All are **free-tier, no payment card required**; some have tight rate limits (e.g., GitHub Models CapFree tier = Copilot Free limits).
- Models are grouped by provider. Models with `(NEW)` are missing from today’s `scripts/sync_models.py` and must be added.

### 1.2 Provider-by-Provider Additions

#### Google Gemini (AI Studio)
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `gemini-3.5-flash` | `gemini-3.5-flash` | **S** | **(NEW)** Latest flagship flash; 1M ctx; faster + stronger than 2.5 Pro on most tasks. |
| `gemini-3-flash` | `gemini-3-flash` | **S** | **(NEW)** New generation baseline. |
| `gemini-3.1-flash-lite` | `gemini-3.1-flash-lite` | A | **(NEW)** 500 req/day free; best throughput. |

- **Privacy note:** Gemini free tier trains on data by default outside UK/CH/EEA. Users should opt out or route sensitive traffic to Cloudflare / local.

#### GitHub Models (Copilot Free tier)
| Gateway ID | Provider Model ID | Strength | Tier | Notes |
|------------|-------------------|:--------:|:----:|-------|
| `gh-gpt-5-chat` | `openai/gpt-5-chat` | **S** | High | **(NEW)** 2 RPM / 12 RPD; 4k in / 4k out. |
| `gh-gpt-5-mini` | `openai/gpt-5-mini` | A | High | **(NEW)** 2 RPM / 12 RPD. |
| `gh-gpt-5-nano` | `openai/gpt-5-nano` | B | High | **(NEW)** 2 RPM / 12 RPD. |
| `gh-o4-mini` | `openai/o4-mini` | A | High | **(NEW)** Reasoning model. 2 RPM / 12 RPD. |
| `gh-deepseek-v3-0324` | `deepseek/DeepSeek-V3-0324` | **S** | High | **(NEW)** 1 RPM / 8 RPD. |
| `gh-deepseek-r1-0528` | `deepseek/DeepSeek-R1-0528` | **S** | High | **(NEW)** 1 RPM / 8 RPD. |
| `gh-llama-4-maverick` | `meta/llama-4-maverick-17b-128e-instruct` | A | Low | **(NEW)** 15 RPM / 150 RPD. |

- **Rate limit tiers** come from official GitHub docs:
  - Low: 15 RPM / 150 RPD, 8k/4k tokens, 5 concurrent (Copilot Free).
  - High: 10 RPM / 50 RPD, 8k/4k, 2 concurrent.
- All GPT-5/O4-mini variants are classified **High** tier in the official doc.

#### OpenRouter (:free models)
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `or-nemotron-3-ultra-550b` | `nvidia/nemotron-3-ultra-550b-a55b:free` | **S** | **(NEW)** 550B model. |
| `or-nemotron-3-super-120b` | `nvidia/nemotron-3-super-120b-a12b:free` | **S** | **(NEW)** 120B. |
| `or-qwen3-next-80b` | `qwen/qwen3-next-80b-a3b-instruct:free` | A | **(NEW)** |
| `or-gemma-4-26b` | `google/gemma-4-26b-a4b-it:free` | A | **(NEW)** |
| `or-nemotron-3-nano-30b` | `nvidia/nemotron-3-nano-30b-a3b:free` | B | **(NEW)** |

- OpenRouter free limits: 20 RPM, 50 RPD (shared), raises to 1000 RPD after ≥$10 lifetime top-up.

#### Groq
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `groq-qwen3.6-27b` | `qwen/qwen3.6-27b` | A | **(NEW)** Latest Qwen; 1k req/day, 8k TPM. |
| `groq-compound` | `groq/compound` | A | **(NEW)** Groq flagship reasoning; 250 req/day, 70k TPM. |
| `groq-compound-mini` | `groq/compound-mini` | B | **(NEW)** Smaller reasoning; 250 req/day, 70k TPM. |

#### Cloudflare Workers AI
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `cf-glm-5.2` | `@cf/zai-org/glm-5.2` | A | **(NEW)** Latest GLM. |
| `cf-kimi-k2.7-code` | `@cf/moonshotai/kimi-k2.7-code` | A | **(NEW)** Strong coding. |
| `cf-kimi-k2.6` | `@cf/moonshotai/kimi-k2.6` | A | **(NEW)** General purpose. |
| `cf-gemma-4-26b` | `@cf/google/gemma-4-26b-a4b-it` | A | **(NEW)** |

- Budget: 10,000 neurons/day. Each request costs ~100–500 neurons depending on model size.

#### OpenCode Zen (NEW Provider)
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `oczen-deepseek-v4-flash` | `deepseek-v4-flash-free` | **S** | **(NEW)** High-tier reasoning+chat. |
| `oczen-nemotron-3-super` | `nemotron-3-super-free` | **S** | **(NEW)** 120B. |
| `oczen-big-pickle-stealth` | `big-pickle-stealth` | A | **(NEW)** General. |

- Base: `https://opencode.ai/v1` (OpenAI-compatible).
- No card. Free tier allows data usage for improvement (standard Zen policy).
- Requires an OpenCode account (free sign-up).

#### Qwen / Zhipu GLM (Z.ai)
| Gateway ID | Provider Model ID | Strength | Notes |
|------------|-------------------|:--------:|-------|
| `glm-5.2-flash` | `glm-5.2-flash` | A | **(NEW)** Follow-up to 4.7. |
| `glm-5.2-air` | `glm-5.2-air` | B | **(NEW)** Lightweight. |

### 1.3 Consolidated "NEW" list in one view
- `gemini-3.5-flash`, `gemini-3-flash`, `gemini-3.1-flash-lite`
- `gh-gpt-5-chat`, `gh-gpt-5-mini`, `gh-gpt-5-nano`, `gh-o4-mini`, `gh-deepseek-v3-0324`, `gh-deepseek-r1-0528`, `gh-llama-4-maverick`
- `or-nemotron-3-ultra-550b`, `or-nemotron-3-super-120b`, `or-qwen3-next-80b`, `or-gemma-4-26b`, `or-nemotron-3-nano-30b`
- `groq-qwen3.6-27b`, `groq-compound`, `groq-compound-mini`
- `cf-glm-5.2`, `cf-kimi-k2.7-code`, `cf-kimi-k2.6`, `cf-gemma-4-26b`
- `oczen-deepseek-v4-flash`, `oczen-nemotron-3-super`, `oczen-big-pickle-stealth`
- `glm-5.2-flash`, `glm-5.2-air`

---

## 2. Boot-Time Model Probing & Auto-Quarantine

### 2.1 Problem Statement
Today `models_registry.json` contains doc-verified free models. In practice, providers rotate `:free` model IDs weekly, and an individual user’s key may lack access to some models. At 3 AM on a Tuesday, an Agent calls `"model": "auto"` and routes to a 404/401 → user gets a failure. We want failures to happen at gateway boot, not during the user’s workflow.

### 2.2 Design: Two-Level Probe

#### Level A — Provider Health Check (already exists)
- Current `health.py` loops through providers every `_CHECK_INTERVAL_SECONDS = 300`.
- It marks a provider `HEALTHY / RATE_LIMITED / INVALID / ERROR`.
- This is a **reachability** check (typically a `list_models` or tiny ping).

#### Level B — Model Smoke Test (NEW)
At startup (and optionally nightly), send a tiny **model-specific** smoke test for every model in `models_registry.json`:

- Request: minimal chat completion (`"Say OK"`), `max_tokens=4`.
- Success = HTTP 200 + non-empty choices[0].message.content.
- Failure = 404, 401, 403, 429, 5xx, timeout, or empty response.

Success/failure is recorded in SQLite circuit breaker state (`circuit.py`): after **3 consecutive failures**, a model is **blacklisted** (automatic). It is only unblacklisted by a successful probe or manual admin reset.

```
┌──────────────────────────────────────────────────────────────────────┐
│ On Gateway Startup                                                    │
│                                                                       │
│  for each model_id in models_registry.json:                          │
│    try:                                                               │
│      send tiny chat completion (max_tokens=4)                         │
│      if 200 + content: record_success(model)                          │
│    except 401/404/429/5xx/timeout:                                   │
│      record_failure(model)                                            │
│                                                                       │
│  after loop:                                                          │
│    publish /v1/models (only models with breaker state == closed)    │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Code Changes Required

#### a. Add `src/core/smoke.py`
```python
async def smoke_test_model(model_id: str, timeout: float = 5.0) -> bool:
    """Return True if the model returns a non-empty completion from a tiny prompt."""
    ...
```

#### b. Add `src/core/probe.py`
```python
async def probe_all_models(concurrency: int = 3) -> dict[str, bool]:
    """Run smoke tests for the entire catalog at startup. Update circuit breakers."""
    ...
```

#### c. Add toggle to `config.yaml`
```yaml
probe:
  enabled: true
  concurrency: 3
  timeout_seconds: 5
  max_consecutive_failures: 3        # auto-blacklist threshold
  prompt: "Reply with the single word: OK"
  max_tokens: 4
```

#### d. Wire into `server.py` lifespan
```python
if get_config().probe.enabled:
    await probe_all_models(concurrency=get_config().probe.concurrency)
```

### 2.4 UX Behavior
- `/v1/models` only returns models whose breaker state is `closed` (or not-yet-tested = closed by default).
- `/health` includes a `catalog_probe` field: `{ "probed": 46, "healthy": 44, "blacklisted": 2 }`.
- If a user’s key is missing, that provider is marked `INVALID`; its models are skipped but not deleted.
- Admin Dashboard shows “Quarantined Models” with reason and a one-click “Retry Now”.

### 2.5 Operational Notes
- **Running the probe consumes rate budget.** Keep concurrency low (3–5) and timeout tight (5s).
- **Rate-limited providers** should be probed last / skipped if already `RATE_LIMITED` from health check.
- **OpenRouter `:free` rotations:** If a model 404s on Monday, the health check will catch it at the next interval anyway; the boot probe accelerates discovery.

---

## 3. Strategic Improvements & Competitive Edge

### 3.1 Observability & Telemetry
- **Per-request latency + token logging** into SQLite (`usage` table).
- `/metrics` endpoint (Prometheus format) exposing:
  - Per-provider success rate, avg latency, last-error.
  - Per-model request count, token count.
  - Circuit-breaker state distribution.
- Structured JSON logs with trace id for correlating fallback events.

### 3.2 Smarter Quality Router
- Introduced a **per-model confidence score** derived from:
  - Recent success rate (from circuit + usage).
  - Average latency (from `health._provider_analytics`).
  - User preference overrides (configurable `task_type` → explicit model).
- Adjust `_PREFERRED_CHAINS` dynamically:
  - A model that has 3 failures in the last hour drops one slot.
  - If all preferred models are degraded, fall back to the highest-success-rate active model for that task type.

### 3.3 OpenRouter “Free Fallback” Rotation
- OpenRouter `:free` models change weekly.
- Add a **pseudo-model** `or-free-auto` backed by OpenRouter’s `/chat/completions` with `model: "openrouter/free"` — this lets OpenRouter’s own router pick the best available free model at request time.
- GateKeeper still tracks individual `or-*` models for health; `or-free-auto` acts as a pressure valve.

### 3.4 Budget & Quota Tracking
- Track per-provider daily RPM/RPD counters in SQLite.
- If a provider is within 80% of its daily limit, mark it `BUDGET_WARNING`; at 100%, mark `RATE_LIMITED`.
- This prevents running into hard 429s unexpectedly.

### 3.5 Catalog Auto-Sync
- Add a scheduled job (via Python `schedule` or OS cron) that:
  1. Pulls the latest `free-llm-api-resources/README.md` from GitHub.
  2. Compares it to the local `models_registry.json`.
  3. Opens a PR / writes a `docs/internal/models-diff.md` with additions/removals.
  4. Optionally auto-runs `python scripts/sync_models.py` if the user enables `catalog.auto_sync = true`.

### 3.6 Local Model Support (llama.cpp / Ollama)
- Add a `local` provider binding to `http://localhost:11434/v1` (Ollama) or a llama.cpp server.
- Benefits:
  - **Zero-cost + zero-privacy-risk** inference.
  - Offline-ready.
  - Unlimited personal usage.
- Models hosted locally should be discoverable via the same `/v1/models` and Quality Router.
- Suggested initial local models:
  - `llama-3.3-70b-instruct` (needs ~40 GB VRAM / 80 GB RAM).
  - `qwen2.5-coder-32b` (good quality/VRAM trade-off).
  - `deepseek-r1-distill-32b` (reasoning).

### 3.7 Streamlit Dashboard (completion)
- Current `dashboard/` folder exists but needs to be finished.
- Pages:
  - **Home:** request volume, top models, success rate.
  - **Providers:** per-provider health, budget, keys (masked).
  - **Models:** model list, force enable/disable, retry blacklisted.
  - **Logs:** recent requests, fallback events, errors.
- Add “Retry Blacklisted” and “Enable/Disable” buttons with immediate effect (no restart).

### 3.8 Streaming Completeness
- Today, only Gemini has a proven streaming implementation.
- For all OpenAI-compatible providers, reuse the `/chat/completions?stream=true` contract.
- Add a `stream=True` smoke test in the boot probe for providers that advertise streaming support.

### 3.9 Multi-Account Provider Support (e.g., GitHub Models)
- Some users have multiple GitHub PATs (personal + org).
- Allow `providers.github_models[0]`, `providers.github_models[1]` entries in `config.yaml` for round-robin / budget spreading.

### 3.10 Security Hardening
- Key vault: already AES-256-GCM; add **key rotation** reminder after 90 days.
- Rate limiter: add per-IP quotas in front of the gateway to prevent abuse.
- CORS: default to `["http://localhost:3000"]` in production mode, `["*"]` only in dev.

---

## 4. Implementation Timeline (2-Week Sprint)

| Week | Deliverable | Owner (suggested) |
|------|-------------|-------------------|
| 1 | Add all NEW models to `sync_models.py`, `models-classification.md`, `quality_router.py`. Run `sync_models.py`. | Code |
| 1 | Add OpenCode Zen provider (`src/providers/oc_zen.py`). | Code |
| 2 | Implement `src/core/smoke.py` + `src/core/probe.py` + config toggle + server wiring. | Code |
| 2 | Streamlit dashboard refresh (model management, retry, enable/disable). | UI |
| 2 | Observability: `/metrics` + structured logs + latency histograms. | Infra |
| 2 | Budget tracker: per-provider RPM/RPD counters + `BUDGET_WARNING` status. | Infra |
| 3 | Catalog auto-sync cron job + `models-diff.md` generator. | Ops |
| 3 | Local-model provider (`llama.cpp` / Ollama) + sample config. | Platform |
| 4 | OpenAI-compatible streaming for all remaining providers + smoke test. | Code |
| 4 | Performance benchmark suite (latency, tokens/sec, success rate). | QA |

---

## 5. Acceptance Criteria

- [ ] Catalog contains **≥70 verified free models** across **≥12 providers**.
- [ ] Boot smoke test probes every model within 60 seconds of startup; broken models are not exposed via `/v1/models`.
- [ ] At least one provider is **privacy-preserving** (Cloudflare or local) and is prioritized for sensitive task types.
- [ ] `/health` returns per-provider + per-model health, probe status, and budget utilization.
- [ ] Quality Router uses dynamic scoring (recent success rate + latency).
- [ ] Dashboard allows enable/disable/retry with no restart.
- [ ] All new features are controlled by `config.yaml` toggles; zero breaking changes to existing deployments.

---

## 6. References & Sources

- `free-llm-api-resources` maintained by **cheahjs** (source of truth for free-tier model lists): https://github.com/cheahjs/free-llm-api-resources
- GitHub Models rate limits and tier definitions: https://docs.github.com/en/github-models/prototyping-with-ai-models#rate-limits
- OpenRouter free models: https://openrouter.ai/models?order=top-weekly&q=:free
- Google AI Studio free tier: https://aistudio.google.com/apikey
- Groq model list + limits: https://console.groq.com/docs/models
- Cloudflare Workers AI pricing (10k neurons/day free): https://developers.cloudflare.com/workers-ai/platform/pricing/
- OpenCode Zen (free models): https://opencode.ai/docs/zen/
- Zhipu / Z.ai GLM models: https://z.ai/manage-apikey/apikey-list
- Cerebras free tier: https://cloud.cerebras.ai/
- Mistral Experiment tier: https://console.mistral.ai/
- NVIDIA NIM free prototyping: https://build.nvidia.com/

---

*Plan authored by Hermes Agent, June 21, 2026.*
