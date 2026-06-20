# 🧩 SCHEMAS.md — المواصفات الرسمية للبيانات
> **الملف:** `docs/SCHEMAS.md`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Designed**
>
> هذا الملف يحتوي على **الـ schemas الرسمية** لكل كيان في الـ Gateway.  
> أي كود يكتب يجب أن يتبع هذه الـ schemas بالضبط.

---

## 1. `models_registry.json` Schema

الـ Registry هو **النسخة الآلية** من `models-classification.md`.

```json
{
  "$schema": "https://json-schema.org/draft-07/schema",
  "title": "Model Registry",
  "description": "Machine-readable registry of all free models in the gateway",
  "type": "array",
  "items": {
    "$ref": "#/definitions/ModelInfo"
  },
  "definitions": {
    "ModelInfo": {
      "type": "object",
      "required": [
        "id", "display_name", "provider_id", "provider_model_id",
        "strength", "use_cases", "context_window", "max_output_tokens",
        "enabled", "status", "added_at", "last_verified"
      ],
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique model ID used in API requests (e.g., 'codestral')",
          "pattern": "^[a-z0-9.-]+$"
        },
        "display_name": {
          "type": "string",
          "description": "Human-readable name (e.g., 'Codestral')"
        },
        "provider_id": {
          "type": "string",
          "description": "Provider key in config.yaml (e.g., 'mistral')"
        },
        "provider_model_id": {
          "type": "string",
          "description": "Model ID as the provider expects it (e.g., 'codestral-latest')"
        },
        "strength": {
          "type": "string",
          "enum": ["S", "A", "B", "C"],
          "description": "S=Frontier, A=Strong, B=Good, C=Decent"
        },
        "strength_order": {
          "type": "integer",
          "description": "Numeric sort key: S=0, A=1, B=2, C=3"
        },
        "use_cases": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["coding", "search", "reasoning", "creative", "data", "vision", "audio", "default"]
          },
          "minItems": 1
        },
        "category": {
          "type": "string",
          "enum": ["general", "coding", "reasoning", "creative", "vision"],
          "description": "Model category for quick filtering"
        },
        "context_window": {
          "type": "integer",
          "minimum": 4096,
          "description": "Maximum input tokens (e.g., 262144)"
        },
        "max_output_tokens": {
          "type": "integer",
          "minimum": 1024,
          "description": "Maximum output tokens (e.g., 262144)"
        },
        "modalities": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["text", "image", "audio", "video"]
          },
          "default": ["text"]
        },
        "rate_limits": {
          "type": "object",
          "properties": {
            "rpm":  { "type": "integer", "minimum": 0 },
            "rpd":  { "type": "integer", "minimum": 0 },
            "tpm":  { "type": "integer", "minimum": 0 },
            "rps":  { "type": "number", "minimum": 0 },
            "tpd":  { "type": "integer", "minimum": 0 },
            "neurons": { "type": "integer", "minimum": 0 },
            "concurrent": { "type": "integer", "minimum": 1 }
          },
          "description": "At least one rate limit type must be present"
        },
        "fallback_models": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Ordered list of fallback model IDs (same strength or lower)"
        },
        "pricing": {
          "type": "object",
          "properties": {
            "input":  { "type": "number", "default": 0 },
            "output": { "type": "number", "default": 0 }
          },
          "description": "Price per million tokens. 0 = free tier"
        },
        "enabled": {
          "type": "boolean",
          "default": true
        },
        "status": {
          "type": "string",
          "enum": ["active", "deprecated", "removed", "pending_verification"],
          "default": "active"
        },
        "notes": {
          "type": "string",
          "description": "Free-text notes about the model"
        },
        "source_url": {
          "type": "string",
          "format": "uri",
          "description": "Link to official model documentation or pricing page"
        },
        "added_at": {
          "type": "string",
          "format": "date",
          "description": "Date when model was added to registry"
        },
        "removed_at": {
          "type": ["string", "null"],
          "format": "date",
          "default": null,
          "description": "Date when model was removed (null = still active)"
        },
        "last_verified": {
          "type": "string",
          "format": "date",
          "description": "Date of last successful verification of model availability"
        },
        "verification_source": {
          "type": "string",
          "description": "How verification was done: 'manual_test', 'api_check', 'community_report'"
        }
      }
    }
  }
}
```

