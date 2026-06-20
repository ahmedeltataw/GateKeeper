# 🏗️ GateKeeper — Architecture Document
> **الملف:** `docs/ARCHITECTURE.md`
> **المسار:** `D:\ai-project\free models`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Design Complete** — المراجع متكاملة، الكود لم يبدأ بعد
> **حالة التنفيذ:** 🟡 **مرحلة التصميم** — لم يبدأ الكود بعد
> **عدد الصفحات المرجعية:** 4 (هذا الملف + PROVIDERS.md + CONFIG.md + SCHEMAS.md)
>
> ### 🚦 قراءة Banner
> | اللون | المعنى |
> |:-----:|--------|
> | 🟢 **Designed** | المواصفات مكتوبة ومنتهية |
> | 🟡 **Planned** | في مرحلة التخطيط، لم تُكتب بعد |
> | 🔴 **Draft** | مسودة أولية، قد تتغير

---

## 📋 **فهرس المحتويات**
1. [نظرة عامة](#1-نظرة-عامة)
2. [المبادئ الأساسية](#2-المبادئ-الأساسية)
3. [هيكل المشروع](#3-هيكل-المشروع)
4. [العمارة العامة](#4-العمارة-العامة)
5. [مواصفات API (API Contract)](#5-مواصفات-api-api-contract)
6. [تدفق الطلب الكامل](#6-تدفق-الطلب-الكامل)
7. [المكونات بالتفصيل](#7-المكونات-بالتفصيل)
8. [قاعدة بيانات الموديلات (Model Registry)](#8-قاعدة-بيانات-الموديلات-model-registry)
9. [Quality-Based Router — الميزة الفريدة](#9-quality-based-router--الميزة-الفريدة)
10. [نظام الـ Fallback](#10-نظام-الـ-fallback)
11. [Sticky Sessions + Context Handoff](#11-sticky-sessions--context-handoff)
12. [نظام Rate Limiting](#12-نظام-rate-limiting)
13. [Encrypted Key Storage](#13-encrypted-key-storage)
14. [Health Checks](#14-health-checks)
15. [نظام Caching](#15-نظام-caching)
16. [Admin Dashboard](#16-admin-dashboard)
17. [معالجة الأخطاء (Error Handling)](#17-معالجة-الأخطاء-error-handling)
18. [التكامل مع الـ Agents](#18-التكامل-مع-الـ-agents)
19. [خريطة الطريق](#19-خريطة-الطريق)
20. [المخاطر والتحديات](#20-المخاطر-والتحديات)

---

## 1. **نظرة عامة**

### المشكلة
- **12+ مصدر** يقدمون نماذج LLM مجانية
- كل مصدر: API مختلف، Rate Limits مختلفة، Authentication مختلفة
- أي Agent يدعم `custom provider` واحد فقط في كل مرة
- مضطر تختار مصدر واحد أو تنتقل بينهم يدوياً

### الحل: Gateway وسطي واحد
```
Agent → http://localhost:8000/v1 → Gateway → Provider A أو B أو C (حسب الحالة)
```

### الهدف
> **API واحد، موحد، بتاعك أنت — بيجمع كل النماذج المجانية في مكان واحد، بدون عمولة، بدون كارد، بدون وسيط.**

### النطاق (Scope)
- **يدعم:** `GET /health` و `GET /v1/models` و `POST /v1/chat/completions`
- **يدعم لاحقاً/اختياري:** `POST /v1/responses` للتوافق مع Codex CLI
- **لا يدعم:** Image gen, Audio, Embeddings (ممكن لاحقاً)
- **الاستخدام:** شخصي فقط (single-user)
- **اللغة:** Python 3.11+ / FastAPI

---

## 2. **المبادئ الأساسية**

| المبدأ | الشرح | تطبيقه في الكود |
|--------|-------|----------------|
| **🧩 Modular** | كل Provider ملف مستقل | `src/providers/<name>.py` — إضافة/حذف بدون تأثير على الباقي |
| **🔁 Fail-First** | الفشل مش نهاية — جرب البديل فوراً | Fallback chain من 4 مستويات |
| **📊 Data-Driven** | كل تصنيفات الموديلات في ملف واحد | `models-classification.md` ← Registry ← الكود يقرأ منه |
| **💸 Zero Cost** | مفيش كارد، مفيش عمولة | كل المصادر من Free Tiers |
| **🪶 Lightweight** | أقل عدد اعتماديات | FastAPI + httpx + Python stdlib فقط |
| **🔌 OpenAI Compatible** | أي Agent يشتغل معانا | `/v1/chat/completions` بالـ format الرسمي لـ OpenAI |
| **🔒 Key Security** | API keys مش plain text | AES-256-GCM في SQLite |
| **🔄 State Awareness** | المحادثة مش بتنقطع | Sticky Sessions 30 دقيقة + Context Handoff |

---

## 3. **هيكل المشروع**

```
D:\ai-project\free models\
│
├── 📄 README.md                        # شرح المشروع
├── 📄 models-classification.md         # مصدر الحقيقة — كل الموديلات
│
├── 📁 docs/                            # الوثائق
│   ├── 📄 ARCHITECTURE.md              # العمارة الكاملة — تفاصيل النظام
│   ├── 📄 SCHEMAS.md                   # الـ Schemas الرسمية للبيانات
│   ├── 📄 API.md                       # مواصفات API الرسمية
│   ├── 📄 SECURITY.md                  # النموذج الأمني
│   ├── 📄 ONBOARDING.md                # دليل البدء السريع
│   ├── 📄 PROVIDERS.md                 # تفاصيل توصيل كل Provider
│   └── 📄 CONFIG.md                    # شرح إعدادات التشغيل
│
├── 📁 src/
│   ├── 📁 api/                         # طبعة API
│   │   ├── 📄 __init__.py
│   │   ├── 📄 server.py                # FastAPI app
│   │   ├── 📄 routes.py                # endpoints
│   │   └── 📄 middleware.py            # CORS, Logging, Auth
│   │
│   ├── 📁 core/                        # طبعة المنطق
│   │   ├── 📄 __init__.py
│   │   ├── 📄 router.py               # Model Router
│   │   ├── 📄 quality_router.py       # Quality-Based Selection (ميزتنا)
│   │   ├── 📄 fallback.py             # Fallback Engine
│   │   ├── 📄 rate_limiter.py         # Token Bucket Manager
│   │   ├── 📄 cache.py                # Response Cache
│   │   ├── 📄 registry.py             # Model Registry
│   │   ├── 📄 config_loader.py        # يقرأ YAML
│   │   └── 📄 key_manager.py          # Encrypted Key Manager
│   │
│   └── 📁 providers/                   # Provider Modules
│       ├── 📄 __init__.py
│       ├── 📄 base.py                  # Base Class
│       ├── 📄 openrouter.py
│       ├── 📄 gemini.py
│       ├── 📄 groq.py
│       ├── 📄 mistral.py
│       ├── 📄 github_models.py
│       ├── 📄 nvidia.py
│       ├── 📄 cerebras.py
│       ├── 📄 cloudflare.py
│       ├── 📄 zhipu.py
│       ├── 📄 huggingface.py
│       ├── 📄 aion.py
│       └── 📄 cohere.py
│
├── 📁 scripts/
│   ├── 📄 test_gateway.sh
│   └── 📄 sync_models.py
│
├── 📁 tests/
│   ├── 📄 test_router.py
│   ├── 📄 test_fallback.py
│   ├── 📄 test_providers.py
│   ├── 📄 test_rate_limiter.py
│   └── 📄 conftest.py
│
├── 📄 requirements.txt
├── 📄 config.yaml                      # إعدادات المستخدم
├── 📄 .env                             # API Keys (مش Plain Text — AES مشفر)
├── 📄 Dockerfile
└── 📄 docker-compose.yml
```

---

## 4. **العمارة العامة**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          YOUR GATEWAY (port 8000)                          │
│                                                                             │
│  ┌───────────┐   ┌──────────────┐   ┌────────────────────────────────┐    │
│  │  Agent    │   │   FastAPI    │   │         Core Layer             │    │
│  │(OpenCode  │──▶│  /v1/*       │──▶│                                │    │
│  │ Claude    │   │              │   │  ┌────────────────────────┐    │    │
│  │ Codex     │   │  routes.py   │   │  │   Quality Router      │    │    │
│  │ Hermes)   │   │  middleware  │   │  │  (quality_router.py)  │    │    │
│  └───────────┘   └──────────────┘   │  └───────────┬────────────┘    │    │
│                                      │              │                    │    │
│                                      │     ┌────────┴────────┐         │    │
│                                      │     │   Model Router    │         │    │
│                                      │     │   (router.py)    │         │    │
│                                      │     └────────┬────────┘         │    │
│                                      │              │                    │    │
│                                      │     ┌────────┴────────┐         │    │
│                                      │     │   Fallback      │         │    │
│                                      │     │  Engine(4 tiers)│         │    │
│                                      │     └────────┬────────┘         │    │
│                                      │              │                    │    │
│                                      │     ┌────────┴────────┐         │    │
│                                      │     │  Rate Limiter   │         │    │
│                                      │     │  Key Manager    │         │    │
│                                      │     │  Cache Layer    │         │    │
│                                      │     └────────┬────────┘         │    │
│                                      └────────────────┼────────────────┘    │
│                                                        │                    │
│                                             ┌──────────┴──────────┐        │
│                                             │   Provider Layer     │        │
│                                             │                      │        │
│                                             │  openrouter.py  ◀───┤        │
│                                             │  gemini.py      ◀───┤        │
│                                             │  groq.py        ◀───┤        │
│                                             │  mistral.py     ◀───┤        │
│                                             │  github_models  ◀───┤        │
│                                             │  nvidia.py      ◀───┤        │
│                                             │  cerebras.py    ◀───┤        │
│                                             │  cloudflare.py  ◀───┤        │
│                                             │  zhipu.py       ◀───┤        │
│                                             │  huggingface.py ◀───┤        │
│                                             │  aion.py        ◀───┤        │
│                                             │  cohere.py      ◀───┤        │
│                                             └──────────┬──────────┘        │
└────────────────────────────────────────────────────────┼──────────────────┘
                                                         │
        ┌────────────┬────────────┬────────────┬─────────┼──────────┬──────────┐
        ▼            ▼            ▼            ▼         ▼          ▼          ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
   │OpenRouter│ │  Gemini  │ │  Groq   │ │ Mistral│ │GitHub  │ │NVIDIA  │ │  باقي   │
   │  API     │ │  API     │ │  API    │ │  API   │ │ Models │ │  NIM   │ │المصادر  │
   └──────────┘ └──────────┘ └──────────┘ └────────┘ └────────┘ └────────┘ └─────────┘
```

### مسارات البيانات (Data Paths)

```
1. Agent → POST /v1/chat/completions
2. API Layer → routes.py → middleware (CORS, Log, Auth)
3. Core Layer → Quality Router (اختيار الموديل حسب المهمة)
4. Core Layer → Model Router (اختيار الـ Provider)
5. Core Layer → Rate Limiter (هل في رصيد؟)
6. Core Layer → Failover (لو لأ — جرب البديل)
7. Core Layer → Key Manager (فك تشفير API Key)
8. Provider Layer → ارسال HTTP request
9. Provider Layer → استقبال والتحويل لـ OpenAI format
10. Core Layer → Cache (تخزين اختياري)
11. API Layer → Response للمستخدم
```

---

## 5. **مواصفات API (API Contract)**

### 5.1 `GET /v1/models`
ترجع قائمة بكل الموديلات المتاحة حالياً.

#### Response
```json
{
  "object": "list",
  "data": [
    {
      "id": "codestral",
      "object": "model",
      "created": 1719000000,
      "owned_by": "mistral",
      "permission": [],
      "root": "codestral",
      "parent": null
    },
    {
      "id": "gemini-3.5-flash",
      "object": "model",
      "created": 1719000000,
      "owned_by": "google",
      "permission": [],
      "root": "gemini-3.5-flash",
      "parent": null
    }
  ]
}
```

#### Response Extensions (اختياري — معلومات إضافية)
```json
{
  "id": "codestral",
  "object": "model",
  "strength": "A",
  "provider": "mistral",
  "use_cases": ["coding"],
  "context_window": 262144,
  "max_output": 262144,
  "rate_limits": {"rps": 1, "tpm": 500000}
}
```

### 5.2 `POST /v1/chat/completions`
الـ endpoint الرئيسي — إرسال طلب لموديل معين.

#### Request
```json
{
  "model": "codestral",
  "messages": [
    {"role": "system", "content": "You are a coding assistant."},
    {"role": "user", "content": "Write a Python function to sort a list."}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": null
}
```

#### Response (Non-Streaming)
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "codestral",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "```python\ndef sort_list(lst):\n    return sorted(lst)\n```"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 20,
    "total_tokens": 70
  },
  "provider": "mistral",
  "fallback_used": false
}
```

#### Response (Streaming — SSE)
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"content":"```python"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"content":"\\ndef"},"finish_reason":null}]}

... (باقي الـ chunks)

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 5.3 `GET /health`
فحص صحة الـ Gateway.
#### Response
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "providers": {
    "openrouter": "healthy",
    "gemini": "healthy",
    "groq": "rate_limited",
    "mistral": "healthy"
  },
  "uptime_seconds": 3600,
  "total_requests": 1500,
  "cache_hits": 120
}
```

---

## 6. **تدفق الطلب الكامل**

### سيناريو: مستخدم يطلب كود — وكل حاجة تمام

```
[1] Agent يرسل:
    POST /v1/chat/completions
    {"model": "codestral", "messages": [...], "task_type": "coding"}

[2] FastAPI Middleware:
    → تحقق Auth (Bearer token = "sk-...")
    → Log: {time, ip, model, task_type}
    → CORS headers

[3] Quality Router (quality_router.py):
    → task_type = "coding"
    → يبحث عن أفضل موديلات coding (من الـ Registry)
    → الترتيب: Codestral (A) > Nemotron 3 Ultra (A) > DeepSeek V4 Flash (A)
    → اختار: Codestral (لأنه #1 coding)
    → مرر لـ Model Router

[4] Model Router (router.py):
    → الموديل: codestral
    → الـ Provider: mistral
    → طلب من Rate Limiter: هل Mistral عنده رصيد؟

[5] Rate Limiter:
    → Mistral: 500K TPM / 1 RPS
    → الطلب الحالي: 50 tokens prompt
    → متبقي: 499,950 TPM — ✅ OK
    → خصم 50 token

[6] Key Manager:
    → استرجع API Key بتاع Mistral
    → فك التشفير (AES-256-GCM → plain text)
    → مرر الـ key لـ Mistral Provider

[7] Mistral Provider (mistral.py):
    → بناء HTTP request
    → POST https://api.mistral.ai/v1/chat/completions
    → Headers: {"Authorization": "Bearer <decrypted_key>"}
    → Body: {model: "codestral-latest", messages: [...]}

[8] Mistral API → Response:
    → استقبال JSON
    → تحويل لـ OpenAI format
    → إضافة "provider": "mistral" في metadata

[9] Cache:
    → تخزين الـ response (لو الـ caching مفعل)
    → TTL: 5 دقائق

[10] Logging:
    → سجل: {model, provider, tokens, latency, success}

[11] Response → Agent:
    → 200 OK
    → JSON بالـ OpenAI format
```

### سيناريو: Rate Limit نفد — Fallback

```
[1] Request: codestral
[2] Quality Router: codestral (A)
[3] Model Router: mistral
[4] Rate Limiter: ❌ Mistral خلص TPM
[5] Fallback Engine:
    → Tier 1: نفس الموديل من Provider آخر → Codestral متاح بس على Mistral → خلص
    → Tier 2: موديل بنفس القوة (A) → DeepSeek V4 Flash عبر OpenRouter
    → Rate Limiter: ✅ OpenRouter عنده رصيد
    → إرسال
[6] Log: Fallback → codestral → deepseek-v4-flash (سبب: mistral rate limit)
[7] Context Handoff: إضافة system message تخبر الـ agent بالتغيير
```

---

## 7. **المكونات بالتفصيل**

### 7.1 طبقة API (`src/api/`)

| المكون | الملف | المسؤوليات |
|--------|-------|------------|
| **Server** | `server.py` | إنشاء FastAPI app (`app = FastAPI(title="GateKeeper")`)، بدء Uvicorn |
| **Routes** | `routes.py` | `GET /v1/models`, `POST /v1/chat/completions`, `GET /health`, `POST /v1/responses` (اختياري) |
| **Middleware** | `middleware.py` | `CORSMiddleware`، `LoggerMiddleware`، `AuthMiddleware` (Bearer token) |

#### `server.py` — المواصفات الدقيقة
```python
# FastAPI App Configuration
app = FastAPI(
    title="GateKeeper",
    description="مجمع النماذج المجانية في API واحد",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — للاستخدام المحلي فقط
# ⚠️ للأمان: لو شغال على جهاز واحد فقط، استخدم "127.0.0.1:8000"
# ⚠️ لو فتحته على الشبكة (0.0.0.0)، حدد origins محددة مش "*"
if HOST == "127.0.0.1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # آمن — بس المحلي
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # شبكة خارجية — حدد origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```
# Startup: تحميل Registry + Keys
@app.on_event("startup")
async def startup():
    await registry.load()       # قراءة models-classification.md
    await key_manager.init()    # فك تشفير keys من SQLite

# Shutdown: حفظ حالة Rate Limits
@app.on_event("shutdown")
async def shutdown():
    await rate_limiter.save_state()
```

### 7.2 طبقة Core (`src/core/`)

| المكون | الملف | المسؤوليات |
|--------|-------|------------|
| **Quality Router** | `quality_router.py` | **ميزتنا الفريدة** — اختيار الموديل حسب المهمة والقوة |
| **Model Router** | `router.py` | اختيار Provider بناءً على الموديل المطلوب |
| **Fallback Engine** | `fallback.py` | 4 مستويات Fallback مع Context Handoff |
| **Rate Limiter** | `rate_limiter.py` | Token Bucket لكل Provider |
| **Cache** | `cache.py` | Response Cache (TTL اختياري) |
| **Registry** | `registry.py` | قاعدة بيانات الموديلات في الذاكرة |
| **Config Loader** | `config_loader.py` | قراءة `config.yaml` |
| **Key Manager** | `key_manager.py` | Encrypted Key Storage في SQLite |

### 7.3 طبقة Providers (`src/providers/`)

#### Base Class — `base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProviderConfig:
    name: str                      # "openrouter"
    base_url: str                  # "https://openrouter.ai/api/v1"
    api_key: str                   # plain text (key_manager يفكها قبل ما توصل)
    models: list[str]              # ["nvidia/nemotron-3-ultra-550b-a55b:free", ...]
    rate_limits: dict              # {"rpm": 20, "rpd": 50}

class BaseProvider(ABC):
    """كل Provider يرث من هذه الكلاس"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """إرسال طلب chat وإنشاء رد"""
        pass
    
    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """جلب قائمة الموديلات المتاحة"""
        pass
    
    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """فحص إذا كان الـ Provider شغال"""
        pass
    
    async def close(self):
        """تنظيف الموارد"""
        await self.client.aclose()
```

#### طريقة عمل كل Provider:

```
Agent → Gateway → [BaseProvider.chat()]
                      ↓
                 بناء HTTP request (حسب format المصدر)
                      ↓
                 httpx.AsyncClient.post(url, headers, json)
                      ↓
                 استقبال response
                      ↓
                 تحويل لـ OpenAI format موحد
                      ↓
                 إضافة metadata (provider, latency, fallback)
                      ↓
                 return ChatResponse
```

---

## 8. **قاعدة بيانات الموديلات (Model Registry)**

### 8.1 المصدر الأساسي
ملف `models-classification.md` هو الـ **Single Source of Truth**. أي تغيير في الموديلات يبدأ من هنا.

### 8.2 تنسيق Model Object

```python
@dataclass
class ModelInfo:
    """معلومات كاملة عن أي موديل في الـ Gateway"""
    
    # --- الهوية (Required) ---
    id: str                              # "codestral"
    display_name: str                    # "Codestral"
    provider_id: str                     # "mistral"
    provider_model_id: str               # "codestral-latest"
    
    # --- التصنيف (Classification) ---
    strength: str                        # "S" | "A" | "B" | "C"
    use_cases: list[str]                 # ["coding", "search"]
    category: str                        # "general" | "coding" | "reasoning" | "creative"
    
    # --- الحدود التقنية (Capabilities) ---
    context_window: int                  # 262144
    max_output_tokens: int               # 262144
    modalities: list[str]                # ["text"], ["text", "image"]
    pricing_per_million: dict | None     # {"input": 0, "output": 0} (مجاني)
    
    # --- Rate Limits (Limits) ---
    rate_limits: dict                    # {"rpm": 30, "rpd": 1000, "tpm": 6000}
    
    # --- الحالة (Status) ---
    enabled: bool                        # True
    status: str                          # "active" | "deprecated" | "removed"
    
    # --- المصادر البديلة (Fallback Options) ---
    fallback_models: list[str]           # ["deepseek-v4-flash", "nemotron-3-ultra"]
    
    # --- Metadata ---
    notes: str | None                    # "أفضل موديل مجاني للكودينج"
    source_url: str | None               # رابط التوثيق
    added_at: str                        # "2026-06-16"
    removed_at: str | None               # None (لا يزال موجوداً)
    last_verified: str                   # "2026-06-16"
```

### 8.3 استراتيجية التحميل

```
models-classification.md (يدوي — مصدر الحقيقة)
         │
         ▼
   scripts/sync_models.py  (توليد JSON آلي)
         │
         ▼
   models_registry.json  (cache للقراءة السريعة)
         │
         ▼
   Registry Class (في الذاكرة عند تشغيل الـ Gateway)
         │
         ▼
   Quality Router + Model Router (يقرأوا من الـ Registry)
```

---

## 9. **Quality-Based Router — الميزة الفريدة**

دي **أهم نقطة بيفرقنا** عن FreeLLMAPI وأي حل تاني.

### الفكرة
بدل ما نختار الموديل عشوائي أو على أساس Rate Limits بس، بنختار **أقوى موديل مناسب للمهمة المطلوبة ومازال عنده رصيد**.

### آلية الاختيار

```python
async def select_best_model(task_type: str, available_models: list[ModelInfo]):
    """
    اختيار أفضل موديل للمهمة المطلوبة.
    
    1. task_type يحدد use_case المطلوب
    2. نبحث عن موديلات تدعم هذا الـ use_case
    3. نرتبهم حسب القوة (S → A → B → C)
    4. نتحقق من Rate Limits
    5. نرجع الأول المتاح
    """
    
    # تصفية حسب المهمة
    candidates = [
        m for m in available_models
        if task_type in m.use_cases and m.enabled and m.status == "active"
    ]
    
    # ترتيب حسب القوة
    strength_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    candidates.sort(key=lambda m: strength_order.get(m.strength, 99))
    
    # اختيار الأول اللي عنده رصيد
    for model in candidates:
        provider = get_provider(model.provider_id)
        if await rate_limiter.allow(provider, model):
            return model
    
    # لو مفيش — جرب أي موديل متاح
    return await fallback_any()
```

### task_type دعم

| القيمة | المعنى | مثال الموديلات المناسبة |
|--------|--------|------------------------|
| `"coding"` | برمجة وتطوير | Codestral → Nemotron 3 Ultra → DeepSeek V4 Flash |
| `"search"` | بحث وتحليل | Gemini 3.5 Flash → Nemotron 3 Ultra → Llama 3.3 |
| `"reasoning"` | منطق واستراتيجية | Gemini 2.5 Pro → DeepSeek R1 → Magistral |
| `"creative"` | كتابة إبداعية | Claude 3.5 Sonnet → GPT-4o → MiniMax M2.5 |
| `"data"` | تحليل بيانات | GPT-4o → Mistral Large → Command A+ |
| `"vision"` | صور | Gemini 3.5 Flash → Pixtral Large → GLM-4.6V |
| `"default"` | أي حاجة | Gemini 3.5 Flash (S-tier general) |

### User Flow

```
المستخدم: "أكتب لي كود React component"  → task_type = "coding"
                                                                    ↓
Quality Router: أفضل موديل coding مع رصيد = Codestral
                                                                    ↓
Model Router: إرسال الطلب لـ Mistral Provider
```

---

## 10. **نظام الـ Fallback**

### المستويات الأربعة

```
إذا فشل Provider A على الموديل X:

[المستوى 1] نفس الموديل — Provider آخر
    X من OpenRouter؟ → X من NVIDIA (لو موجود)
    
[المستوى 2] نفس القوة — موديل آخر
    Codestral (A) → Nemotron 3 Ultra (A) → DeepSeek V4 Flash (A)
    
[المستوى 3] أقل بدرجة
    A → B: Codestral (A) → MiniMax M2.5 (B)
    
[المستوى 4] Last Resort
    أي موديل متاح عنده Rate Limit
```

### أسباب الفشل

| الكود | السبب | Cooldown | الإجراء |
|-------|-------|:--------:|---------|
| `429` | Rate Limit | 60 ثانية | جرب الموديل التالي فوراً |
| `5xx` | خطأ في الخادم | 30 ثانية | ضع علامة unhealthy، جرب غيره |
| `timeout` | بطء في الرد (>30s) | — | جرب البديل |
| `401` | API Key غير صحيح | دائم | أوقف هذا الـ Key (غير صالح) |
| `404` | موديل محذوف | دائم | سجل كـ "removed" في الـ Registry |

### آلية العمل الكاملة

```python
COOLDOWN = {
    "429": 60,     # ثانية
    "5xx": 30,
    "timeout": 0,  
    "401": None,   # للأبد
    "404": None,   # للأبد
}

async def try_with_fallback(request, task_type):
    # 1. اختيار أفضل موديل للمهمة (Quality Router)
    preferred_model = await select_best_model(task_type, registry.models)
    if not preferred_model:
        raise NoModelAvailableError("No suitable model found")
    
    # 2. جرب نفس الموديل من كل Provider عنده
    for provider in get_providers_for_model(preferred_model.id):
        if not rate_limiter.allow(provider, preferred_model):
            log(f"[Fallback T1] {provider.name} rate-limited, trying next")
            continue
        try:
            response = await provider.chat(request)
            log(f"[Success] {provider.name}/{preferred_model.id}")
            return response
        except ProviderError as e:
            wait = COOLDOWN.get(e.code, 30)
            await rate_limiter.cooldown(provider, wait)
            log(f"[Fallback T1] {provider.name} failed: {e}")
            continue
    
    # 3. جرب موديلات بنفس القوة
    for model in registry.get_by_strength(preferred_model.strength):
        if model.id == preferred_model.id: continue
        for provider in get_providers_for_model(model.id):
            if not rate_limiter.allow(provider, model): continue
            try:
                response = await provider.chat(request)
                log(f"[Fallback T2] {model.id} (same tier)")
                # Context Handoff
                response = add_context_handoff(response, preferred_model.id, model.id)
                return response
            except ProviderError:
                continue
    
    # 4. جرب أقل (Tier 3) وأخيراً Last Resort (Tier 4)
    ...
```

---

## 11. **Sticky Sessions + Context Handoff**

### Sticky Sessions
**المشكلة:** لو غيرنا الموديل في وسط محادثة (بسبب Fallback)، المستخدم يحس بتغير في الشخصية والجودة.

**الحل:** Session Stickiness — أول موديل ينجح يفضل مستخدم لمدة 30 دقيقة.

```python
# Sticky Session: معرف بسيط من conversation
session_cache = {}  # session_id → model_id

def get_sticky_model(session_id: str) -> str | None:
    """يرجع الموديل اللي شغال عليه الـ session (أو None لو جديد)"""
    entry = session_cache.get(session_id)
    if entry and (time() - entry["time"] < 1800):  # 30 دقيقة
        return entry["model_id"]
    return None

def set_sticky_model(session_id: str, model_id: str):
    session_cache[session_id] = {"model_id": model_id, "time": time()}
```

### Context Handoff
**المشكلة:** لو اضطرينا نغير الموديل (مثلاً من Codestral لـ DeepSeek)، الموديل الجديد ما عنده context.

**الحل:** حقن system message يشرح الموقف للموديل الجديد.

```python
CONTEXT_HANDOFF_TEMPLATE = """
[Note: This conversation was started with {original_model}. 
The current model ({new_model}) is continuing the conversation 
because the original was unavailable. Please maintain the same 
tone, style, and follow the existing conversation flow.
Please continue where the previous model left off.
"""

def inject_context_handoff(messages, original_model, new_model):
    context_msg = {
        "role": "system",
        "content": CONTEXT_HANDOFF_TEMPLATE.format(
            original_model=original_model,
            new_model=new_model
        )
    }
    messages.insert(1, context_msg)  # بعد أول system message
    return messages
```

---

## 12. **نظام Rate Limiting**

### Token Bucket لكل Provider

كل Provider بيشتغل بنظام **دلو من الرصيد (Token Bucket)**:
- الدلو بيتعبأ بمعدل ثابت (مثلاً 20 request/دقيقة)
- كل طلب بياخد token من الدلو
- لو الدلو فاضي → Fallback

```python
class TokenBucket:
    def __init__(self, rpm: int = 0, rpd: int = 0, tpm: int = 0):
        self.rpm = rpm         # حد الدقيقة
        self.rpd = rpd         # حد اليوم
        self.tpm = tpm         # حد التوكن في الدقيقة
        
        # الحالة الحالية
        self.tokens_minute = rpm     # الرصيد الحالي (كل دقيقة بيتجدد)
        self.tokens_day = rpd        # الرصيد الحالي (كل يوم بيتجدد)
        self.tokens_tpm = tpm        # رصيد التوكن
        self.last_refill = time()
    
    def refill(self):
        """تجديد الرصيد"""
        now = time()
        elapsed = now - self.last_refill
        
        # كل دقيقة: تجديد RPM
        if elapsed >= 60:
            self.tokens_minute = self.rpm
            self.last_refill = now
        
        # كل 24 ساعة: تجديد RPD
        if elapsed >= 86400:
            self.tokens_day = self.rpd
```

### جدول Rate Limits لكل Provider

```python
RATE_LIMITS = {
    "openrouter":     {"rpm": 20, "rpd": 50},            # 1000 لو $10
    "gemini":         {"rpm": 15, "rpd": 1500},
    "groq":           {"rpm": 30, "rpd": 1000, "tpm": 6000},
    "mistral":        {"rps": 1, "tpm": 500000},         # 1B/شهر
    "github_models":  {"rpm": 15, "rpd": 150},
    "nvidia":         {"rpm": 40, "rpd": 1000},
    "cerebras":       {"rpm": 30, "rpd": 14400},
    "cloudflare":     {"neurons": 10000},                 # نظام مختلف
    "zhipu":          {"concurrent": 1},
    "huggingface":    {"rpm": 10, "rpd": 100},
    "aion":           {"rpm": 15, "rpd": 20, "tpd": 20000},
    "cohere":         {"rpm": 20, "rpd": 33},            # 1000/شهر
}
```

---

## 13. **Encrypted Key Storage**

مستوحى من FreeLLMAPI.

### لماذا؟
API Keys مش plain text في ملف `config.yaml`. لو حد اخترق الجهاز، مش هيقدر يقرا الـ keys.

> ⚠️ **تصحيح:** الإصدار السابق استخدم `cryptography.fernet.Fernet` (AES-128-CBC).  
> الكود التالي يستخدم AES-256-GCM الصحيح عبر `cryptography.hazmat`.

### الآلية

```python
# التشفير — AES-256-GCM الفعلي
# يتطلب: pip install cryptography
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENCRYPTION_KEY_LENGTH = 32  # 256 bits

def generate_encryption_key() -> bytes:
    """توليد مفتاح AES-256-GCM (32 bytes = 256 bits)"""
    return AESGCM.generate_key(bit_length=256)

def encrypt_key(plain_key: str, key: bytes) -> str:
    """
    تشفير API Key بـ AES-256-GCM.
    - key: 32 bytes (يتم تخزينه في .env)
    - return: base64(nonce + ciphertext)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce (GCM standard)
    ciphertext = aesgcm.encrypt(nonce, plain_key.encode(), None)
    # nonce + ciphertext معاً في base64 واحد
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_key(encrypted_b64: str, key: bytes) -> str:
    """
    فك تشفير API Key.
    - encrypted_b64: base64(nonce + ciphertext)
    - return: plain text key
    """
    data = base64.b64decode(encrypted_b64)
    nonce, ciphertext = data[:12], data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()

# === تخزين في SQLite ===
# CREATE TABLE keys (
#     id TEXT PRIMARY KEY,
#     encrypted_key TEXT NOT NULL,   -- base64(nonce + AES-256-GCM output)
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     last_used TIMESTAMP,
#     health_status TEXT DEFAULT 'unknown'
# );
```

### التخزين

```
SQLite:
  CREATE TABLE keys (
      id TEXT PRIMARY KEY,         # "openrouter"
      encrypted_key TEXT NOT NULL,  # المشفر
      created_at TIMESTAMP,
      last_used TIMESTAMP,
      health_status TEXT DEFAULT 'unknown'
  );
```

### الـ .env
```bash
# Encryption Key (يتم توليده مرة واحدة)
ENCRYPTION_KEY=...  # 32 bytes base64

# البيئة
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
```

---

## 14. **Health Checks**

### الآلية
كل 30 ثانية، الـ Gateway بيفحص كل الـ Keys عنده:

```
Health Check Loop (every 30s):
  لكل Provider:
    POST {base_url}/v1/chat/completions (prompt صغير)
    ↓
    200 → "healthy"
    429 → "rate_limited" (مؤقت — يرجع بعد cooldown)
    401 → "invalid" (دائم — يحتاج تدخل يدوي)
    5xx → "error" (يرجع يجرب بعد 60s)
    timeout → "unreachable"
```

### الاستخدام
```python
PROVIDER_STATUS = {
    "openrouter": {"status": "healthy", "last_check": "...", "rpd_remaining": 30},
    "mistral": {"status": "rate_limited", "cooldown_until": "..."},
    "github_models": {"status": "healthy"},
}

def get_healthy_providers(model_id: str) -> list[str]:
    return [
        p for p in get_providers_for_model(model_id)
        if PROVIDER_STATUS[p]["status"] == "healthy"
    ]
```

---

## 15. **نظام Caching**

### أنواع Caching

| النوع | المفتاح | الـ TTL | الاستخدام |
|-------|---------|:-------:|-----------|
| **Exact Match** | `md5(model + messages)` | 5 دقائق | نفس السؤال بالضبط |
| **Semantic** | (اختياري) | 30 دقيقة | أسئلة متشابهة |

### Exact Match Cache

```python
cache = {}
TTL = 300  # 5 دقائق

def cache_key(model_id: str, messages: list, params: dict) -> str:
    """توليد مفتاح فريد للـ cache"""
    content = json.dumps({
        "model": model_id,
        "messages": messages,
        "temperature": params.get("temperature"),
        "max_tokens": params.get("max_tokens"),
    }, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

def get_cached(model_id, messages, params):
    key = cache_key(model_id, messages, params)
    entry = cache.get(key)
    if entry and (time() - entry["time"] < TTL):
        return entry["response"]
    return None
```

---

## 16. **Admin Dashboard**

مستوحى من FreeLLMAPI. **Dashboard ويب بسيط** عشان تدير الـ Gateway.

### الصفحات المطلوبة

| الصفحة | الوظيفة |
|--------|---------|
| **/dashboard** | الإحصائيات الرئيسية: عدد الطلبات، tokens المستهلكة، حالة الـ Providers |
| **/dashboard/keys** | إضافة/حذف API Keys |
| **/dashboard/models** | رؤية كل الموديلات المتاحة وتصنيفها |
| **/dashboard/analytics** | Latency, tokens, per-provider breakdown |

### الـ Stack
- **Frontend:** HTML + CSS + JavaScript (بدون React — خفيف)
- **Backend:** نفس FastAPI — `GET /dashboard/*`
- **Auth:** `scrypt`-hashed password (أول مرة تشغيل)

---

## 17. **معالجة الأخطاء (Error Handling)**

### أخطاء الـ Gateway

| الحالة | المعنى | Response |
|:------:|--------|---------|
| `400` | طلب غير صحيح | `{"error": {"message": "...", "type": "invalid_request_error"}}` |
| `401` | Auth فاشل | `{"error": {"message": "Invalid API key", "type": "authentication_error"}}` |
| `404` | موديل غير موجود | `{"error": {"message": "Model 'x' not found", "type": "not_found"}}` |
| `429` | كل الحدود خلصت | `{"error": {"message": "All providers rate limited", "type": "rate_limit_error"}}` |
| `500` | خطأ داخلي | `{"error": {"message": "Internal server error", "type": "api_error"}}` |
| `503` | كل Providers معطلين | `{"error": {"message": "No healthy providers", "type": "service_unavailable"}}` |

### الـ Error Handling في الكود

```python
# === Custom Exceptions ===
class GatewayError(Exception): pass
class NoHealthyProviderError(GatewayError): pass
class AllRateLimitedError(GatewayError): pass
class ModelNotFoundError(GatewayError): pass

# === Error Handler ===
@app.exception_handler(GatewayError)
async def gateway_error_handler(request, exc: GatewayError):
    if isinstance(exc, ModelNotFoundError):
        return JSONResponse(status_code=404, content={
            "error": {
                "message": str(exc),
                "type": "not_found"
            }
        })
    elif isinstance(exc, AllRateLimitedError):
        return JSONResponse(status_code=429, content={
            "error": {
                "message": "All providers are currently rate-limited. Try again later.",
                "type": "rate_limit_error"
            }
        })
    elif isinstance(exc, NoHealthyProviderError):
        return JSONResponse(status_code=503, content={
            "error": {
                "message": "No healthy providers available.",
                "type": "service_unavailable"
            }
        })
```

---

## 18. **التكامل مع الـ Agents**

### OpenCode (الأساسي)

#### الطريقة 1: `/connect` (TUI)
```bash
opencode
/connect
# اختار: Custom Provider
# Base URL: http://localhost:8000/v1
# API Key: sk-local
```

#### الطريقة 2: `config.json`
```json
{
  "provider": {
    "mygateway": {
      "api_key": "sk-local",
      "base_url": "http://localhost:8000/v1"
    }
  },
  "model": "mygateway/codestral"
}
```

### Hermes Agent
```yaml
# config.yaml
custom_providers:
  - name: mygateway
    api_key: sk-local
    base_url: http://localhost:8000/v1
    models:
      - id: gemini-3.5-flash
      - id: codestral
      - id: gpt-4o
```

### أي Agent يدعم OpenAI SDK
```python
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-local"
)
response = client.chat.completions.create(
    model="codestral",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Claude Code
```bash
claude --model mygateway/codestral
# أو عبر config:
# استخدام provider: mygateway
```

### Codex CLI
```bash
# Codex يدعم --model provider/model_id
export CODEX_API_BASE=http://localhost:8000/v1
export CODEX_API_KEY=sk-local
codex --model codestral
```

---

## 19. **خريطة الطريق**

### **المرحلة 1: الأساسيات (MVP)**
- [ ] Base Class لـ Providers (`base.py`)
- [ ] Model Registry يقرأ من MD/JSON
- [ ] أول Providerين: **OpenRouter** + **Gemini**
- [ ] `server.py` + `routes.py` أساسيين
- [ ] `GET /v1/models` + `POST /v1/chat/completions`
- [ ] Streaming support

### **المرحلة 2: الميزات الفريدة 🏆**
- [ ] **Quality Router** — اختيار حسب المهمة والقوة
- [ ] Task type detection من الـ prompt
- [ ] تصنيف موديلات كامل في `models-classification.md`

### **المرحلة 3: الميزات الأساسية**
- [ ] Fallback System (4 مستويات)
- [ ] Rate Limiter (Token Bucket)
- [ ] Sticky Sessions
- [ ] Context Handoff
- [ ] Key Manager (AES-256-GCM + SQLite)
- [ ] Health Checks دورية
- [ ] باقي الـ Providers (8 مصادر)

### **المرحلة 4: التكميلات**
- [ ] Admin Dashboard (HTML/CSS/JS)
- [ ] Caching
- [ ] Docker + Docker Compose
- [ ] Config عبر YAML
- [ ] Arabic docs كاملة

---

## 20. **المخاطر والتحديات**

| الخطر | الاحتمال | التأثير | الحل |
|-------|:--------:|:-------:|------|
| **Provider يحذف الـ free tier** | 🟡 متوسط | فقدان موديل | Fallback لمصادر بديلة + تحديث الـ Registry |
| **Rate Limits تتغير** | 🟡 متوسط | نفاد مفاجئ | Rate Limiter يراقب ويضبط نفسه |
| **مصدر يغير API format** | 🟢 نادر | فشل الطلب | Base Class يعزل التغيير في ملف واحد |
| **المستخدم يبعت كود حساس** | 🟠 عالي | تسريب بيانات | تنبيه في الـ README: بعض المصادر بتجمع بيانات |
| **Spike في الاستخدام** | 🟠 عالي | استنزاف كل Rate Limits | Fallback + Rate Limiter يمنع الاستخدام المفرط |
| **الاعتماد على مصدر واحد** | 🟡 متوسط | نقطة فشل وحيدة | دائماً 2+ Fallbacks لكل Tier |

---

## 📌 **إرشادات التطوير**

```
💡 ابدأ بملف base.py (أبسط حاجة — كلاس واحد)
💡 ثاني حاجة: registry.py (عشان الـ Models تبقى في الذاكرة)
💡 ثالث حاجة: أول Provider بسيط (مثلاً openrouter.py — أسهل API)
💡 رابع حاجة: routes.py (اختبار الـ endpoints)
💡 وبعدين: الباقي تدريجياً
```

> **مستعدين لبدء كتابة الكود؟** 🚀
