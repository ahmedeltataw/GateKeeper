# 🏗️ Personal GateKeeper — Implementation Plan (Self-Contained)

> **Purpose:** This single file is the complete, self-contained implementation spec. It consolidates ALL details from `docs/` + `models-classification.md` + `README.md` so implementation can start immediately even after the source docs are deleted.
> **Project root:** `D:\ai-project\free models`
> **Language/Stack:** Python 3.11+ / FastAPI + httpx + Pydantic (lightweight, stdlib-leaning)
> **Mode:** Single-user, personal, zero-cost (free provider tiers only)
> **Last consolidated:** 2026-06-17

---

## 0. Mission & Principles

**Problem:** 12+ providers offer free LLMs, each with a different API, auth, and rate limits. Agents support only one custom provider at a time.

**Solution:** One unified OpenAI-compatible gateway: `Agent → http://localhost:8000/v1 → Gateway → best available provider`.

**Core principles (must hold in code):**
| Principle | Implementation |
|-----------|----------------|
| 🧩 Modular | Each provider = one file `src/providers/<name>.py`, add/remove without touching others |
| 🔁 Fail-First | 4-tier fallback chain; failure → immediately try alternative |
| 📊 Data-Driven | `models-classification.md` → `models_registry.json` → in-memory Registry |
| 💸 Zero Cost | Free tiers only, no card |
| 🪶 Lightweight | FastAPI + httpx + stdlib only |
| 🔌 OpenAI Compatible | `/v1/chat/completions` exact OpenAI format |
| 🔒 Key Security | AES-256-GCM keys stored in SQLite, never plain text |
| 🔄 State Awareness | Sticky sessions (30 min) + context handoff on model switch |

**Scope:**
- Supports: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`
- Optional/later: `POST /v1/responses` (Codex CLI compat — same body/response as chat completions)
- NOT supported: image gen, audio, embeddings (maybe later)

---

## 1. Final Directory Structure

```
D:\ai-project\free models\
├── README.md
├── models-classification.md          # Source of truth (kept; data below mirrors it)
├── IMPLEMENTATION_PLAN.md            # this file
│
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py                # FastAPI app, startup/shutdown, CORS
│   │   ├── routes.py                # endpoints
│   │   └── middleware.py            # CORS, Logging, Auth (Bearer)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── router.py                # Model → Provider router
│   │   ├── quality_router.py        # task_type → best model (UNIQUE FEATURE)
│   │   ├── fallback.py              # 4-tier fallback engine + context handoff
│   │   ├── rate_limiter.py          # Token Bucket per provider
│   │   ├── cache.py                 # Response cache (TTL)
│   │   ├── registry.py             # In-memory model registry
│   │   ├── config_loader.py         # reads config.yaml
│   │   └── key_manager.py           # AES-256-GCM key store (SQLite)
│   └── providers/
│       ├── __init__.py             # provider discovery/factory
│       ├── base.py                 # BaseProvider ABC + ProviderConfig
│       ├── openrouter.py
│       ├── gemini.py               # needs format translation
│       ├── groq.py
│       ├── mistral.py
│       ├── github_models.py
│       ├── nvidia.py
│       ├── cerebras.py
│       ├── cloudflare.py           # needs format translation (neurons)
│       ├── zhipu.py
│       ├── huggingface.py
│       ├── aion.py
│       └── cohere.py
│
├── scripts/
│   ├── test_gateway.sh
│   └── sync_models.py              # models-classification.md → models_registry.json
│
├── tests/
│   ├── conftest.py
│   ├── test_router.py
│   ├── test_fallback.py
│   ├── test_providers.py
│   └── test_rate_limiter.py
│
├── server/data/                    # runtime (gitignored): gateway.db, rate_limits.json
├── models_registry.json            # generated cache from sync_models.py
├── requirements.txt
├── config.yaml
├── .env                            # gitignored
├── .gitignore
├── Dockerfile
└── docker-compose.yml
```

---

## 2. Data Models / Schemas

### 2.1 `ModelInfo` (dataclass + Registry source)
```python
@dataclass
class ModelInfo:
    # Identity (required)
    id: str                      # "codestral" (pattern ^[a-z0-9.-]+$ — dots allowed, e.g. gemini-3.5-flash; used in API)
    display_name: str            # "Codestral"
    provider_id: str             # "mistral"
    provider_model_id: str       # "codestral-latest" (id provider expects)
    # Classification
    strength: str                # "S"|"A"|"B"|"C"
    strength_order: int          # S=0, A=1, B=2, C=3
    use_cases: list[str]         # subset of: coding, search, reasoning, creative, data, vision, audio, default (minItems 1)
    category: str                # general|coding|reasoning|creative|vision
    # Capabilities
    context_window: int          # >=4096
    max_output_tokens: int       # >=1024
    modalities: list[str]        # default ["text"]; enum: text,image,audio,video
    pricing: dict | None         # {"input":0,"output":0} per million; 0=free
    # Limits (>=1 key present): rpm,rpd,tpm,rps,tpd,neurons,concurrent
    rate_limits: dict
    # Status
    enabled: bool                # default True
    status: str                  # active|deprecated|removed|pending_verification
    # Fallback
    fallback_models: list[str]   # ordered, same strength or lower
    # Metadata
    notes: str | None
    source_url: str | None
    added_at: str                # date
    removed_at: str | None       # default None
    last_verified: str           # date
    verification_source: str | None  # manual_test|api_check|community_report
