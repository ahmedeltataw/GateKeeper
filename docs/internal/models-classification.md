# 📋 تصنيف الموديلات المجانية — Free Models Catalog
> **Source of Truth** — هذا الملف هو المرجع الأساسي لكل الموديلات في المشروع.
> أي إضافة أو حذف أو تعديل لأي موديل يتم هنا أولاً، ثم في `scripts/sync_models.py` ثم `python scripts/sync_models.py` لتوليد `models_registry.json`.
>
> **آخر تحديث / تحقق:** 17 يونيو 2026 — كل الموديلات **doc-verified** (متحقق منها مقابل توثيق كل مزود الحالي) على أنها **مجانية وبدون كارت دفع**.
> ⚠️ **ليست live-call verified** — قوائم الموديلات المفتوحة تتغير أسبوعياً؛ شغّل Health Check عند الإقلاع واحذف أي موديل يرجع 401/404.

---

## 📖 دليل المصطلحات (Legend)
- **Rate limits:** RPM=طلب/دقيقة · RPD=طلب/يوم · TPM=توكن/دقيقة · TPD=توكن/يوم · RPS=طلب/ثانية · neurons=وحدة Cloudflare · concurrent=طلب متزامن
- **Strength:** S=Frontier · A=Strong · B=Good · C=Decent
- **Use cases:** coding 💻 · search 🔍 · reasoning 🧠 · creative ✍️ · data 📊 · vision 👁️
- **API Format:** ✅ OpenAI-compatible · ⚠️ جزئي · ❌ يحتاج تحويل

> **ملاحظة خصوصية:** "مجاني بدون كارت" ≠ "خاص". Gemini (free) و Mistral (Experiment) **يستخدمان بياناتك للتدريب افتراضياً**. Cloudflare و OVH لا يدرّبان.

---

## 🔥 Provider 1: OpenRouter
> **Key:** https://openrouter.ai/settings/keys · **كارت:** ❌ · **Base:** `https://openrouter.ai/api/v1` · **Format:** ✅
> **Limits:** 20 RPM · 50 RPD (ترتفع لـ 1000 RPD لو اشتريت ≥$10 مرة واحدة) · عام (مفاتيح إضافية لا تساعد)
> ⚠️ موديلات `:free` تتغير ~أسبوعياً — تحقق عبر `GET /api/v1/models`.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context | Limits |
|---|---|:--:|---|:--:|---|
| `or-gpt-oss-120b` | `openai/gpt-oss-120b:free` | A | 💻🔍🧠 | 128K | 20/50 |
| `or-qwen3-coder` | `qwen/qwen3-coder:free` | A | 💻 | 256K | 20/50 |
| `or-llama-3.3-70b` | `meta-llama/llama-3.3-70b-instruct:free` | A | 🔍💻✍️🧠 | 128K | 20/50 |
| `or-glm-4.5-air` | `z-ai/glm-4.5-air:free` | A | 🧠💻 | 128K | 20/50 |
| `or-gemma-4-31b` | `google/gemma-4-31b-it:free` | B | ✍️🔍 | 128K | 20/50 |
| `or-auto` | `openrouter/free` | B | default | 128K | 20/50 |

## 🔥 Provider 2: Google Gemini (AI Studio)
> **Key:** https://aistudio.google.com/apikey · **كارت:** ❌ · **Base:** `…/v1beta` (+ `/v1beta/openai/`) · **Format:** ⚠️→✅
> **Auth:** query param `?key=` أو Bearer · ⚠️ **يدرّب على بياناتك في الطبقة المجانية** · الحدود اتقلّصت ~ديسمبر 2025

| Gateway ID | Provider Model ID | Strength | Use Cases | Context | Limits |
|---|---|:--:|---|:--:|---|
| `gemini-2.5-pro` | `gemini-2.5-pro` | S | 💻🔍🧠✍️📊👁️ | 1M | 5/100 |
| `gemini-2.5-flash` | `gemini-2.5-flash` | A | 💻🔍✍️📊👁️ | 1M | 10/250 |
| `gemini-2.5-flash-lite` | `gemini-2.5-flash-lite` | B | 💻🔍👁️ | 1M | 15/1000 |
| `gemini-2.0-flash` | `gemini-2.0-flash` | B | 🔍💻👁️ | 1M | 15/1500 |

## 🔥 Provider 3: Groq
> **Key:** https://console.groq.com/keys · **كارت:** ❌ · **Base:** `https://api.groq.com/openai/v1` · **Format:** ✅
> **أسرع inference.** Limits ~30 RPM، RPD 1000–14400، TPM منخفض (6K–30K). موديلات preview "مش للإنتاج".

