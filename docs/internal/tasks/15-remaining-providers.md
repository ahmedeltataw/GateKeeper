# Task 15 — Remaining 10 Providers

> **Phase 3** · depends on: 05, 06 · Reference: `IMPLEMENTATION_PLAN.md` §12.2, §13 (Providers 3–12)

## Objective
Implement the other ten providers, copying the OpenRouter pattern (or Gemini's translation pattern for non-compatible ones).

## Files to create/modify
- `src/providers/groq.py`, `mistral.py`, `github_models.py`, `nvidia.py`, `cerebras.py`, `cloudflare.py`, `zhipu.py`, `huggingface.py`, `aion.py`, `cohere.py`
- `src/providers/__init__.py` provider factory/registry (map provider_id → class).

## Detailed spec (per §12.2)
- **OpenAI-compatible (copy OpenRouter):** groq, mistral, github_models, cerebras, zhipu, huggingface, aion, cohere. Each: correct base_url, Bearer auth, id→provider_model_id mapping, `provider="<id>"`, error-code mapping, health ping.
- **Partial (nvidia):** OpenAI-ish; verify response shape, translate any deviations. Evaluation-only ToS note (non-commercial) — informational.
- **Translate (cloudflare):** base `.../accounts/{account_id}/ai/run/{model}`; needs `account_id` (from `.env` `CLOUDFLARE_ACCOUNT_ID`) + token; non-OpenAI body → translate request/response; quota is neurons (task 11).
- Provider-specific notes: groq TPM bottleneck; mistral rps=1, trains on data; cohere non-commercial 1000/mo; cerebras UNSTABLE → registry/fallback should treat as fallback-only; zhipu concurrent=1.
- `__init__.py`: a factory returning a provider instance per provider_id, used by `router.py`.

## Notes (data realism & known limitations)
- **Model IDs:** §13 ids are forward-dated; verify each `provider_model_id` against the provider's live model list before asserting live calls. Schema/translation correctness is the **hard** acceptance; live calls best-effort.
- **Cohere is NOT drop-in OpenAI:** the v2 chat endpoint is `/v2/chat` (not `/chat/completions`) with a different response envelope (`message.content[].text`). The generic `OpenAICompatibleProvider` will 404/mis-parse against it. Either give Cohere a dedicated translator or leave it as a documented non-functional stub (it's optional/non-commercial, 1000 calls/month).

## Acceptance criteria
- [ ] All 10 provider files exist and subclass `BaseProvider`.
- [ ] Each maps gateway ids → provider_model_id per §13 and sets `provider` correctly.
- [ ] Cloudflare translation works (request+response) and uses account_id.
- [ ] NVIDIA partial-compat handled.
- [ ] Provider factory resolves every provider_id from the registry.
- [ ] Error-code mapping consistent across all providers.

## Review checklist
- Base URLs/auth exactly per §12.2 (Cloudflare account_id; HF router URL; Zhipu paas/v4).
- No OpenAI assumptions leaked into Cloudflare/NVIDIA.
- Cerebras flagged fallback-only; data-training providers noted.