```
Registry JSON = array of these objects. Required keys: `id, display_name, provider_id, provider_model_id, strength, use_cases, context_window, max_output_tokens, enabled, status, added_at, last_verified`.

### 2.2 `ChatRequest` (POST /v1/chat/completions body)
- Required: `model` (string), `messages` (array, minItems 1)
- `messages[].role`: `system|user|assistant|tool`; `content`: string; optional `name`, `tool_calls`, `tool_call_id`
- `tool_calls[]`: `{id, type:"function", function:{name, arguments(string)}}`
- Optional params + defaults: `temperature`=0.7 (0–2), `max_tokens`=2048 (≥1), `stream`=false, `top_p`=1, `frequency_penalty`=0 (−2..2), `presence_penalty`=0 (−2..2), `stop`=null (string|array|null)
- **Extension:** `task_type` ∈ {coding, search, reasoning, creative, data, vision, default} — Quality Router hint
- **Extension:** `model: "auto"` → gateway picks best model by `task_type`

### 2.3 `ChatResponse` (non-streaming)
- Required: `id` (`^chatcmpl-[a-z0-9]+$`), `object`="chat.completion", `created` (unix int), `model`, `choices`, `usage`
- `choices[]`: `{index, message:{role:"assistant", content:string|null, tool_calls?, refusal?}, finish_reason: stop|length|tool_calls|content_filter|error}`
- `usage`: `{prompt_tokens, completion_tokens, total_tokens}`
- **Extension fields:** `provider` (string), `fallback_used` (bool), `original_model` (string), `fallback_chain` (string[], optional)

### 2.4 Streaming response (SSE)
- `object`="chat.completion.chunk", `choices[].delta` carries incremental content
- `role:"assistant"` only in first chunk; final chunk `delta:{}` + `finish_reason:"stop"`; terminate with `data: [DONE]`
- If fallback occurs mid-stream: stream ends and returns error chunk `data: {"error":{...}}`

### 2.5 Provider Metadata schema
`{id, name, base_url, api_format(openai_compatible|partial|custom), requires_card(bool), auth_type(bearer|query_param|custom), data_training_policy(no_training|opt_out_available|may_use_for_training|unknown), commercial_use_allowed(bool), rate_limits{...}, signup_url, docs_url, notes, last_verified}`

### 2.6 Registry query API (in-memory)
```python
registry.get_by_strength("A")
registry.get_by_use_case("coding")
registry.get_best_for_task("coding")
registry.get_by_provider("mistral")
registry.get_active()
registry.search("nemotron")
```

---

## 3. API Contract

Base URL: `http://localhost:8000/v1` (local: `127.0.0.1`; network: `your-ip:8000`).
Auth: `Authorization: Bearer sk-local` on all except `/health`. If `auth.enabled:false`, header not required.

### 3.1 `GET /v1/models`  (and `?task_type=coding` filter)
Returns `{object:"list", data:[ {id, object:"model", created, owned_by, permission:[], root, parent:null}, ... ]}`.
Extended fields per model: `strength, provider, use_cases, context_window, max_output, rate_limits`.

### 3.2 `POST /v1/chat/completions`
Body = §2.2, response = §2.3 (or SSE §2.4). Adds `provider`, `fallback_used`, `original_model` to response.

### 3.3 `POST /v1/responses`
Codex CLI compatibility — identical body & response to chat completions.

### 3.4 `GET /health`
```json
{"status":"healthy","version":"1.0.0",
 "providers":{"openrouter":"healthy","gemini":"healthy","groq":"rate_limited","mistral":"healthy"},
 "uptime_seconds":3600,"requests_total":1500,"requests_last_hour":50,
 "cache_hits":120,"fallback_count":5}
```
Provider statuses: `healthy | rate_limited | invalid | error | unknown`.

### 3.5 Errors
| HTTP | type | When |
|:---:|------|------|
| 400 | invalid_request_error | bad body (missing model/messages) |
| 401 | authentication_error | auth failed / missing key |
| 404 | not_found | model not in registry |
| 429 | rate_limit_error | all providers rate-limited |
| 500 | api_error | internal error |
| 503 | service_unavailable | no healthy providers |

Error body:
```json
{"error":{"message":"Model 'xyz' not found. Available models: ...","type":"not_found","code":404,"param":"model","doc_url":"http://localhost:8000/v1/models"}}
```
Streaming errors emitted as `data: {"error":{"message":"...","type":"..."}}`.

---