### مثال كامل
```json
{
  "id": "codestral",
  "display_name": "Codestral",
  "provider_id": "mistral",
  "provider_model_id": "codestral-latest",
  "strength": "A",
  "strength_order": 1,
  "use_cases": ["coding"],
  "category": "coding",
  "context_window": 262144,
  "max_output_tokens": 262144,
  "modalities": ["text"],
  "rate_limits": {"rps": 1, "tpm": 500000},
  "fallback_models": ["nemotron-3-ultra", "deepseek-v4-flash"],
  "pricing": {"input": 0, "output": 0},
  "enabled": true,
  "status": "active",
  "notes": "أفضل موديل مجاني للكودينج",
  "source_url": "https://mistral.ai/products/codestral",
  "added_at": "2026-06-16",
  "removed_at": null,
  "last_verified": "2026-06-16",
  "verification_source": "manual_test"
}
```

---

## 2. `config.yaml` Schema

```yaml
# ============================================
# config.yaml — GateKeeper
# ============================================

server:
  host: "127.0.0.1"          # string, default: "127.0.0.1"
  port: 8000                 # integer, default: 8000, range: 1024-65535
  workers: 1                 # integer, default: 1
  log_level: "INFO"          # enum: ["DEBUG", "INFO", "WARNING", "ERROR"]
  cors_origins:              # array[string], default: ["*"]
    - "*"

auth:
  enabled: true              # boolean, default: true
  api_key: "sk-local"        # string, default: ""

database:
  path: "server/data/gateway.db"  # string, default: "server/data/gateway.db"

cache:
  enabled: true              # boolean, default: true
  ttl: 300                   # integer (seconds), default: 300
  max_size: 1000             # integer, default: 1000

rate_limiter:
  enabled: true              # boolean, default: true
  state_file: "server/data/rate_limits.json"  # string

sticky_sessions:
  enabled: true              # boolean, default: true
  ttl: 1800                  # integer (seconds), default: 1800
  context_handoff: true      # boolean, default: true

quality_router:
  enabled: true              # boolean, default: true
  default_task_type: "default"  # enum: ["coding", "search", "reasoning", "creative", "data", "default"]

providers:
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
  # ... كل Provider عنده base_url فقط
  # API Keys في encrypted SQLite, مش هنا

dashboard:
  enabled: true              # boolean, default: true · also gates the /admin/* router
  username: "admin"          # string, default: "admin"
  admin_token: null          # string|null, default: null · set via ADMIN_TOKEN env; bearer token for /admin/* (Streamlit dashboard). Unset → /admin/* returns 403
```

---

