# Task 06 — Provider: Gemini (format translation)

> **Phase 1** · depends on: 03, 04 · Reference: `IMPLEMENTATION_PLAN.md` §12.2 (row 2), §13 (Provider 2)

## Objective
Implement Google Gemini with a translation layer (non-OpenAI API). Proves the abstraction handles non-compatible providers.

## Files to create/modify
- `src/providers/gemini.py`

## Detailed spec
- Base URL `https://generativelanguage.googleapis.com/v1beta`. Auth is a **query param** `?key=API_KEY` (not Bearer).
- Endpoint: `POST {base}/models/{provider_model_id}:generateContent?key=...` (and `:streamGenerateContent` for streaming).
- **Request translation:** OpenAI `messages` → Gemini `{"contents":[{"role":..., "parts":[{"text":...}]}]}`. Map roles: user→user, assistant→model; system → `system_instruction`. Map `temperature/max_tokens/top_p` → `generationConfig` (`temperature`, `maxOutputTokens`, `topP`).
- **Response translation:** Gemini `candidates[0].content.parts[].text` → OpenAI `choices[0].message.content`; map `finishReason` → §2.3 enum (`STOP`→`stop`, `MAX_TOKENS`→`length`, etc.); build `usage` from `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`).
- Set `provider="gemini"`. Multimodal text+image supported (text-only required now).
- Error mapping → `ProviderError` codes as in task 05.

## Notes (sequencing & data realism)
- **API key source:** key comes from `.env` (`GEMINI_KEY`) via `key_manager` bootstrap (task 13). Never hard-code keys.
- **Model IDs:** §13 Gemini ids are forward-dated; verify each against the live Google model list before asserting a live call. Treat the request/response translation correctness as the **hard** acceptance; live calls best-effort.

## Acceptance criteria
- [ ] OpenAI-format request is correctly translated to Gemini and back; output is a schema-valid `ChatResponse`.
- [ ] System message routed to `system_instruction`; assistant role mapped to `model`.
- [ ] `usage` populated from `usageMetadata`.
- [ ] Auth uses query param, never a Bearer header.
- [ ] Error codes map correctly.

## Review checklist
- Role/finishReason mappings correct and complete.
- Streaming endpoint variant referenced for task 08.
- No key leaked in logs/URLs printed to logs.
