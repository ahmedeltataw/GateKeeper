# 🔌 PROVIDERS.md — توصيل وتفاصيل كل Provider
> **الملف:** `docs/PROVIDERS.md`
> **المسار:** `D:\ai-project\free models`
> **آخر تحديث:** 16 يونيو 2026
> **حالة التوثيق:** 🟢 **Designed** — مواصفات الاتصال لكل Provider
> **حالة التنفيذ:** 🟡 **الكود لم يبدأ بعد**
> **إجمالي الـ Providers:** 12 (+1 Custom)

---

## 📋 **فهرس المحتويات**

1. [OpenRouter](#1-openrouter)
2. [Google Gemini (AI Studio)](#2-google-gemini-ai-studio)
3. [Groq](#3-groq)
4. [Mistral AI](#4-mistral-ai)
5. [GitHub Models](#5-github-models)
6. [NVIDIA NIM](#6-nvidia-nim)
7. [Cerebras](#7-cerebras)
8. [Cloudflare Workers AI](#8-cloudflare-workers-ai)
9. [Zhipu AI / Z AI](#9-zhipu-ai--z-ai)
10. [HuggingFace Inference API](#10-huggingface-inference-api)
11. [Aion Labs](#11-aion-labs)
12. [Cohere (اختياري)](#12-cohere-اختياري)
13. [مقارنة سريعة](#13-مقارنة-سريعة)

---

## 1. **OpenRouter**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [openrouter.ai](https://openrouter.ai) |
| **تسجيل API Key** | [keys](https://openrouter.ai/keys) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://openrouter.ai/api/v1` |
| **API Format** | ✅ **OpenAI-compatible** (نفس openai SDK تماماً) |
| **نوع Auth** | `Authorization: Bearer <key>` |

### الـ API Key
1. ادخل [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. سجل بـ GitHub/Google/Email
3. اضغط "Create Key"
4. انسخ الـ key (بيبدأ بـ `sk-or-v1-`)

### تفاصيل الـ API

#### طلب Chat
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-YOUR_KEY_HERE"
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",  # الـ ID الكامل
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### النماذج المجانية — قائمة الـ IDs الكاملة
```python
# ⚠️ هذه قائمة جزئية — القائمة الكاملة في models-classification.md → Provider 1
# الرابط المباشر: https://openrouter.ai/models?max_price=0
free_models = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "deepseek/deepseek-v4-flash:free",
    "minimax/minimax-m2.5:free",
]
```

#### Rate Limits
- **مجاني (No payment):** 20 RPM, 50 RPD
- **بعد $10 top-up:** 20 RPM, 1,000 RPD
- **ملاحظة:** لو حطيت $10، ترتفع حدودك 20x لـ 1,000 RPD

#### ملاحظات
- أكبر مصدر نماذج مجانية — 20+ موديل
- يعمل auto-failover بين الـ Providers اللي وراه
- يدعم streaming (`stream=True`)
- يدعم tool calling
- **بياناتك مش بتستخدم في التدريب**

---

## 2. **Google Gemini (AI Studio)**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [aistudio.google.com](https://aistudio.google.com) |
| **تسجيل API Key** | [apikey](https://aistudio.google.com/app/apikey) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://generativelanguage.googleapis.com/v1beta` |
| **API Format** | ⚠️ **SDK مختلف** (لكن في OpenAI-Compatible wrapper) |
| **نوع Auth** | `?key=API_KEY` (query parameter) |

### جلب API Key
1. ادخل [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. سجل بحساب Google
3. اضغط "Create API Key"
4. انسخ الـ key

### تفاصيل الـ API

#### عبر Google SDK
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_KEY")
model = genai.GenerativeModel('gemini-3.5-flash')
response = model.generate_content("Hello")
```

#### عبر OpenAI-Compatible Proxy (للتوحيد)
```python
# ملاحظة: Gemini API مختلف — لازم نحول لـ OpenAI format
# في الـ Gateway، هنعمل translation layer
# الطريقة المباشرة:
import requests

response = requests.post(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
    params={"key": "YOUR_KEY"},
    json={"contents": [{"parts": [{"text": "Hello"}]}]}
)
```

#### النماذج المجانية

| الموديل | الـ ID (Google Format) | أقصى Input | ملاحظات |
|---------|------------------------|:----------:|---------|
| **Gemini 3.5 Flash** | `gemini-3.5-flash` | 1,048,576 | 🔥 **أفضل موديل مجاني عام** |
| **Gemini 2.5 Pro** | `gemini-2.5-pro` | 2,097,152 | أقوى في الـ reasoning |
| **Gemini 2.5 Flash** | `gemini-2.5-flash` | 1,048,576 | سريع |
| **Gemini 3.1 Flash-Lite** | `gemini-3.1-flash-lite` | 1,048,576 | أسرع إصدار |

#### Rate Limits
- **Gemini 3.5 Flash:** 15 RPM, 1,500 RPD
- **Gemini 2.5 Pro:** 5 RPM, 50 RPD
- **Gemini 2.5 Flash:** 15 RPM, 1,500 RPD
- **Gemini 3.1 Flash-Lite:** 30 RPM, 1,500 RPD

#### ملاحظات
- ✅ Multimodal: يدخل نص + صورة + صوت + فيديو
- ⚠️ في EU/UK/Switzerland مش متاح الـ free tier
- ⚠️ بياناتك يمكن استخدامها للتدريب (خارج EU)
- ممتاز لـ long context (حتى 2M token)

---

## 3. **Groq**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [groq.com](https://groq.com) |
| **تسجيل API Key** | [console.groq.com/keys](https://console.groq.com/keys) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://api.groq.com/openai/v1` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### جلب API Key
1. ادخل [https://console.groq.com/keys](https://console.groq.com/keys)
2. سجل بـ GitHub/Google/Email
3. اضغط "Create API Key"
4. انسخ الـ key

### تفاصيل الـ API

#### طلب Chat
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="gsk_YOUR_KEY"
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### النماذج المجانية

| الموديل | الـ ID | سرعة | ملاحظات |
|---------|--------|:----:|---------|
| **Llama 3.3 70B** | `llama-3.3-70b-versatile` | 🔥 | أسرع وأقوى — 320 tok/s |
| **Llama 4 Scout** | `llama-4-scout-17b-16e-instruct` | 🔥 | MoE 17B |
| **Qwen3-32B** | `qwen-3-32b` | 🔥 | من علي بابا |
| **gpt-oss-120b** | `gpt-oss-120b` | 🔥 | موديل مفتوح 120B |
| **Gemma 4 31B** | `gemma4-31b-it` | 🔥 | من جوجل |
| **Mixtral 8x7B** | `mixtral-8x7b-32768` | 🟢 | قديم لكن سريع |
| **Llama 3.1 8B** | `llama-3.1-8b-instant` | 🔥🔥 | الأسرع — للردود السريعة |

#### Rate Limits
- 30 RPM, 1,000 RPD
- 6,000 TPM (ده الـ bottleneck الحقيقي)

#### ملاحظات
- **أسرع inference** في السوق — يستخدم LPU hardware
- مناسب للـ real-time chat والvoice agents
- يدعم streaming و tool calling
- يدخل صوت (Whisper model متاح)
- ⚠️ حدود TPM (6,000) مش RPM (30) — لو طلبك طويل، توصل للحد بسرعة

---

## 4. **Mistral AI**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [mistral.ai](https://mistral.ai) |
| **تسجيل API Key** | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) |
| **كارد؟** | ❌ لا (يحتاج فيريفي phone) |
| **Base URL** | `https://api.mistral.ai/v1` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### جلب API Key
1. ادخل [https://console.mistral.ai/api-keys](https://console.mistral.ai/api-keys)
2. سجل بـ Google/GitHub/Email
3. ارسل رمز التحقق للـ phone
4. اضغط "Create API Key"
5. انسخ الـ key

### تفاصيل الـ API

#### طلب Chat
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.mistral.ai/v1",
    api_key="YOUR_KEY"
)

response = client.chat.completions.create(
    model="codestral-latest",
    messages=[{"role": "user", "content": "Write Python code"}]
)
```

#### النماذج المجانية (Free Experiment Tier)

| الموديل | الـ ID | التخصص |
|---------|--------|--------|
| **Codestral** | `codestral-latest` | 💻 **أفضل موديل كودينج مجاني** |
| **Devstral** | `devstral-latest` | 💻 كودينج |
| **Mistral Medium 3.5** | `mistral-medium-2604` | 💻🔍🧠 شامل (128B) |
| **Mistral Small 4** | `mistral-small-latest` | 💻🔍 خفيف وسريع |
| **Mistral Large 3** | `mistral-large-latest` | 💻🔍🧠 أقوى موديل |
| **Magistral** | `magistral-2405` | 🧠 Reasoning |
| **Pixtral Large** | `pixtral-large-latest` | 👁️💻 Vision + Text |
| **Mistral Nemo** | `open-mistral-nemo` | 💻 موديل مفتوح 12B |

#### Rate Limits
- 1 RPS (request per second)
- 500K TPM (tokens per minute)
- **~1B tokens/month** (أكتر free tier سخاءً)

#### ملاحظات
- ⚠️ **بيجمع بياناتك للتدريب** — في الـ "Experiment" tier
- **أفضل مصدر للكودينج** — Codestral متفوق على كتير موديلات
- جميع الموديلات عندها context 256K (كبير جداً)
- الـ free tier من أكتر الحاجة generosity
- يدعم streaming + tool calling

---

## 5. **GitHub Models**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [github.com/marketplace/models](https://github.com/marketplace/models) |
| **تسجيل API Key** | حساب GitHub فقط |
| **كارد؟** | ❌ لا (حساب GitHub فقط) |
| **Base URL** | `https://models.inference.ai.azure.com` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <github_token>` |

### جلب API Key
1. سجل دخول GitHub
2. ادخل [https://github.com/settings/tokens](https://github.com/settings/tokens)
3. أنشئ Personal Access Token (classic) ✅ (fine-grained مش ضروري)
4. انسخ الـ token

### تفاصيل الـ API

#### طلب Chat
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key="ghp_YOUR_GITHUB_TOKEN"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### النماذج المجانية 🔥

| الموديل | الـ ID | القوة | ملاحظات |
|---------|--------|:----:|---------|
| **GPT-4o** | `gpt-4o` | **S** | 🔥 أقوى موديل على GitHub مجاناً |
| **GPT-4o Mini** | `gpt-4o-mini` | **A** | أسرع وأرخص |
| **Claude 3.5 Sonnet** | `claude-3.5-sonnet` | **S** | 🔥 ممتاز في الكود والكتابة |
| **Claude 3.5 Haiku** | `claude-3.5-haiku` | **A** | أسرع كلود |
| **Llama 3.3 70B** | `llama-3.3-70b` | **A** | من Meta |
| **Phi-4** | `phi-4` | **B** | من مايكروسوفت |

#### Rate Limits
- **GPT-4o / Claude:** 15 RPM, 150 RPD
- **Llama / Phi:** 15 RPM, 1,000 RPD

#### ملاحظات
- 🔥 **أفضل مصدر مجاني لموديلات Frontier** — GPT-4o و Claude Sonnet ع الفاضي
- Azure endpoint — سرعة ممتازة
- يدعم streaming
- ماهو مزودج: كل موديل عنده حدود مختلفة
- ⚠️ الـ limits على GPT-4o (150 RPD) مش كتير، لكن يكفي للاستخدام الشخصي

---

## 6. **NVIDIA NIM**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [build.nvidia.com](https://build.nvidia.com) |
| **تسجيل API Key** | [build.nvidia.com](https://build.nvidia.com) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://integrate.api.nvidia.com/v1` |
| **API Format** | ⚠️ **متوافق جزئياً** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### جلب API Key
1. ادخل [https://build.nvidia.com](https://build.nvidia.com)
2. سجل بحساب NVIDIA
3. اختار أي نموذج → "Get API Key"
4. انسخ الـ key

### تفاصيل الـ API

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="nvapi-YOUR_KEY"
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra",
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### النماذج المجانية

| الموديل | الـ ID | المواصفات |
|---------|--------|-----------|
| **Nemotron 3 Ultra** | `nvidia/nemotron-3-ultra` | 550B MoE (55B active) |
| **Nemotron 3 Super** | `nvidia/nemotron-3-super` | 120B MoE (12B active) |

#### Rate Limits
- 40 RPM
- ~1,000 inference credits/day

#### ملاحظات
- ⚠️ **Evaluation-only Terms of Service** — مش للاستخدام التجاري
- Nemotron 3 Ultra من أقوى الموديلات المجانية في الكودينج
- يدخل context 1M tokens
- الـ API format مختلف شوية — يحتاج تحويل

---

## 7. **Cerebras**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| **تسجيل API Key** | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://api.cerebras.ai/v1` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### النماذج المجانية
| الموديل | الـ ID |
|---------|--------|
| **gpt-oss-120b** | `gpt-oss-120b` |
| **ZAI GLM-4.7** | `zai-glm-4.7` |

#### Rate Limits
- **gpt-oss-120b:** 30 RPM, 14,400 RPD
- **zai-glm-4.7:** 10 RPM, 100 RPD
- Shared: 1M TPD

#### ⚠️ ملاحظة مهمة
**غير مستقر!** — Cerebras معروف إنه بيحذف نماذج من الـ free tier بدون إشعار. في مايو 2026، حذف 10 نماذج فجأة. **لا تعتمد عليه كمصدر أساسي** — استخدمه كـ fallback فقط.

---

## 8. **Cloudflare Workers AI**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [workers.ai](https://workers.ai) |
| **تسجيل API Key** | [dash.cloudflare.com](https://dash.cloudflare.com) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run` |
| **API Format** | ❌ مختلف (يحتاج تحويل) |
| **نوع Auth** | `Authorization: Bearer <key>` |

### النماذج المجانية
| الموديل | الـ ID |
|---------|--------|
| **Llama 4 Scout 17B** | `@cf/meta/llama-4-scout-17b-16e-instruct` |
| **Llama 3.3 70B** | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| **gpt-oss-120b** | `@cf/openai/gpt-oss-120b` |
| **Gemma 4 26B** | `@cf/google/gemma-4-26b-it` |

#### Rate Limits: 10,000 neurons/day
نظام غريب — مش tokens ولا requests. الـ neurons تحتاج فهم خاص.

#### ملاحظات
- متنوع — 50+ موديل
- نظام neurons معقد
- ليس Open AI-compatible مباشرة — يحتاج تحويل

---

## 9. **Zhipu AI / Z AI**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [open.bigmodel.cn](https://open.bigmodel.cn) |
| **تسجيل API Key** | [open.bigmodel.cn](https://open.bigmodel.cn) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://open.bigmodel.cn/api/paas/v4` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### النماذج المجانية
| الموديل | الـ ID | التخصص |
|---------|--------|--------|
| **GLM-4.7-Flash** | `glm-4.7-flash` | 💻🔍🧠 قوي في الكود |
| **GLM-4.6V-Flash** | `glm-4.6v-flash` | 👁️💻 يدخل صور |

#### Rate Limits: 1 concurrent request

#### ملاحظات
- نماذج صينية قوية جداً في الكودينج
- GLM-4.7-Flash بينافس موديلات A-tier
- الـ site بالصيني — يحتاج ترجمة أو حساب دولي

---

## 10. **HuggingFace Inference API**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [huggingface.co](https://huggingface.co) |
| **تسجيل API Key** | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://router.huggingface.co/hf-inference/v1` |
| **API Format** | ✅ **OpenAI-compatible** (عبر الـ router الجديد) |
| **نوع Auth** | `Authorization: Bearer <key>` |

### جلب API Key
1. ادخل [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. سجل بحساب HuggingFace
3. اضغط "New Token"
4. اختار `read` role
5. انسخ الـ key

### النماذج المجانية (Serverless)
أي موديل <10GB تقدر تستخدمه مجاناً. أشهرها:

| الموديل | الـ ID |
|---------|--------|
| **Llama 3.3 70B** | `meta-llama/llama-3.3-70b-instruct` |
| **DeepSeek V4** | `deepseek-ai/deepseek-v4` |
| **Command A+** | `coherelabs/command-a-plus-05-2026` |
| **Qwen 3.6** | `qwen/qwen-3.6-35b-a3b` |
| **Mistral Small 4** | `mistralai/mistral-small-4-119b-2603` |
| **North Mini Code** | `coherelabs/north-mini-code` |

#### Rate Limits
- متغير حسب الموديل
- بطيء نسبياً (serverless inference)
- نسبة availability مش مضمونة

#### ملاحظات
- **أكبر مكتبة موديلات مفتوحة المصدر** — آلاف الموديلات
- الـ Serverless Inference أبطأ من باقي المصادر
- مناسب للنماذج النادرة/غير المتاحة في المصادر التانية

---

## 11. **Aion Labs**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [aionlabs.ai](https://aionlabs.ai) |
| **تسجيل API Key** | عبر Discord |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://api.aionlabs.ai/v1` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### النماذج المجانية
| الموديل | الـ ID |
|---------|--------|
| **Aion 2.5** | `aion-2.5` |
| **Aion 2.0** | `aion-2.0` |
| **Aion-RP 1.0 (8B)** | `aion-rp-llama-3.1-8b` |

#### Rate Limits
- 15 RPM
- 20K TPD

#### ملاحظات
- التخصص: **Roleplay و Storytelling** — مش للكودينج
- الموديلات صغيرة وضعيفة مقارنة بباقي المصادر
- ممكن نستبعدها من القائمة لو عايزين

---

## 12. **Cohere (اختياري)**

| الحقل | القيمة |
|-------|--------|
| **الموقع** | [cohere.com](https://cohere.com) |
| **تسجيل API Key** | [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys) |
| **كارد؟** | ❌ لا |
| **Base URL** | `https://api.cohere.com/v2` |
| **API Format** | ✅ **OpenAI-compatible** |
| **نوع Auth** | `Authorization: Bearer <key>` |

### النماذج المجانية (Trial — 1,000 call/شهر)

| الموديل | الـ ID | المواصفات |
|---------|--------|-----------|
| **Command A+ 218B** | `command-a-plus-05-2026` | MoE قوي |
| **Command A 111B** | `command-a-03-2025` | 256K context |
| **Command R+** | `command-r-plus-08-2024` | RAG specialist |
| **Command R** | `command-r-08-2024` | — |

#### Rate Limits
- 20 RPM
- **1,000 call/شهر** (33 call/يوم)
- **غير تجاري** — Trial key non-commercial only

#### ملاحظات
- **غير تجاري** — ممنوع استخدامه في مشاريع تجارية
- 1,000 call/شهر فقط — ينفذ بسرعة
- يستحق وضعه في القائمة فقط لو محتاج موديل معين عنده

---

## 13. **مقارنة سريعة**

| Provider | Speed | Quality | Limits | Setup | للكودينج؟ |
|----------|:-----:|:-------:|:------:|:-----:|:---------:|
| **OpenRouter** | 🟢 | 🟢🟢🟢 | 🟡 50 RPD | 🟢 سهل | ✅ ممتاز |
| **Gemini** | 🟢 | 🔥 S-Tier | 🟢 1500 RPD | 🟢 سهل | ✅ جيد جداً |
| **Groq** | 🔥🔥 | 🟢🟢 | 🟡 1000 RPD + TPM | 🟢 سهل | ✅ ممتاز |
| **Mistral** | 🟢 | 🟢🟢🟢 | 🔥 1B/شهر | 🟡 Phone | ✅ **أفضل كودينج** |
| **GitHub Models** | 🟢 | 🔥 **S-Tier** | 🟡 150 RPD | 🟢 سهل | ✅ **GPT-4o مجاناً** |
| **NVIDIA** | 🟢 | 🟢🟢 | 🟢 40 RPM | 🟢 سهل | ✅ جيد |
| **Cerebras** | 🔥 | 🟢 | 🔥 14K RPD | 🟢 سهل | ✅ لكن **غير مستقر** |
| **Cloudflare** | 🟡 | 🟢 | 🟡 neurons | 🟠 معقد | ✅ |
| **Zhipu** | 🟡 | 🟢🟢 | 🔴 1 concurrent | 🟠 صيني | ✅ جيد جداً |
| **HuggingFace** | 🔴 | 🟢 | 🟡 متغير | 🟢 سهل | ✅ |
| **Aion** | 🟡 | 🔴 | 🟡 20K TPD | 🟡 Discord | ❌ Story فقط |
| **Cohere** | 🟢 | 🟢🟢 | 🔴 1K/شهر | 🟢 سهل | ✅ غير تجاري |

---

## 📌 **ملاحظات عامة**

### ترتيب الأولوية للتوصيل (من الأسهل للأصعب):
1. **OpenRouter** — أسهل API (OpenAI-compatible, 20+ models)
2. **GitHub Models** — أسهل تسجيل (GitHub account بس)
3. **Groq** — أسرع، OpenAI-compatible
4. **Gemini** — أقوى موديل مجاني (يحتاج تحويل format)
5. **Mistral** — 1B tokens/شهر (يحتاج phone)
6. **NVIDIA** — Nemotron قوي
7. **Cloudflare** — متنوع لكن معقد
8. **HuggingFace** — آلاف الموديلات
9. **Zhipu** — قوي لكن بالصيني
10. **Cerebras** — سريع لكن غير مستقر
11. **Aion** — تخصصي (story only)
12. **Cohere** — محدود جداً

### طريقة الـ Test لكل Provider
```bash
# اختبار بسيط لكل Provider
curl http://localhost:8000/v1/models | jq '.'
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{"model": "codestral", "messages": [{"role": "user", "content": "Say hi"}]}'
```

> **عند إضافة Provider جديد:** انسخ تنسيق أي Provider موجود في هذا الملف، واملأ بياناته.
