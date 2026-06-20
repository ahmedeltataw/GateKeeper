# 🚀 ONBOARDING.md — دليل البدء السريع
> **الملف:** `docs/ONBOARDING.md`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Designed**
> **الموجه لـ:** مطور جديد يريد تشغيل المشروع لأول مرة

---

## ⏱️ **الوقت التقديري: 30 دقيقة**

---

## خطوة 1: فهم المشروع

اقرأ هذه الملفات بالترتيب:

| الترتيب | الملف | لماذا؟ |
|:-------:|-------|--------|
| 1 | `README.md` | نظرة عامة سريعة |
| 2 | `docs/ARCHITECTURE.md` (الأقسام 1-4) | فهم المبادئ والعمارة |
| 3 | `docs/SCHEMAS.md` (قسم 1-2) | فهم تنسيق البيانات |
| 4 | `docs/PROVIDERS.md` (قسم 1-5) | المصادر اللي هتشتغل معاها |
| 5 | `docs/SECURITY.md` | الأمان (مهم من البداية) |

---

## خطوة 2: المتطلبات

### الأدوات المطلوبة
```bash
# 1. Python 3.11+
python --version  # تأكد: >= 3.11

# 2. pip (آخر إصدار)
pip install --upgrade pip

# 3. Git (اختياري)
git --version

# 4. Docker (اختياري — للتشغيل في container)
docker --version
docker compose version
```

### API Keys — اللي هتحتاج تجيبها
للبدأ، انت تحتاج **API Key واحد على الأقل** من المصادر دي:

| Provider | وقت التسجيل | سهولة |
|----------|:-----------:|:-----:|
| **GitHub Models** | 2 دقيقة | 🔥 الأسهل (حساب GitHub بس) |
| **OpenRouter** | 3 دقيقة | 🟢 سهل |
| **Groq** | 3 دقيقة | 🟢 سهل |
| **Google Gemini** | 5 دقيقة | 🟢 سهل |
| **Mistral** | 10 دقيقة | 🟡 يحتاج phone verification |

> **اقتراح:** ابدأ بـ GitHub Models (GPT-4o مجاناً) + OpenRouter (أكبر مجموعة نماذج)

---

## خطوة 3: الإعداد

```bash
# 1. ادخل مجلد المشروع
Set-Location -LiteralPath "D:\ai-project\free models"

# 2. أنشئ Virtual Environment
python -m venv venv

# 3. فعّل البيئة
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
# source venv/bin/activate

# 4. ثبت المكتبات
pip install -r requirements.txt

# 5. أنشئ ملف .env
# انسخ من docs/CONFIG.md → Section 3 → .env
# الأهم: ENCRYPTION_KEY

# 6. أنشئ مجلد البيانات
New-Item -ItemType Directory -Force -Path "server/data" | Out-Null
```

---

## خطوة 4: إضافة API Keys

### الخيار A — Dashboard (موصى به)
```bash
# شغّل الـ server
python -m src.api.server

# افتح المتصفح
# http://localhost:8000/dashboard
# → اضبط Dashboard password
# → أضف Keys من صفحة Keys
```

### الخيار B — يدوي (بدون Dashboard)
أضف keys مباشرة في `.env`:
```env
OPENROUTER_KEY=sk-or-...
GEMINI_KEY=AIza...
GROQ_KEY=gsk_...
MISTRAL_KEY=...
GITHUB_KEY=ghp_...
```

---

## خطوة 5: اختبر التشغيل

```bash
# 1. تأكد إن الـ Server شغال
curl http://localhost:8000/health
# → {"status": "healthy", "providers": {...}}

# 2. جيب النماذج المتاحة
curl http://localhost:8000/v1/models
# → list of models with IDs

# 3. جرب طلب
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Say hello"}]}'
```

### لو شغال، مبروك 🎉 — Gateway جاهز!

---

## خطوة 6: الربط مع Agent

### OpenCode
```bash
opencode
/connect
# → Custom Provider
# → Base URL: http://localhost:8000/v1
# → API Key: sk-local
# → اختر موديل: gpt-4o أو codestral أو أي حاجة
```

### Hermes Agent
```yaml
# في config.yaml بتاع Hermes
custom_providers:
  - name: mygateway
    api_key: sk-local
    base_url: http://localhost:8000/v1
```

### أي Agent (OpenAI SDK)
```python
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-local"
)
```

---

## 🆘 **لو واجهت مشكلة:**

| المشكلة | راجع |
|---------|------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `Address already in use` | غير الـ port في config.yaml |
| `401 Unauthorized` | تحقق من API Key في Dashboard |
| `429 Too Many Requests` | انتظر — Fallback هيتولى |
| أي مشكلة تانية | `docs/CONFIG.md → Troubleshooting` |

---

## 📚 **دليل الملفات السريع**

| عايز تعرف | اقرأ |
|-----------|------|
| إيه هو المشروع أساساً؟ | `README.md` |
| إزاي الـ Gateway بيشتغل؟ | `docs/ARCHITECTURE.md` |
| الـ Schemas الرسمية | `docs/SCHEMAS.md` |
| توصيل Provider معين | `docs/PROVIDERS.md` |
| إعدادات التشغيل | `docs/CONFIG.md` |
| الأمان | `docs/SECURITY.md` |
| كل الموديلات المتاحة | `models-classification.md` |