## 4. Request Flow (canonical happy path)
1. Agent → `POST /v1/chat/completions`
2. Middleware: Auth (Bearer check) → Log `{time, ip, model, task_type}` → CORS headers
3. **Quality Router**: resolve `task_type` → candidate models (filter by use_case, enabled, active) → sort by strength → pick best with budget
4. **Model Router**: model → provider_id; ask Rate Limiter
5. **Rate Limiter**: token bucket check/deduct; if empty → Fallback
6. **Key Manager**: fetch encrypted key, AES-256-GCM decrypt in memory
7. **Provider**: build HTTP request (provider format) → httpx POST
8. Receive → translate to OpenAI format → add metadata (`provider`, latency, fallback)
9. **Cache**: store if enabled (TTL 5 min)
10. Log `{model, provider, tokens, latency, success}`
11. Return 200 OpenAI-format JSON

---

## 5. Quality Router (UNIQUE FEATURE)
Select strongest model that fits the task AND still has budget.
```python
async def select_best_model(task_type, available_models):
    candidates = [m for m in available_models
                  if task_type in m.use_cases and m.enabled and m.status == "active"]
    strength_order = {"S":0,"A":1,"B":2,"C":3}
    candidates.sort(key=lambda m: strength_order.get(m.strength, 99))
    for model in candidates:
        provider = get_provider(model.provider_id)
        if await rate_limiter.allow(provider, model):
            return model
    return await fallback_any()
```
**task_type → preferred models (priority order):**
| task_type | preferred chain |
|-----------|-----------------|
| coding | Codestral → Nemotron 3 Ultra → DeepSeek V4 Flash |
| search | Gemini 3.5 Flash → Nemotron 3 Ultra → Llama 3.3 |
| reasoning | Gemini 2.5 Pro → DeepSeek R1 → Magistral |
| creative | Claude 3.5 Sonnet → GPT-4o → MiniMax M2.5 |
| data | GPT-4o → Mistral Large → Command A+ |
| vision | Gemini 3.5 Flash → Pixtral Large → GLM-4.6V |
| default | Gemini 3.5 Flash (S-tier general) |

If `model:"auto"` → choose by task_type. If explicit model → task_type is a hint.

---

## 6. Fallback Engine (4 tiers)
```python
COOLDOWN = {"429":60, "5xx":30, "timeout":0, "401":None, "404":None}  # seconds; None=permanent
```
| Code | Reason | Cooldown | Action |
|------|--------|:---:|--------|
| 429 | rate limit | 60s | try next model immediately |
| 5xx | server error | 30s | mark unhealthy, try other |
| timeout | >30s slow | 0 | try alternative |
| 401 | bad key | permanent | disable key |
| 404 | model removed | permanent | mark "removed" in registry |

**Tiers:**
1. Same model, different provider (if model offered by multiple providers)
2. Same strength, different model (A → other A models)
3. One step lower (A → B)
4. Last resort: any available model with budget

On Tier ≥2 switch, inject **Context Handoff** and set `fallback_used=true`, fill `original_model` / `fallback_chain`.

```python
async def try_with_fallback(request, task_type):
    preferred = await select_best_model(task_type, registry.models)
    if not preferred: raise NoModelAvailableError("No suitable model found")
    # Tier 1: same model across its providers
    for provider in get_providers_for_model(preferred.id):
        if not rate_limiter.allow(provider, preferred): continue
        try: return await provider.chat(request)
        except ProviderError as e:
            await rate_limiter.cooldown(provider, COOLDOWN.get(e.code, 30)); continue
    # Tier 2: same strength
    for model in registry.get_by_strength(preferred.strength):
        if model.id == preferred.id: continue
        for provider in get_providers_for_model(model.id):
            if not rate_limiter.allow(provider, model): continue
            try:
                resp = await provider.chat(request)
                return add_context_handoff(resp, preferred.id, model.id)
            except ProviderError: continue
    # Tier 3 (lower) then Tier 4 (any) ...
```

---

## 7. Sticky Sessions + Context Handoff
```python
session_cache = {}  # session_id -> {"model_id":..., "time":...}
def get_sticky_model(session_id):
    e = session_cache.get(session_id)
    return e["model_id"] if e and (time()-e["time"] < 1800) else None  # 30 min
def set_sticky_model(session_id, model_id):
    session_cache[session_id] = {"model_id": model_id, "time": time()}
```
**Context handoff template** (inject as system message at index 1, after first system msg):
```
[Note: This conversation was started with {original_model}.
The current model ({new_model}) is continuing the conversation
because the original was unavailable. Please maintain the same
tone, style, and follow the existing conversation flow.
Please continue where the previous model left off.
```

---

## 8. Rate Limiter (Token Bucket per provider)
```python
class TokenBucket:
    def __init__(self, rpm=0, rpd=0, tpm=0):
        self.rpm, self.rpd, self.tpm = rpm, rpd, tpm
        self.tokens_minute, self.tokens_day, self.tokens_tpm = rpm, rpd, tpm
        self.last_refill = time()
    def refill(self):
        now = time(); elapsed = now - self.last_refill
        if elapsed >= 60:    self.tokens_minute = self.rpm; self.last_refill = now
        if elapsed >= 86400: self.tokens_day = self.rpd
```
Each request consumes a token; empty bucket → fallback. State persisted to `server/data/rate_limits.json` on shutdown, loaded on startup.

