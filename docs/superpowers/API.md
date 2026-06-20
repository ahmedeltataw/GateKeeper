# 📡 API.md — مواصفات API الرسمية
> **الملف:** `docs/API.md`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Designed** — الكود لم يبدأ بعد

---

## 📋 **فهرس**

1. [Base URL](#1-base-url)
2. [Authentication](#2-authentication)
3. [GET /v1/models](#3-get-v1models)
4. [POST /v1/chat/completions](#4-post-v1chatcompletions)
5. [POST /v1/responses (Codex CLI)](#5-post-v1responses-codex-cli)
6. [GET /health](#6-get-health)
7. [خطأ (Errors)](#7-خطأ-errors)
8. [Streaming](#8-streaming)
9. [Extensions](#9-extensions)

---

## 1. **Base URL**

```
جميع الـ endpoints تبدأ بـ:
http://localhost:8000/v1
```

للإنتاج المحلي: `http://127.0.0.1:8000/v1`
للشبكة: `http://your-ip:8000/v1`

---

## 2. **Authentication**

```bash
# كل الطلبات (ما عدا /health) تحتاج:
Authorization: Bearer sk-local
# أو أي key في auth.api_key في config.yaml
```

لو `auth.enabled: false`، ما في داعي للـ header. لو `auth.enabled: true`، استخدم `Authorization: Bearer <api_key>`.

---

## 3. **GET /v1/models**

جلب قائمة كل الموديلات المتاحة حالياً.

### Request
```http
GET /v1/models
Authorization: Bearer sk-local
```

### Response
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
    }
  ]
}
```

### الحقول الإضافية (Gateway Extension)
```json
{
  "id": "codestral",
  "strength": "A",
  "provider": "mistral",
  "use_cases": ["coding"],
  "context_window": 262144,
  "rate_limits": {"rps": 1, "tpm": 500000}
}
```

### `GET /v1/models?task_type=coding`
فلترة حسب المهمة:
```json
{
  "object": "list",
  "data": [
    {"id": "codestral", "strength": "A", "use_cases": ["coding"], ...},
    {"id": "nemotron-3-ultra", "strength": "A", "use_cases": ["coding", "search"], ...}
  ]
}
```

---

## 4. **POST /v1/chat/completions**

### Request (Non-Streaming)
```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer sk-local

{
  "model": "codestral",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Write a Python function"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": null,
  "task_type": "coding"
}
```

### Response (Non-Streaming)
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
  "fallback_used": false,
  "original_model": "codestral"
}
```

### الحقول الإضافية في الـ Response
| الحقل | النوع | الوصف |
|-------|------|-------|
| `provider` | string | الـ Provider اللي خدم الطلب (مثلاً `"mistral"`) |
| `fallback_used` | boolean | هل تم استخدام Fallback؟ |
| `original_model` | string | الموديل المطلوب أصلاً (لو حصل Fallback) |
| `fallback_chain` | string[] | (اختياري) ترتيب الـ Fallback اللي حصل |

---

## 5. **POST /v1/responses (Codex CLI)**

لـ Codex CLI compatibility. **نفس الـ body والـ response زي chat completions**.

---

## 6. **GET /health**

فحص صحة الـ Gateway.

### Request
```http
GET /health
```

### Response
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "providers": {
    "openrouter": "healthy",
    "gemini": "healthy",
    "groq": "rate_limited",
    "mistral": "healthy",
    "github_models": "healthy"
  },
  "uptime_seconds": 3600,
  "requests_total": 1500,
  "requests_last_hour": 50,
  "cache_hits": 120,
  "fallback_count": 5
}
```

### حالات Providers
| الحالة | المعنى |
|--------|--------|
| `healthy` | شغال تمام |
| `rate_limited` | حدود الاستخدام خلصت مؤقتاً |
| `invalid` | API Key مش صالح |
| `error` | خطأ في الاتصال |
| `unknown` | لم يتم الفحص بعد |

---

## 7. **خطأ (Errors)**

| الحالة | الـ Error Type | متى يحدث؟ |
|:------:|---------------|-----------|
| `400` | `invalid_request_error` | طلب مش صحيح (model مفقود، messages غلط) |
| `401` | `authentication_error` | Auth فاشل أو API Key مش موجود |
| `404` | `not_found` | موديل مش موجود في الـ Registry |
| `429` | `rate_limit_error` | كل الـ Providers خلص Rate Limits |
| `500` | `api_error` | خطأ داخلي في الـ Gateway |
| `503` | `service_unavailable` | كل الـ Providers معطلين |

### تنسيق الخطأ
```json
{
  "error": {
    "message": "Model 'xyz' not found. Available models: codestral, gpt-4o, nemotron-3-ultra",
    "type": "not_found",
    "code": 404,
    "param": "model",
    "doc_url": "http://localhost:8000/v1/models"
  }
}
```

### مع `stream: true`
```
data: {"error": {"message": "...", "type": "..."}}
```

---

## 8. **Streaming**

### Request
```json
{"model": "codestral", "messages": [...], "stream": true}
```

### Response (Server-Sent Events)
```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"content":"def"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{"content":" sorted"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1719000000,"model":"codestral","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### ملاحظات الـ Streaming
- كل chunk بيروح لـ Agent فوراً
- لو حصل Fallback في النص، الـ Streaming ينتهي ويرجع error
- الـ "role": "assistant" ييجي في أول chunk بس

---

## 9. **Extensions**

### `task_type` — توجيه الـ Quality Router
```json
{"model": "auto", "messages": [...], "task_type": "coding"}
```
- `"model": "auto"` → الـ Gateway يختار أفضل موديل بناءً على `task_type`
- لو `model` محدد، `task_type` يُستخدم كـ hint

### `fallback_chain` — معرفة ترتيب الـ Fallback
```json
{
  "choices": [...],
  "fallback_chain": ["codestral", "nemotron-3-ultra", "deepseek-v4-flash"]
}
```
يرجع الترتيب اللي حصل فيه Fallback (مفيد للـ debugging).

---

> **هذه هي الـ API Contract الرسمية.**  
> أي تغيير في الـ endpoints يبدأ من هنا.