| Gateway ID | Provider Model ID | Strength | Use Cases | Context | Limits |
|---|---|:--:|---|:--:|---|
| `groq-gpt-oss-120b` | `openai/gpt-oss-120b` | A | 💻🔍🧠 | 128K | 30/1000 |
| `groq-gpt-oss-20b` | `openai/gpt-oss-20b` | B | 💻🧠🔍 | 128K | 30/1000 |
| `groq-llama-3.3-70b` | `llama-3.3-70b-versatile` | A | 💻🔍🧠📊 | 128K | 30/1000 |
| `groq-llama-3.1-8b` | `llama-3.1-8b-instant` | C | 🔍💻 | 128K | 30/14400 |
| `groq-qwen3-32b` | `qwen/qwen3-32b` | A | 🧠💻🔍 | 128K | preview |
| `groq-llama-4-scout` | `meta-llama/llama-4-scout-17b-16e-instruct` | B | 🔍👁️💻 | 128K | preview |

## 🔥 Provider 4: Mistral AI
> **Key:** https://console.mistral.ai · **كارت:** ❌ (يحتاج تأكيد هاتف) · **Base:** `https://api.mistral.ai/v1` · **Format:** ✅
> ⚠️ **Experiment tier يدرّب على بياناتك افتراضياً** — اعمل opt-out من الـ console. ~1 RPS.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context | Notes |
|---|---|:--:|---|:--:|---|
| `mistral-large` | `mistral-large-latest` | S | 💻🔍🧠📊 | 128K | flagship |
| `mistral-medium` | `mistral-medium-latest` | A | 💻🔍🧠 | 128K | balanced |
| `mistral-magistral` | `magistral-medium-latest` | A | 🧠💻 | 128K | reasoning |
| `mistral-small` | `mistral-small-latest` | B | 💻🔍✍️ | 128K | cheap |
| `mistral-pixtral` | `pixtral-large-latest` | A | 👁️💻 | 128K | vision |
| `mistral-codestral` | `codestral-latest` | A | 💻 | 256K | ⚠️ قد يتطلب billing |

## 🔥 Provider 5: GitHub Models
> **Key:** PAT بصلاحية `models:read` — https://github.com/settings/personal-access-tokens · **كارت:** ❌
> **Base:** `https://models.github.ai/inference` · **Format:** ✅ (+ header `X-GitHub-Api-Version`)
> **المصدر الوحيد بدون كارت لـ GPT-4o/4.1.** Limits ضيقة: 15/150 (low)، 10/50 (high)، 8K in/4K out.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context | Limits |
|---|---|:--:|---|:--:|---|
| `gh-gpt-4.1` | `openai/gpt-4.1` | A | 💻🔍🧠📊 | 128K | 10/50 |
| `gh-gpt-4o` | `openai/gpt-4o` | A | 💻🔍✍️📊👁️ | 128K | 15/150 |
| `gh-gpt-4o-mini` | `openai/gpt-4o-mini` | B | 💻🔍📊 | 128K | 15/150 |
| `gh-llama-3.3-70b` | `meta/llama-3.3-70b-instruct` | A | 💻🔍📊 | 128K | 15/150 |
| `gh-deepseek-r1` | `deepseek/DeepSeek-R1` | A | 🧠💻 | 128K | ~1/8 |

## 🔥 Provider 6: NVIDIA NIM
> **Key:** https://build.nvidia.com (`nvapi-…`) · **كارت:** ❌ · **Base:** `https://integrate.api.nvidia.com/v1` · **Format:** ✅
> ~40 RPM/model، للتجريب فقط. تحقق من نسخة الموديل في صفحته.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context |
|---|---|:--:|---|:--:|
| `nv-llama-3.1-405b` | `meta/llama-3.1-405b-instruct` | S | 🧠💻🔍 | 128K |
| `nv-deepseek-r1` | `deepseek-ai/deepseek-r1` | S | 🧠💻 | 128K |
| `nv-llama-3.3-70b` | `meta/llama-3.3-70b-instruct` | A | 💻🔍📊 | 128K |
| `nv-qwen2.5-coder-32b` | `qwen/qwen2.5-coder-32b-instruct` | A | 💻 | 128K |
| `nv-nemotron-70b` | `nvidia/llama-3.1-nemotron-70b-instruct` | A | 🧠💻 | 128K |

## 🔥 Provider 7: Cerebras
> **Key:** https://cloud.cerebras.ai · **كارت:** ❌ · **Base:** `https://api.cerebras.ai/v1` · **Format:** ✅
> ⚡ **الأسرع** (~2000+ tok/s) و **أكبر budget يومي** (~1M TPD). ⚠️ **الطبقة المجانية تحدّ الـ context بـ 8K**. القائمة تتغير كثيراً.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context |
|---|---|:--:|---|:--:|
| `cb-gpt-oss-120b` | `gpt-oss-120b` | A | 💻🔍🧠 | 8K |
| `cb-glm-4.7` | `zai-glm-4.7` | A | 🧠💻 | 8K (preview) |