**Per-provider limits:**
```python
RATE_LIMITS = {
    "openrouter":    {"rpm":20, "rpd":50},            # 1000 RPD after $10 top-up
    "gemini":        {"rpm":15, "rpd":1500},
    "groq":          {"rpm":30, "rpd":1000, "tpm":6000},  # TPM is the real bottleneck
    "mistral":       {"rps":1,  "tpm":500000},        # ~1B/month
    "github_models": {"rpm":15, "rpd":150},
    "nvidia":        {"rpm":40, "rpd":1000},
    "cerebras":      {"rpm":30, "rpd":14400},
    "cloudflare":    {"neurons":10000},               # different system
    "zhipu":         {"concurrent":1},
    "huggingface":   {"rpm":10, "rpd":100},
    "aion":          {"rpm":15, "rpd":20, "tpd":20000},
    "cohere":        {"rpm":20, "rpd":33},            # 1000/month
}
```

---

## 9. Encrypted Key Storage (AES-256-GCM)
```python
# pip install cryptography
import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ENCRYPTION_KEY_LENGTH = 32  # 256 bits

def generate_encryption_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)

def encrypt_key(plain_key: str, key: bytes) -> str:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit GCM nonce
    ct = aesgcm.encrypt(nonce, plain_key.encode(), None)
    return base64.b64encode(nonce + ct).decode()   # base64(nonce + ciphertext)

def decrypt_key(encrypted_b64: str, key: bytes) -> str:
    data = base64.b64decode(encrypted_b64)
    nonce, ct = data[:12], data[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()
```
**SQLite table:**
```sql
CREATE TABLE keys (
    id TEXT PRIMARY KEY,                 -- "openrouter"
    encrypted_key TEXT NOT NULL,         -- base64(nonce + AES-256-GCM output)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    health_status TEXT DEFAULT 'unknown'
);
```
`ENCRYPTION_KEY` (32-byte base64) lives in `.env`. Decryption only in memory at request time. Dashboard shows keys masked `●●●●●`.

---

## 10. Health Checks
Every 30s, ping each provider with a tiny prompt:
- 200 → `healthy`; 429 → `rate_limited` (recover after cooldown); 401 → `invalid` (manual fix); 5xx → `error` (retry after 60s); timeout → `unreachable`.
```python
def get_healthy_providers(model_id):
    return [p for p in get_providers_for_model(model_id)
            if PROVIDER_STATUS[p]["status"] == "healthy"]
```

---

## 11. Caching
| Type | Key | TTL | Use |
|------|-----|:---:|-----|
| Exact match | `md5(model + messages + temp + max_tokens)` | 300s | identical question |
| Semantic | (optional) | 1800s | similar questions |
```python
def cache_key(model_id, messages, params):
    content = json.dumps({"model":model_id,"messages":messages,
        "temperature":params.get("temperature"),"max_tokens":params.get("max_tokens")}, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()
```
Config: `cache.enabled`, `cache.ttl`=300, `cache.max_size`=1000.

---

## 12. Provider Layer

### 12.1 Base class (`base.py`)
```python
@dataclass
class ProviderConfig:
    name: str            # "openrouter"
    base_url: str
    api_key: str         # decrypted before reaching provider
    models: list[str]
    rate_limits: dict

class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...
    @abstractmethod
    async def list_models(self) -> list[ModelInfo]: ...
    @abstractmethod
    async def check_health(self) -> HealthStatus: ...
    async def close(self): await self.client.aclose()
```
Each provider: build request in its native format → POST via httpx → translate response to unified OpenAI format → attach metadata (provider, latency, fallback).

### 12.2 Provider matrix (auth, base URL, format)
| # | provider_id | Base URL | Format | Auth |
|---|-------------|----------|:------:|------|
| 1 | openrouter | `https://openrouter.ai/api/v1` | ✅ openai | Bearer |
| 2 | gemini | `https://generativelanguage.googleapis.com/v1beta` | ⚠️ translate | `?key=API_KEY` query param |
| 3 | groq | `https://api.groq.com/openai/v1` | ✅ openai | Bearer |
| 4 | mistral | `https://api.mistral.ai/v1` | ✅ openai | Bearer |
| 5 | github_models | `https://models.inference.ai.azure.com` | ✅ openai | Bearer (GitHub token) |
| 6 | nvidia | `https://integrate.api.nvidia.com/v1` | ⚠️ partial | Bearer |
| 7 | cerebras | `https://api.cerebras.ai/v1` | ✅ openai | Bearer |
| 8 | cloudflare | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run` | ❌ translate (neurons) | Bearer + account_id |
| 9 | zhipu | `https://open.bigmodel.cn/api/paas/v4` | ✅ openai | Bearer |
| 10 | huggingface | `https://router.huggingface.co/hf-inference/v1` | ✅ openai | Bearer |
| 11 | aion | `https://api.aionlabs.ai/v1` | ✅ openai | Bearer |
| 12 | cohere | `https://api.cohere.com/v2` | ✅ openai | Bearer |

