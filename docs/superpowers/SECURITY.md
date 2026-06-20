# 🔒 SECURITY.md — النموذج الأمني
> **الملف:** `docs/SECURITY.md`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Designed**

---

## 📋 **نظرة عامة**

| المبدأ | القيمة |
|--------|--------|
| **مستوى الأمان** | شخصي (personal use) — غير تجاري |
| **نوع التهديد** | الوصول المحلي، تسريب API Keys |
| **Encryption at rest** | ✅ AES-256-GCM |
| **Encryption in transit** | HTTP (محلي) / HTTPS (شبكة خارجية) |
| **Auth** | Bearer token (اختياري — مفعل افتراضياً) |

---

## 1. **API Keys — الحماية**

| الطبقة | الآلية |
|--------|--------|
| **التخزين** | `server/data/gateway.db` (SQLite) |
| **التشفير** | AES-256-GCM (nonce 12-byte لكل key) |
| **مفتاح التشفير** | `ENCRYPTION_KEY` في `.env` (32 bytes base64) |
| **فك التشفير** | فقط في الذاكرة، وقت الطلب |
| **التعريض** | الـ keys **غير مرئية** في Dashboard (تظهر على هيئة `●●●●●`) |

### الـ Key Flow
```
.env: ENCRYPTION_KEY
         ↓
Dashboard: User inputs plain API Key
         ↓
key_manager.encrypt_key(plain, ENCRYPTION_KEY)  ← AES-256-GCM
         ↓
SQLite: stores base64(nonce + ciphertext)
         ↓
Request Time: key_manager.decrypt_key(stored, ENCRYPTION_KEY)
         ↓
Provider Module: uses plain key for HTTP call
         ↓
(plain key gets garbage collected after request)
```

### ⚠️ أبداً
- **لا تشارك** `ENCRYPTION_KEY` مع أحد
- **لا ترفع** `.env` على GitHub
- **لا تترك** الـ Gateway شغال على `0.0.0.0` بدون Auth

---

## 2. **Authentication (API Key للـ Gateway نفسه)**

```python
# config.yaml
auth:
  enabled: true        # يُفعل افتراضياً
  api_key: "sk-local"  # أي قيمة تختارها
```

```python
# كيف تعمل
if auth.enabled:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != auth.api_key:
        return 401 {"error": {"message": "Invalid API key"}}
```

### الاستخدام
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-local" \
  -d '{"model": "...", "messages": [...]}'
```

---

## 3. **Network Security**

| السيناريو | الإجراء الموصى به |
|-----------|------------------|
| **محلي فقط (نفس الجهاز)** | `host: "127.0.0.1"`، CORS `["*"]` آمن |
| **شبكة منزلية** | `host: "0.0.0.0"`، CORS محدد، Auth مفعل |
| **VPS / خارجي** | HTTPS عبر Nginx reverse proxy + Auth مفعل |

### نموذج Nginx Reverse Proxy (لـ VPS)
```nginx
server {
    listen 443 ssl;
    server_name your.domain.com;

    ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # لازم للـ streaming
    }
}
```

---

## 4. **Data Privacy**

### Policy لكل Provider

| Provider | Data Training Policy | مصدر |
|----------|--------------------|------|
| OpenRouter | ❌ لا تستخدم بياناتك | [docs](https://openrouter.ai/privacy) |
| Google Gemini | ✅ تستخدم للتدريب (خارج EU) | [docs](https://ai.google.dev/gemini-api/terms) |
| Groq | ❌ لا تستخدم | [docs](https://groq.com/privacy) |
| Mistral | ✅ تستخدم للتدريب (Experiment tier) | [docs](https://mistral.ai/terms) |
| GitHub Models | ❌ لا تستخدم | [docs](https://docs.github.com/en/github-models) |
| NVIDIA | ❌ Evaluation only | [docs](https://build.nvidia.com) |
| Cohere | ❌ Trial — غير تجاري | [docs](https://cohere.com/terms) |

### ⚠️ تنبيه للمستخدم
> بعض المصادر المجانية (Mistral, Gemini) قد تستخدم بياناتك لتحسين نماذجها.  
> **لا تستخدم هذا الـ Gateway لكود حساس** أو معلومات خاصة.  
> للكود الحساس: استخدم نماذج محلية (Ollama, LM Studio) أو اقرأ سياسة الخصوصية لكل Provider.

---

## 5. **Threat Model**

| التهديد | الاحتمال | التأثير | الحل |
|---------|:--------:|:-------:|------|
| **تسريب .env** | 🟢 نادر | Key leak | ملف `.env` في `.gitignore` |
| **قرصنة SQLite** | 🟢 نادر | Keys مشفرة — AES-256-GCM يحميها | التشفير القوي |
| **Man-in-the-Middle** | 🟡 محلي | محدود | استخدام `127.0.0.1` |
| **DoS (طلب كثير)** | 🟠 ممكن | Rate limits تنفذ | Fallback لـ Provider تاني |
| **كود حساس يطلع** | 🟠 ممكن | تسريب بيانات | تنبيه في README |
| **Dependency vuln** | 🟢 نادر | يعتمد على المكتبات | `pip audit` دوري |

---

## 6. **Security Checklist**

- [ ] `ENCRYPTION_KEY` في `.env` (غير في git)
- [ ] Auth مفعل (`auth.enabled: true`)
- [ ] `host: "127.0.0.1"` لو محلي
- [ ] `.gitignore` يمنع `.env` و `*.db`
- [ ] الـ Dashboard محمي بكلمة سر
- [ ] قراءة سياسة خصوصية كل Provider
- [ ] لا تستخدم الـ Gateway لكود حساس
- [ ] تحديث المكتبات دورياً (`pip install --upgrade -r requirements.txt`)
