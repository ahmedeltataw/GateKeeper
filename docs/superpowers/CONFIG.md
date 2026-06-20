# ⚙️ CONFIG.md — إعدادات التشغيل
> **الملف:** `docs/CONFIG.md`
> **المسار:** `D:\ai-project\free models`
> **آخر تحديث:** 16 يونيو 2026

---

## 📋 **فهرس المحتويات**
1. [ملفات الإعدادات](#1-ملفات-الإعدادات)
2. [config.yaml — الإعدادات الرئيسية](#2-configyaml--الإعدادات-الرئيسية)
3. [ملف .env — المتغيرات السرية](#3-ملف-env--المتغيرات-السرية)
4. [requirements.txt — مكتبات Python](#4-requirementstxt--مكتبات-python)
5. [Docker — تشغيل في Container](#5-docker--تشغيل-في-container)
6. [تشغيل يدوي (Manual)](#6-تشغيل-يدوي-manual)
7. [إعدادات Providers في Gateway](#7-إعدادات-providers-في-gateway)
8. [تسجيل أول مرة (First Run)](#8-تسجيل-أول-مرة-first-run)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. **ملفات الإعدادات**

| الملف | الوظيفة | هل هو في Git؟ |
|-------|---------|:-------------:|
| `config.yaml` | إعدادات التشغيل العامة (port, logging, providers) | ✅ نعم |
| `.env` | المتغيرات السرية (encryption key, ...) | ❌ لا (في `.gitignore`) |
| `requirements.txt` | مكتبات Python | ✅ نعم |
| `.gitignore` | تجاهل الملفات الحساسة | ✅ نعم |
| `docker-compose.yml` | تشغيل Docker | ✅ نعم |

---

## 2. **config.yaml — الإعدادات الرئيسية**

```yaml
# ============================================
# GateKeeper — Config
# ============================================

# --- Server ---
server:
  host: "127.0.0.1"          # آمن: محلي فقط. للشبكة: "0.0.0.0" (⚠️ أقل أماناً)
  port: 8000                # البورت اللي هيشتغل عليه
  workers: 1                # عدد العمال (شخصي => 1)
  log_level: "INFO"         # DEBUG | INFO | WARNING | ERROR
  cors_origins: ["*"]       # CORS (محلي => *). للشبكة: حدد origins محددة

# --- Auth ---
auth:
  enabled: true             # تفعيل Auth؟ (موصى به)
  api_key: "sk-local"       # Bearer token الافتراضي

# --- Database (SQLite) ---
database:
  path: "server/data/gateway.db"  # مسار قاعدة البيانات

# --- Cache ---
cache:
  enabled: true             # تفعيل التخزين المؤقت؟
  ttl: 300                  # مدة الصلاحية بالثواني (300 = 5 دقائق)
  max_size: 1000            # أقصى عدد للـ cached responses

# --- Rate Limiting ---
rate_limiter:
  enabled: true             # تفعيل؟
  state_file: "server/data/rate_limits.json"  # حفظ الحالة بين الجلسات

# --- Sticky Sessions ---
sticky_sessions:
  enabled: true             # تفعيل؟
  ttl: 1800                 # 30 دقيقة (بالثواني)
  context_handoff: true     # حقن context عند تغيير الموديل؟

# --- Quality Router ---
quality_router:
  enabled: true             # تفعيل الاختيار الذكي؟
  default_task_type: "default"  # المهمة الافتراضية
  # إذا ما حدد المستخدم task_type

# --- Providers ---
# ⚠️ القائمة الكاملة للنماذج والـ IDs في models-classification.md
# هنا فقط الإعدادات الأساسية لكل Provider (base_url + enabled models)
# يتم تخزين API Keys في encrypted SQLite، مش هنا
providers:
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
  
  gemini:
    base_url: "https://generativelanguage.googleapis.com/v1beta"
  
  groq:
    base_url: "https://api.groq.com/openai/v1"
  
  mistral:
    base_url: "https://api.mistral.ai/v1"
  
  github_models:
    base_url: "https://models.inference.ai.azure.com"
  
  nvidia:
    base_url: "https://integrate.api.nvidia.com/v1"
  
  cerebras:
    base_url: "https://api.cerebras.ai/v1"
  
  cloudflare:
    base_url: "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
  
  zhipu:
    base_url: "https://open.bigmodel.cn/api/paas/v4"
  
  huggingface:
    base_url: "https://router.huggingface.co/hf-inference/v1"
  
  aion:
    base_url: "https://api.aionlabs.ai/v1"
  
  cohere:
    base_url: "https://api.cohere.com/v2"

# --- Dashboard ---
dashboard:
  enabled: true             # تفعيل لوحة التحكم؟
  username: "admin"         # اسم المستخدم
  # كلمة السر: تُسأل في أول مرة
```

---

## 3. **ملف .env — المتغيرات السرية**

ملف `.env` هو الملف الوحيد اللي فيه الـ sensitive data.

```env
# ============================================
# GateKeeper — Environment
# ============================================

# Encryption Key (يتم توليده مرة واحدة — يحفظ كل API Keys)
# توليد key جديد (AES-256-GCM — 32 bytes):
#   python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())"
ENCRYPTION_KEY=YOUR_32_BYTE_BASE64_KEY_HERE

# Server
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO

# Dashboard Password (يتم توليده في أول مرة)
# لو عايز تحدده يدوي:
# DASHBOARD_PASSWORD=your_password_here

# === لو عايز تضيف API Keys مباشرة (بدون Dashboard) ===
# ملاحظة: لو استخدمت الـ Dashboard، keys هتتخزن مشفرة في SQLite
# OPENROUTER_KEY=sk-or-...
# GEMINI_KEY=AIza...
# GROQ_KEY=gsk_...
# MISTRAL_KEY=...
# GITHUB_KEY=ghp_...
# NVIDIA_KEY=nvapi-...
```

### كيفية توليد Encryption Key
```bash
# على Windows (PowerShell)
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())"

# على Linux/macOS
python3 -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())"
```

### ملف `.gitignore`
```gitignore
# Environment
.env
*.db

# Data
server/data/

# Cache
__pycache__/
*.pyc
```

---

## 4. **requirements.txt — مكتبات Python**

```txt
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.28.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Database
aiosqlite>=0.20.0

# Encryption
cryptography>=42.0.0

# Utils
python-dotenv>=1.0.0
pyyaml>=6.0.0
python-json-logger>=2.0.0

# Optional — Dashboard
jinja2>=3.0.0
aiofiles>=23.0.0

# Development
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.28.0  # لاختبار API
```

---

## 5. **Docker — تشغيل في Container**

### `Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# تثبيت الاعتماديات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# إنشاء مجلد البيانات
RUN mkdir -p /app/server/data

# المنفذ
EXPOSE 8000

# التشغيل
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  gateway:
    build: .
    container_name: llm-free-gateway
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./server/data:/app/server/data
      - ./.env:/app/.env:ro
    environment:
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### تشغيل Docker
```bash
# بناء وتشغيل
docker compose up -d

# متابعة الـ logs
docker compose logs -f

# إيقاف
docker compose down

# إعادة بناء
docker compose up -d --build
```

---

## 6. **تشغيل يدوي (Manual)**

### أول مرة — تثبيت المكتبات
```bash
# 1. إنشاء Virtual Environment
python -m venv venv

# 2. تفعيل
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. تثبيت المكتبات
pip install -r requirements.txt
```

### تشغيل الـ Server
```bash
# من مجلد المشروع (PowerShell)
Set-Location -LiteralPath "D:\ai-project\free models"

# تفعيل venv (لو مش مفعل)
.\venv\Scripts\Activate.ps1

# تشغيل
python -m src.api.server

# أو باستخدام uvicorn مباشرة
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### اختبر التشغيل
```bash
# 1. هل الـ server شغال؟
curl http://localhost:8000/health

# 2. جيب النماذج المتاحة
curl http://localhost:8000/v1/models

# 3. جرب طلب
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "codestral", "messages": [{"role": "user", "content": "Say hi"}]}'

# 4. مع الـ API key
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{"model": "codestral", "messages": [{"role": "user", "content": "Say hi"}]}'
```

---

## 7. **إعدادات Providers في Gateway**

### إضافة API Key عبر Dashboard (موصى به)
```
1. افتح http://localhost:8000/dashboard
2. سجل الدخول (أول مرة: أنشئ password)
3. اذهب إلى Keys page
4. اختر Provider من القائمة
5. الصق API Key
   → يتم تشفيره وتخزينه في SQLite
```

### إضافة API Key يدوي (بدون Dashboard)
في `.env`:
```env
# Provider Keys (Plain Text — مش موصى به)
# الأفضل استخدام Dashboard عشان التشفير التلقائي
OPENROUTER_KEY=sk-or-v1-...
GEMINI_KEY=AIzaSy...
GROQ_KEY=gsk_...
MISTRAL_KEY=...
GITHUB_KEY=ghp_...
NVIDIA_KEY=nvapi-...
CEREBRAS_KEY=...
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
ZHIPU_KEY=...
HF_KEY=hf_...
AION_KEY=...
COHERE_KEY=...
```

---

## 8. **تسجيل أول مرة (First Run)**

عند تشغيل الـ Gateway لأول مرة:

```
1. ⚙️ قراءة config.yaml ✅
2. 🗄️ إنشاء SQLite database ✅
3. 🔑 توليد Encryption Key (من .env) ✅
4. 🔍 البحث عن keys مشفرة في DB
   → لو ﻻ: فتح Dashboard لإضافة keys
5. 🌐 Health Check لكل Provider
   → تسجيل الحالة الأولية
6. 🚀 Server جاهز على http://localhost:8000
```

### ما يحتاجه المستخدم في أول مرة:
1. `config.yaml` مع إعدادات أساسية
2. `.env` مع `ENCRYPTION_KEY`
3. API Keys من الـ Providers اللي عايزهم
4. Dashboard: `http://localhost:8000/dashboard` → إضافة keys

---

## 9. **Troubleshooting**

### 9.1 Server مش شغال

| المشكلة | السبب | الحل |
|---------|-------|------|
| `Address already in use` | Port 8000 مشغول | غير البورت في config.yaml |
| `ModuleNotFoundError` | مكتبة ناقصة | `pip install -r requirements.txt` |
| `No such file` | مسار غلط | شوف `pwd` وضع الـ path الصحيح |
| `.env not found` | ملف البيئة مش موجود | أنشئ `.env` من النموذج |

### 9.2 Provider مش شغال

| المشكلة | السبب | الحل |
|---------|-------|------|
| `401 Unauthorized` | API Key غلط | تحقق من الـ Key في Dashboard |
| `429 Too Many Requests` | Rate Limit خلص | استنى — الـ Fallback هيتولى |
| `timeout` | بطء Provider | جرب Provider تاني |
| `404 Model Not Found` | موديل محذوف | حدث الـ Registry |

### 9.3 الاتصال من OpenCode

| المشكلة | السبب | الحل |
|---------|-------|------|
| `Connection refused` | الـ Gateway مش شغال | `python -m src.api.server` |
| `Invalid API key` | الـ key في config غلط | استخدم `sk-local` (أو الـ key اللي عرفته) |
| `Model not found` | الـ model ID مش موجود | `GET /v1/models` — شوف القائمة |

### 9.4 الـ Docker

| المشكلة | السبب | الحل |
|---------|-------|------|
| `Permission denied` | صلاحيات المجلد | `chmod -R 777 server/data` |
| `Port already in use` | Port 8000 مشغول | غير الـ port mapping |
| `Container exits` | خطأ في config | `docker compose logs` |

---

## 📌 **الخلاصة — خطوات التشغيل السريعة:**

```bash
# خطوة 1: Clone/Download المشروع
Set-Location -LiteralPath "D:\ai-project\free models"

# خطوة 2: أنشئ Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# source venv/bin/activate     # Linux/macOS

# خطوة 3: ثبت المكتبات
pip install -r requirements.txt

# خطوة 4: أنشئ ملف .env
# انسخ من قسم .env أعلاه

# خطوة 5: شغّل الـ Server
python -m src.api.server

# خطوة 6: افتح Dashboard
# http://localhost:8000/dashboard
# أضف API Keys

# خطوة 7: استخدم مع OpenCode
# opencode → /connect → http://localhost:8000/v1 → sk-local
```

> **جاهزين؟** الكود مستنينا في الـ src/ 🚀