Special handling:
- **gemini**: translate OpenAI messages → `{"contents":[{"parts":[{"text":...}]}]}`, endpoint `/models/{id}:generateContent?key=...`; translate response back. Multimodal capable. EU/UK/CH: no free tier; may train on data outside EU.
- **cloudflare**: neurons-based quota (10k/day), non-OpenAI body → translate.
- **nvidia**: partial OpenAI compat, evaluation-only ToS (non-commercial).
- **cohere**: non-commercial trial, 1000 calls/month.
- **mistral / gemini**: may use data for training — warn user.

---

## 13. Model Registry Data (mirror of models-classification.md)

> ⚠️ **SUPERSEDED (2026-06-17):** the model list below was the original *forward-dated/aspirational* catalog (fictional ids like `gemini-3.5-flash`, `gpt-4o` free on GitHub, `deepseek-v4-flash`). It has been **replaced** by a doc-verified, no-card catalog. The current authoritative data lives in **`models-classification.md`** → **`scripts/sync_models.py`** → **`models_registry.json`** (46 models, 10 providers). See **`docs/STATUS_AND_SETUP.md`** for the verified list and signup links. The section below is kept only for historical reference.

> Strength: S=Frontier, A=Strong, B=Good, C=Decent. Use cases: coding, search, reasoning, creative, data, vision, audio.

### Provider 1 — OpenRouter (Bearer; $10 top-up raises RPD to 1000)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | rpd |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| nemotron-3-ultra | nvidia/nemotron-3-ultra-550b-a55b:free | A | coding,search,reasoning,data | 1M | 4K | 20 | 50 |
| deepseek-v4-flash | deepseek/deepseek-v4-flash:free | A | coding,data,search | 1M | 8K | 20 | 50 |
| minimax-m2.5 | minimax/minimax-m2.5:free | B | coding,creative,search | 1M | 4K | 20 | 50 |
| mimo-v2.5 | xiaomi/mimo-v2.5:free | B | coding,search | 128K | 4K | 20 | 50 |
| big-pickle | big-pickle:free | B | coding,search | — | — | 20 | 50 | (collects training data) |
| nemotron-3-super | nvidia/nemotron-3-super-120b-a12b:free | B | coding,search | 1M | 4K | 20 | 50 |
| owl-alpha | openrouter/owl-alpha:free | B | coding,search | 1.05M | — | 20 | 50 |
| deepseek-r1 | deepseek/deepseek-r1:free | A | reasoning,coding,search | — | — | 20 | 50 |
| dolphin3-r1 | cognitivecomputations/dolphin3.0-r1-mistral-24b:free | C | creative,coding | — | — | 20 | 50 |
| qwen-3.5-plus | qwen/qwen-3.5-plus:free | B | coding,search,data | — | — | 20 | 50 |

### Provider 2 — Google Gemini (query-param key; translate format)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | rpd |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| gemini-3.5-flash | gemini-3.5-flash | S | coding,search,reasoning,creative,data,vision,audio | 1M | 64K | 15 | 1500 |
| gemini-2.5-pro | gemini-2.5-pro | S | coding,search,reasoning,creative,data,vision | 2M | 65K | 5 | 50 |
| gemini-2.5-flash | gemini-2.5-flash | A | coding,search,vision | 1M | 65K | 15 | 1500 |
| gemini-3.1-flash-lite | gemini-3.1-flash-lite | B | coding,search | 1M | 65K | 30 | 1500 |

### Provider 3 — Groq (Bearer; 6000 TPM is the bottleneck)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | rpd | tpm |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|:--:|
| llama-3.3-70b | llama-3.3-70b-versatile | A | coding,search,reasoning,data | 128K | 8K | 30 | 1000 | 6000 |
| llama-4-scout | llama-4-scout-17b-16e-instruct | B | coding,search | 128K | 8K | 30 | 1000 | 6000 |
| qwen-3-32b | qwen-3-32b | B | coding,search,data | 32K | 8K | 30 | 1000 | 6000 |
| gpt-oss-120b | gpt-oss-120b | A | coding,search | 128K | 8K | 30 | 1000 | 6000 |
| gemma4-31b | gemma4-31b-it | B | coding,search | 256K | 8K | 30 | 1000 | 6000 |
| mixtral-8x7b | mixtral-8x7b-32768 | C | coding,search | 32K | 8K | 30 | 1000 | 6000 |
| llama-3.1-8b | llama-3.1-8b-instant | C | coding,search | 128K | 8K | 30 | 1000 | 6000 |

### Provider 4 — Mistral AI (Bearer; ~1B tokens/month, trains on data)
| id | provider_model_id | strength | use_cases | ctx | out | rps | tpm |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| codestral | codestral-latest | A | coding | 256K | 256K | 1 | 500K |
| mistral-medium-3.5 | mistral-medium-2604 | A | coding,search,reasoning,data | 256K | 256K | 1 | 500K |
| mistral-small-4 | mistral-small-latest | B | coding,search,creative | 256K | 256K | 1 | 500K |
| mistral-large-3 | mistral-large-latest | A | coding,search,reasoning | 256K | 256K | 1 | 500K |
| pixtral-large | pixtral-large-latest | A | coding,vision | 128K | 128K | 1 | 500K |
| mistral-nemo | open-mistral-nemo | B | coding,search | 128K | 128K | 1 | 500K |
| magistral | magistral-2405 | A | reasoning,coding | 256K | 256K | 1 | 500K |
| devstral | devstral-latest | A | coding | 256K | 256K | 1 | 500K |