## 🔥 Provider 8: Cloudflare Workers AI
> **Token:** https://dash.cloudflare.com/profile/api-tokens (+ Account ID) · **كارت:** ❌ · **Format:** ✅ (عبر `/ai/v1`) أو محوّل عبر `/ai/run`
> **10,000 neurons/يوم** · **لا يدرّب على بياناتك**. الـ IDs بـ `@cf/` حرفياً.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context |
|---|---|:--:|---|:--:|
| `cf-gpt-oss-120b` | `@cf/openai/gpt-oss-120b` | A | 💻🔍🧠 | 128K |
| `cf-llama-3.3-70b` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | A | 💻🔍 | 131K |
| `cf-qwen2.5-coder-32b` | `@cf/qwen/qwen2.5-coder-32b-instruct` | A | 💻 | 32K |
| `cf-qwq-32b` | `@cf/qwen/qwq-32b` | A | 🧠 | 32K |
| `cf-llama-4-scout` | `@cf/meta/llama-4-scout-17b-16e-instruct` | A | 🔍💻 | 131K |
| `cf-llama-3.2-11b-vision` | `@cf/meta/llama-3.2-11b-vision-instruct` | B | 👁️ | 128K |
| `cf-llama-3.1-8b` | `@cf/meta/llama-3.1-8b-instruct-fp8-fast` | B | 🔍💻 | 128K |

## 🔥 Provider 9: Z.ai / Zhipu (GLM)
> **Key:** https://z.ai/manage-apikey/apikey-list (دولي) أو https://open.bigmodel.cn (الصين) · **كارت:** ❌
> **Base:** `https://api.z.ai/api/paas/v4` · **Format:** ✅ · ~1 concurrent · موديلات Flash مجانية دائماً.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context |
|---|---|:--:|---|:--:|
| `glm-4.7-flash` | `glm-4.7-flash` | A | 💻🔍🧠📊 | 200K |
| `glm-4.5-flash` | `glm-4.5-flash` | A | 💻🧠🔍 | 128K |
| `glm-4.6v-flash` | `glm-4.6v-flash` | B | 👁️💻 | 128K |

## 🔥 Provider 10: HuggingFace Inference Providers
> **Token:** https://huggingface.co/settings/tokens/new · **كارت:** ❌ · **Base:** `https://router.huggingface.co/v1` · **Format:** ✅
> ⚠️ **~$0.10/شهر فقط** — للتقييم فقط. PRO ($9/شهر) → $2.

| Gateway ID | Provider Model ID | Strength | Use Cases | Context |
|---|---|:--:|---|:--:|
| `hf-deepseek-r1` | `deepseek-ai/DeepSeek-R1` | A | 🧠💻 | 128K |
| `hf-llama-3.3-70b` | `meta-llama/Llama-3.3-70B-Instruct` | A | 💻🔍📊 | 128K |

---

## ⛔ مستبعد من الكتالوج (Excluded)
هذه المزودات **ليست** في الـ registry الحالي ولها أسباب:

| Provider | السبب |
|---|---|
| **Aion Labs** | لا يوجد موديل مجاني دائم — كل الموديلات مدفوعة per-token. |
| **Cohere** | غير تجاري (Trial 1000/شهر) **و** ليس OpenAI-compatible (v2 `/v2/chat` بصيغة مختلفة) — يحتاج محوّل مخصص. الموديول موجود لكن غير مفعّل. |
| **Together / Scaleway / Hyperbolic / Nebius** | تتطلب كارت دفع. |
| **Chutes / GLHF** | الطبقة المجانية أُلغيت / الخدمة متوقفة. |

### إضافات اختيارية بدون كارت (غير مضافة بعد)
- **SambaNova** (`https://api.sambanova.ai/v1`, ✅) — موديلات قوية لكن **20 طلب/يوم فقط**.
- **OVHcloud AI Endpoints** (`https://oai.endpoints.kepler.ai.cloud.ovh.net/v1`, ✅) — **مجهول بدون مفتاح** (2 req/min/IP)، لا يدرّب على البيانات.

---

## 📊 Top Picks (verified, no card)
| المهمة | الترتيب |
|---|---|
| 🏆 ابدأ بـ | **Groq** → **Gemini (AI Studio)** → **OpenRouter** → **Cloudflare** |
| 💻 Coding | `or-qwen3-coder` · `mistral-codestral` · `groq-gpt-oss-120b` · `cf-qwen2.5-coder-32b` |
| 🧠 Reasoning | `gemini-2.5-pro` · `nv-deepseek-r1` · `groq-gpt-oss-120b` · `cb-gpt-oss-120b` |
| 🔍 Search/General | `gemini-2.5-flash` · `groq-llama-3.3-70b` · `or-llama-3.3-70b` |
| 👁️ Vision | `gemini-2.5-flash` · `mistral-pixtral` · `cf-llama-3.2-11b-vision` |
| 📊 Data | `gh-gpt-4o` · `mistral-large` · `groq-llama-3.3-70b` |

---

## 📝 إرشادات التحديث
1. عدّل هذا الملف أولاً (مصدر الحقيقة).
2. عدّل القائمة المطابقة في `scripts/sync_models.py` (`_MODELS`).
3. شغّل `python scripts/sync_models.py` لتوليد `models_registry.json`.
4. حدّث `_PREFERRED_CHAINS` في `src/core/quality_router.py` لو أضفت/حذفت موديلات في القمة.

> **المصادر:** توثيق كل مزود الرسمي (Groq/Cerebras/Google/OpenRouter/Cloudflare/NVIDIA/Mistral/Z.ai/GitHub/HuggingFace) — تم التحقق 17 يونيو 2026.
