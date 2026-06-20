# 📊 GateKeeper — Status & Setup Report
> Generated 2026-06-17. Single source for "what is this, does it work, and how do I turn it on."

---

## 1. Project status (current)

| Area | State |
|------|-------|
| **Build** | ✅ Fully implemented (`src/api`, `src/core`, `src/providers`). |
| **Tests** | ✅ 21/21 passing (`python -m pytest -q`). |
| **Server boot** | ✅ Verified — `/health` and `/v1/models` respond. |
| **Catalog** | ✅ Rebuilt: **46 models across 10 providers**, all FREE + **no payment card** (doc-verified 2026-06-17). |
| **Old fictional models** | ✅ Removed (`gemini-3.5-flash`, `gpt-4o` free, `deepseek-v4-flash`, …). |
| **What's needed to use it** | ⛔ **At least one provider API key** (see §4). Without a key, chat returns a clean `429`, not a crash. |

**Verification caveat:** models are **doc-verified** (confirmed against each provider's current documentation as free/no-card), **not live-call verified** — I don't have your keys. Open-model menus rotate weekly; the gateway's health check prunes anything that 401s/404s at runtime. Confirm your chosen model resolves on `/v1/models` after adding a key.

### Recent fixes applied in this pass
- Rebuilt the model catalog with **real, verified free model IDs** (was forward-dated/fictional).
- Updated endpoints: GitHub Models → `https://models.github.ai/inference` (+ `X-GitHub-Api-Version` header); Zhipu → `https://api.z.ai/api/paas/v4`; HuggingFace → `https://router.huggingface.co/v1`.
- Realigned the Quality Router preferred chains to the new IDs.
- Fixed earlier blockers: `/v1/responses` crash, cross-provider fallback that disabled healthy providers, 404→model-removed (not provider-disable), 401→invalidate key, empty-key now returns a clean error instead of a 500.

---

## 2. Providers in the catalog (all FREE, no card)

Ordered as in `models-classification.md`. Strength S=frontier … C=decent.

| # | Provider | Models | Best for | Caveats |
|---|----------|:------:|----------|---------|
| 1 | **OpenRouter** | 6 | catch-all / fallback | `:free` slugs rotate; 50 RPD until $10 ever spent |
| 2 | **Google Gemini** | 4 | vision, 1M context, reasoning | ⚠️ free tier **trains on your data** |
| 3 | **Groq** | 6 | speed, general, coding | open-weight only; preview models |
| 4 | **Mistral** | 6 | coding (Codestral), reasoning | phone verify; ⚠️ trains on data by default |
| 5 | **GitHub Models** | 5 | only no-card GPT-4o/4.1 | tight limits (15/150) |
| 6 | **NVIDIA NIM** | 5 | huge models (405B, R1) | prototyping only |
| 7 | **Cerebras** | 2 | fastest, big daily budget | ⚠️ 8K context cap on free |
| 8 | **Cloudflare** | 7 | 10k neurons/day, **no training** | neuron budget |
| 9 | **Z.ai / Zhipu** | 3 | coding, reasoning | ~1 concurrent |
| 10 | **HuggingFace** | 2 | evaluation only | ⚠️ ~$0.10/month credit |

**Excluded:** Aion (no permanent free model), Cohere (non-commercial + not OpenAI-compatible). Together/Scaleway/Hyperbolic/Nebius need a card. Chutes/GLHF discontinued.

---

## 3. How to run

```bash
cd "D:/ai-project/free models"

# 1. (first time) install deps
python -m venv venv && venv/Scripts/activate     # Windows; or: source venv/bin/activate
pip install -r requirements.txt

# 2. ensure .env exists with ENCRYPTION_KEY (already set in your repo) + >=1 provider key (see §4)

# 3. (re)generate the registry if you edited the catalog
python scripts/sync_models.py

# 4. start the gateway
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000
#    (or: python -m src.api.server)

# 5. smoke test
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models -H "Authorization: Bearer sk-local"
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-local" -H "Content-Type: application/json" \
  -d '{"model":"auto","task_type":"coding","messages":[{"role":"user","content":"Say hi"}]}'
```

Connect any OpenAI-compatible agent: **base URL** `http://127.0.0.1:8000/v1`, **API key** `sk-local` (from `config.yaml` → `auth.api_key`). Use `"model":"auto"` to let the Quality Router pick, or a specific gateway ID from `/v1/models`.

---

## 4. ⭐ What YOU need to add to `.env` to make it work

You need `ENCRYPTION_KEY` (already set) **plus at least one** provider key below. Add the line(s) to `.env`, then restart. **Easiest, 100% no-card, ~2-minute signups:**

| Provider | Add to `.env` | Get the key here | Notes |
|----------|---------------|------------------|-------|
| **Groq** ⭐ | `GROQ_KEY=gsk_...` | https://console.groq.com/keys | Fastest, instant, easiest. **Start here.** |
| **Google Gemini** ⭐ | `GEMINI_KEY=AIza...` | https://aistudio.google.com/apikey | Strong + vision + 1M ctx. ⚠️ trains on data. |
| **OpenRouter** ⭐ | `OPENROUTER_KEY=sk-or-v1-...` | https://openrouter.ai/settings/keys | Dozens of free models, one key. |
| **Cloudflare** | `CLOUDFLARE_ACCOUNT_ID=...`<br>`CLOUDFLARE_API_TOKEN=...` | https://dash.cloudflare.com/profile/api-tokens | 10k neurons/day, no training. Needs both values. |
| **Cerebras** | `CEREBRAS_KEY=csk-...` | https://cloud.cerebras.ai | Fastest; 8K context cap. |
| **NVIDIA** | `NVIDIA_KEY=nvapi-...` | https://build.nvidia.com | Llama 405B, DeepSeek R1. |
| **Mistral** | `MISTRAL_KEY=...` | https://console.mistral.ai | Phone verify; trains on data. |
| **GitHub Models** | `GITHUB_KEY=github_pat_...` | https://github.com/settings/personal-access-tokens (scope `models:read`) | Only no-card GPT-4o/4.1. |
| **Z.ai / Zhipu** | `ZHIPU_KEY=...` | https://z.ai/manage-apikey/apikey-list | Strong coding (GLM). |
| **HuggingFace** | `HF_KEY=hf_...` | https://huggingface.co/settings/tokens/new | Eval only (~$0.10/mo). |

> **Key import:** on first startup, if the SQLite DB has **no** keys yet, the gateway auto-imports any `*_KEY` it finds in `.env` (encrypted). If you add keys later and they don't take, either add them via the dashboard (`http://127.0.0.1:8000/dashboard`) or delete `server/data/gateway.db` and restart.

### Recommended minimum to "just work"
Add **`GROQ_KEY`** (2-minute signup, no card) → restart → call with `"model":"auto"`. The Quality Router will route coding/reasoning/search to Groq's `openai/gpt-oss-120b` and `llama-3.3-70b-versatile`. Add `GEMINI_KEY` too for vision and 1M-context tasks.

> ⚠️ **Privacy:** Gemini (free) and Mistral (Experiment) may train on your prompts. For anything sensitive, prefer Cloudflare (no training) or a local model. Don't send secrets through training-tier providers.

---

## 5. Match the key to the model
A key only serves **its own** provider's models. With just `GROQ_KEY`, request a `groq-*` model (or `"auto"`). Calling, say, `gemini-2.5-flash` without `GEMINI_KEY` will fall through to whatever provider you do have a key for (via the fallback chain), or return `429` if none match. `"auto"` is the safe default — it picks among providers that actually have budget.