### Provider 5 — GitHub Models (Bearer GitHub token; frontier models free)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | rpd |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| gpt-4o | gpt-4o | S | coding,search,reasoning,creative,data,vision | 128K | 16K | 15 | 150 |
| gpt-4o-mini | gpt-4o-mini | A | coding,search,data | 128K | 16K | 15 | 150 |
| claude-3.5-sonnet | claude-3.5-sonnet | S | coding,reasoning,creative | 200K | 8K | 15 | 150 |
| claude-3.5-haiku | claude-3.5-haiku | A | coding,search | 200K | 8K | 15 | 150 |
| llama-3.3-70b-gh | llama-3.3-70b | A | coding,search,data | 128K | 8K | 15 | 1000 |
| phi-4 | phi-4 | B | coding,search | 128K | 4K | 15 | 1000 |
| mistral-large-gh | mistral-large | A | coding,search,reasoning | 128K | 8K | 15 | 1000 |

### Provider 6 — NVIDIA NIM (Bearer; partial compat; eval-only ToS)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | credits/day |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| nemotron-3-ultra-nv | nvidia/nemotron-3-ultra | A | coding,search,reasoning,data | 1M | 4K | 40 | ~1000 |
| nemotron-3-super-nv | nvidia/nemotron-3-super | B | coding,search | 1M | 4K | 40 | ~1000 |

### Provider 7 — Cerebras (Bearer; UNSTABLE — fallback only; ~2600 tok/s)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | rpd | tpd |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|:--:|
| gpt-oss-120b-cb | gpt-oss-120b | A | coding,search,data | 128K | 8K | 30 | 14400 | 1M |
| zai-glm-4.7 | zai-glm-4.7 | B | coding,search | 128K | 8K | 10 | 100 | 1M |

### Provider 8 — Cloudflare Workers AI (Bearer + account_id; translate; 10k neurons/day shared)
| id | provider_model_id | strength | use_cases | ctx |
|----|-------------------|:--:|----------|:--:|
| cf-llama-4-scout | @cf/meta/llama-4-scout-17b-16e-instruct | B | coding,search,vision | 10M |
| cf-llama-3.3-70b | @cf/meta/llama-3.3-70b-instruct-fp8-fast | A | coding,search | 131K |
| cf-gpt-oss-120b | @cf/openai/gpt-oss-120b | A | coding,search | 128K |
| cf-gemma-4-26b | @cf/google/gemma-4-26b-it | B | coding,search | 256K |

### Provider 9 — Zhipu AI (Bearer; 1 concurrent)
| id | provider_model_id | strength | use_cases | ctx | out |
|----|-------------------|:--:|----------|:--:|:--:|
| glm-4.7-flash | glm-4.7-flash | A | coding,search,reasoning,data | 200K | 128K |
| glm-4.6v-flash | glm-4.6v-flash | B | coding,vision | 128K | 4K |

### Provider 10 — HuggingFace (Bearer; slow serverless; model <10GB)
| id | provider_model_id | strength | use_cases | ctx |
|----|-------------------|:--:|----------|:--:|
| hf-llama-3.3-70b | meta-llama/llama-3.3-70b-instruct | A | coding,search,data | 128K |
| hf-mistral-small-4 | mistralai/mistral-small-4-119b-2603 | B | coding,search | 256K |
| hf-qwen-3.6 | qwen/qwen-3.6-35b-a3b | B | coding,search | 128K |
| hf-deepseek-v4 | deepseek-ai/deepseek-v4 | A | coding,search,data | 1M |
| hf-command-a-plus | coherelabs/command-a-plus-05-2026 | A | coding,search,data | 128K |
| hf-north-mini-code | coherelabs/north-mini-code | B | coding | 128K |

### Provider 11 — Aion Labs (Bearer via Discord; story/RP only)
| id | provider_model_id | strength | use_cases | ctx | out | rpm | tpd |
|----|-------------------|:--:|----------|:--:|:--:|:--:|:--:|
| aion-2.5 | aion-2.5 | C | creative | 128K | 32K | 15 | 20K |
| aion-2.0 | aion-2.0 | C | creative | 128K | 32K | 15 | 20K |
| aion-rp-1.0 | aion-rp-llama-3.1-8b | C | creative | 32K | 8K | 15 | 20K |

### Provider 12 — Cohere (Bearer; non-commercial; 1000 calls/month)
| id | provider_model_id | strength | use_cases | ctx | out | rpm |
|----|-------------------|:--:|----------|:--:|:--:|:--:|
| command-a-plus | command-a-plus-05-2026 | A | coding,search,data | 128K | 4K | 20 |
| command-a | command-a-03-2025 | A | coding,search,reasoning | 256K | 4K | 20 |
| command-r-plus | command-r-plus-08-2024 | B | coding,search | 128K | 4K | 20 |
| command-r | command-r-08-2024 | B | coding,search | 128K | 4K | 20 |