## 3. `ChatRequest` Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema",
  "title": "ChatRequest",
  "description": "POST /v1/chat/completions request body",
  "type": "object",
  "required": ["model", "messages"],
  "properties": {
    "model": {
      "type": "string",
      "description": "Model ID from the registry (e.g., 'codestral')"
    },
    "messages": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {
            "type": "string",
            "enum": ["system", "user", "assistant", "tool"]
          },
          "content": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "tool_calls": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "type", "function"],
              "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["function"]},
                "function": {
                  "type": "object",
                  "required": ["name", "arguments"],
                  "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "string"}
                  }
                }
              }
            }
          },
          "tool_call_id": {
            "type": "string"
          }
        }
      }
    },
    "temperature": {
      "type": "number",
      "default": 0.7,
      "minimum": 0,
      "maximum": 2
    },
    "max_tokens": {
      "type": "integer",
      "default": 2048,
      "minimum": 1
    },
    "stream": {
      "type": "boolean",
      "default": false
    },
    "top_p": {
      "type": "number",
      "default": 1
    },
    "frequency_penalty": {
      "type": "number",
      "default": 0,
      "minimum": -2,
      "maximum": 2
    },
    "presence_penalty": {
      "type": "number",
      "default": 0,
      "minimum": -2,
      "maximum": 2
    },
    "stop": {
      "type": ["string", "array", "null"],
      "items": {"type": "string"},
      "default": null
    },
    "task_type": {
      "type": "string",
      "enum": ["coding", "search", "reasoning", "creative", "data", "vision", "default"],
      "description": "Hints the Quality Router to select the best model for this task"
    }
  },
  "definitions": {
    "ToolCall": {
      "type": "object",
      "required": ["id", "type", "function"],
      "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["function"]},
        "function": {
          "type": "object",
          "required": ["name", "arguments"],
          "properties": {
            "name": {"type": "string"},
            "arguments": {"type": "string"}
          }
        }
      }
    }
  }
}
```

---

## 4. `ChatResponse` Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema",
  "title": "ChatResponse",
  "description": "POST /v1/chat/completions response (non-streaming)",
  "type": "object",
  "required": ["id", "object", "created", "model", "choices", "usage"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^chatcmpl-[a-z0-9]+$"
    },
    "object": {
      "type": "string",
      "enum": ["chat.completion"]
    },
    "created": {
      "type": "integer",
      "description": "Unix timestamp"
    },
    "model": {
      "type": "string",
      "description": "The model that generated this response"
    },
    "choices": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["index", "message", "finish_reason"],
        "properties": {
          "index": {"type": "integer"},
          "message": {
            "type": "object",
            "required": ["role", "content"],
            "properties": {
              "role": {"type": "string", "enum": ["assistant"]},
              "content": {"type": ["string", "null"]},
              "tool_calls": {
                "type": "array",
                "items": {"$ref": "ChatRequest#/definitions/ToolCall"}
              },
              "refusal": {"type": ["string", "null"]}
            }
          },
          "finish_reason": {
            "type": "string",
            "enum": ["stop", "length", "tool_calls", "content_filter", "error"]
          }
        }
      }
    },
    "usage": {
      "type": "object",
      "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
      "properties": {
        "prompt_tokens": {"type": "integer"},
        "completion_tokens": {"type": "integer"},
        "total_tokens": {"type": "integer"}
      }
    },
    "provider": {
      "type": "string",
      "description": "Extended field: which provider served this request"
    },
    "fallback_used": {
      "type": "boolean",
      "description": "Extended field: whether fallback was triggered"
    }
  }
}
```

---

## 5. `Provider Metadata` Schema

```json
{
  "type": "object",
  "required": ["id", "name", "base_url", "api_format", "requires_card", "auth_type"],
  "properties": {
    "id": {"type": "string"},
    "name": {"type": "string"},
    "base_url": {"type": "string", "format": "uri"},
    "api_format": {
      "type": "string",
      "enum": ["openai_compatible", "partial", "custom"]
    },
    "requires_card": {"type": "boolean", "default": false},
    "auth_type": {
      "type": "string",
      "enum": ["bearer", "query_param", "custom"]
    },
    "data_training_policy": {
      "type": "string",
      "enum": ["no_training", "opt_out_available", "may_use_for_training", "unknown"]
    },
    "commercial_use_allowed": {
      "type": "boolean",
      "default": false
    },
    "rate_limits": {
      "type": "object",
      "properties": {
        "rpm":  { "type": "integer", "minimum": 0 },
        "rpd":  { "type": "integer", "minimum": 0 },
        "tpm":  { "type": "integer", "minimum": 0 },
        "rps":  { "type": "number", "minimum": 0 },
        "tpd":  { "type": "integer", "minimum": 0 },
        "neurons": { "type": "integer", "minimum": 0 },
        "concurrent": { "type": "integer", "minimum": 1 }
      },
      "description": "Provider-specific rate limits"
    },
    "signup_url": {"type": "string", "format": "uri"},
    "docs_url": {"type": "string", "format": "uri"},
    "notes": {"type": "string"},
    "last_verified": {"type": "string", "format": "date"}
  }
}
```

---

## 6. Model Registry MongoDB-like Query Format

```python
# الـ Registry في الذاكرة يدعم الـ queries التالية:

# كل الموديلات اللي قوتها A
registry.get_by_strength("A")

# كل الموديلات المناسبة للكودينج
registry.get_by_use_case("coding")

# أفضل موديل coding متاح
registry.get_best_for_task("coding")

# موديلات Coordinate معينة
registry.get_by_provider("mistral")

# موديلات لسة active
registry.get_active()

# بحث بكلمة
registry.search("nemotron")
```

> **هذا الـ Schema هو المرجع الرسمي لأي كود يكتب.**