### Top picks (for Quality Router defaults)
- **S-tier overall:** GPT-4o, Claude 3.5 Sonnet (GitHub), Gemini 3.5 Flash, Gemini 2.5 Pro, Codestral
- **Coding:** Codestral → GPT-4o → Claude 3.5 Sonnet → DeepSeek V4 Flash → Nemotron 3 Ultra
- **Reasoning:** DeepSeek R1 → Gemini 2.5 Pro → Gemini 3.5 Flash → Magistral → Nemotron 3 Ultra
- **Search:** GPT-4o → Gemini 3.5 Flash → Llama 3.3 70B → Mistral Large 3 → Command A+
- **Creative:** Claude 3.5 Sonnet → GPT-4o → Gemini 3.5 Flash → MiniMax M2.5 → Aion 2.5

---

## 14. Configuration

### 14.1 `config.yaml`
```yaml
server:
  host: "127.0.0.1"        # "0.0.0.0" for network (less safe)
  port: 8000               # 1024-65535
  workers: 1
  log_level: "INFO"        # DEBUG|INFO|WARNING|ERROR
  cors_origins: ["*"]      # restrict for network
auth:
  enabled: true
  api_key: "sk-local"
database:
  path: "server/data/gateway.db"
cache:
  enabled: true
  ttl: 300
  max_size: 1000
rate_limiter:
  enabled: true
  state_file: "server/data/rate_limits.json"
sticky_sessions:
  enabled: true
  ttl: 1800
  context_handoff: true
quality_router:
  enabled: true
  default_task_type: "default"
providers:
  openrouter:    {base_url: "https://openrouter.ai/api/v1"}
  gemini:        {base_url: "https://generativelanguage.googleapis.com/v1beta"}
  groq:          {base_url: "https://api.groq.com/openai/v1"}
  mistral:       {base_url: "https://api.mistral.ai/v1"}
  github_models: {base_url: "https://models.inference.ai.azure.com"}
  nvidia:        {base_url: "https://integrate.api.nvidia.com/v1"}
  cerebras:      {base_url: "https://api.cerebras.ai/v1"}
  cloudflare:    {base_url: "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"}
  zhipu:         {base_url: "https://open.bigmodel.cn/api/paas/v4"}
  huggingface:   {base_url: "https://router.huggingface.co/hf-inference/v1"}
  aion:          {base_url: "https://api.aionlabs.ai/v1"}
  cohere:        {base_url: "https://api.cohere.com/v2"}
dashboard:
  enabled: true
  username: "admin"        # password set on first run
```

### 14.2 `.env`
```env
ENCRYPTION_KEY=YOUR_32_BYTE_BASE64_KEY_HERE   # AES-256-GCM, generated once
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
# DASHBOARD_PASSWORD=...   # optional, else set first run
# Optional direct provider keys (prefer Dashboard which encrypts to SQLite):
# OPENROUTER_KEY=sk-or-v1-...   GEMINI_KEY=AIza...   GROQ_KEY=gsk_...
# MISTRAL_KEY=...   GITHUB_KEY=ghp_...   NVIDIA_KEY=nvapi-...   CEREBRAS_KEY=...
# CLOUDFLARE_ACCOUNT_ID=...   CLOUDFLARE_API_TOKEN=...   ZHIPU_KEY=...
# HF_KEY=hf_...   AION_KEY=...   COHERE_KEY=...
```
Generate key:
```bash
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())"
```

### 14.3 `.gitignore`
```
.env
*.db
server/data/
__pycache__/
*.pyc
```

### 14.4 `requirements.txt`
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.28.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
aiosqlite>=0.20.0
cryptography>=42.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
python-json-logger>=2.0.0
jinja2>=3.0.0
aiofiles>=23.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

### 14.5 `Dockerfile`
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/server/data
EXPOSE 8000
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 14.6 `docker-compose.yml`
```yaml
version: '3.8'
services:
  gateway:
    build: .
    container_name: llm-free-gateway
    ports: ["8000:8000"]
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./server/data:/app/server/data
      - ./.env:/app/.env:ro
    environment:
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD","python","-c","import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 15. Server wiring (`server.py`)
```python
app = FastAPI(title="Personal GateKeeper",
    description="مجمع النماذج المجانية في API واحد",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc")

# CORS: if host == 127.0.0.1 → allow_origins ["*"], credentials False
#       else → explicit origins, credentials True
@app.on_event("startup")
async def startup():
    await registry.load()       # read models-classification.md / registry json
    await key_manager.init()    # decrypt keys from SQLite

@app.on_event("shutdown")
async def shutdown():
    await rate_limiter.save_state()
```
Custom exceptions: `GatewayError`, `NoHealthyProviderError`, `AllRateLimitedError`, `ModelNotFoundError` → mapped to HTTP 404/429/503 via `@app.exception_handler(GatewayError)`.

---

## 16. Admin Dashboard

> **UPDATED 2026-06-18 — direction changed to Streamlit.** The original in-app
> HTML/Jinja dashboard (`src/api/dashboard.py` + `templates/dashboard/`) is **deprecated**
> and replaced by a standalone **Streamlit control panel** (`dashboard/`) that talks to the
> gateway over a new `/admin/*` JSON API. Full design: **`docs/plan/DASHBOARD_ARCHITECTURE.md`**.
> Work is tracked in tasks **20–24**. The text below is kept for historical reference.

### 16.1 New model (Streamlit) — summary
- **Standalone Streamlit app** in top-level `dashboard/`, separate process on port `8501`,
  isolated `dashboard/requirements.txt` (deps NOT added to the gateway).
- Backend grows a small **`/admin/*` admin API** (bearer admin token) because Streamlit cannot
  call in-process functions. Endpoints back each page (stats, providers, keys, models, analytics).
- Pages are **one-file-per-module** under `dashboard/pages/` → add modules without restructuring.
- Fixes latent bug: `dashboard.py:182` calls non-existent `key_manager.get_key_metadata()`.

### 16.2 Original in-app design (HISTORICAL)
Lightweight HTML+CSS+JS (no React), served by FastAPI under `/dashboard/*`. Auth: `scrypt`-hashed password set on first run.
| Page | Function |
|------|----------|
| /dashboard | stats: requests, tokens, provider statuses |
| /dashboard/keys | add/remove API keys (encrypted to SQLite, shown masked) |
| /dashboard/models | view all models + classification |
| /dashboard/analytics | latency, tokens, per-provider breakdown |

---

## 17. Registry sync (`scripts/sync_models.py`)
Pipeline: `models-classification.md` (manual source of truth) → parse → `models_registry.json` (validates against §2.1 schema) → loaded into in-memory Registry at startup. Re-run whenever the markdown changes.

---

## 18. Agent integration snippets
- **OpenCode:** `/connect` → Custom Provider → Base URL `http://localhost:8000/v1`, key `sk-local`. Or config.json provider `mygateway` + `model: "mygateway/codestral"`.
- **OpenAI SDK:** `OpenAI(base_url="http://localhost:8000/v1", api_key="sk-local")`.
- **Claude Code:** `claude --model mygateway/codestral`.
- **Codex CLI:** `export CODEX_API_BASE=http://localhost:8000/v1; export CODEX_API_KEY=sk-local; codex --model codestral` (uses `/v1/responses`).
- **Hermes:** custom_providers entry with name/api_key/base_url.

---

## 19. Security checklist
- `ENCRYPTION_KEY` in `.env`, never committed
- Auth enabled; `host:127.0.0.1` for local; `.gitignore` blocks `.env`,`*.db`
- Dashboard password-protected
- Keys AES-256-GCM at rest, decrypted only in memory at request time
- Warn: Mistral & Gemini may train on data — don't send sensitive code
- `pip audit` periodically; for sensitive code prefer local models (Ollama/LM Studio)
- Network/VPS: HTTPS via Nginx reverse proxy (`proxy_buffering off` for streaming)

---

## 20. Build Order (execution roadmap)

**Phase 1 — MVP**
1. `requirements.txt`, `.gitignore`, `config.yaml`, `.env` template, `server/data/`
2. `core/config_loader.py` (read YAML)
3. `providers/base.py` (BaseProvider + ProviderConfig)
4. `core/registry.py` + `scripts/sync_models.py` + `models_registry.json` (from §13 data)
5. First two providers: `openrouter.py` + `gemini.py` (gemini needs translation)
6. `api/server.py` + `api/routes.py` + `api/middleware.py`
7. `GET /v1/models`, `POST /v1/chat/completions`, `GET /health`
8. Streaming (SSE) support

**Phase 2 — Unique feature**
9. `core/quality_router.py` (task_type → best model)
10. task_type detection from prompt; finalize classification data

**Phase 3 — Core features**
11. `core/fallback.py` (4 tiers + context handoff)
12. `core/rate_limiter.py` (token bucket + state persistence)
13. Sticky sessions + context handoff
14. `core/key_manager.py` (AES-256-GCM + SQLite)
15. Health checks (30s loop)
16. Remaining 10 providers

**Phase 4 — Polish**
17. Admin Dashboard (HTML/CSS/JS)
18. `core/cache.py`
19. Docker + docker-compose
20. Tests: `test_router.py`, `test_fallback.py`, `test_providers.py`, `test_rate_limiter.py`, `conftest.py`

**Suggested first-write order:** `base.py` → `registry.py` → `openrouter.py` → `routes.py` → expand.

---

## 21. Risks
| Risk | Mitigation |
|------|------------|
| Provider drops free tier | Fallback + registry update |
| Rate limits change | Rate limiter self-adjusts |
| Provider changes API format | Isolated in single provider file |
| Sensitive code leak | README warning; some providers train on data |
| Usage spike drains limits | Fallback + rate limiter |
| Single-provider dependency | Always 2+ fallbacks per tier |
| Cerebras instability | Use as fallback only, never primary |

---

## 22. Manual run & smoke test
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
# create .env with ENCRYPTION_KEY
python -m src.api.server                          # or: uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{"model":"codestral","messages":[{"role":"user","content":"Say hi"}]}'
```
```
First run sequence: read config.yaml → create SQLite db → load ENCRYPTION_KEY →
look for encrypted keys (none → open Dashboard to add) → health-check providers → ready.
```
```

