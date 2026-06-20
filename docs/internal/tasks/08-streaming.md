# Task 08 — Streaming (SSE)

> **Phase 1** · depends on: 07 · Reference: `IMPLEMENTATION_PLAN.md` §2.4, §3.2

## Objective
Add Server-Sent Events streaming to `POST /v1/chat/completions` (and `/v1/responses`) for `stream:true`.

## Files to create/modify
- `src/api/routes.py` (streaming branch), provider `chat` streaming paths in `openrouter.py` and `gemini.py`.

## Detailed spec
- When `stream:true`, return `text/event-stream` via FastAPI `StreamingResponse`.
- Emit OpenAI chunks (§2.4): `object="chat.completion.chunk"`, incremental `choices[].delta`. `role:"assistant"` only in the first chunk; final chunk `delta:{}` + `finish_reason:"stop"`; terminate with `data: [DONE]`.
- Each chunk forwarded to the client immediately (no buffering).
- OpenRouter: pass `stream=true`, relay upstream SSE lines re-wrapped to our id.
- Gemini: use `:streamGenerateContent`, translate each streamed candidate chunk into an OpenAI delta chunk.
- **Mid-stream failure:** if the upstream errors after streaming started, end the stream by emitting `data: {"error":{"message":"...","type":"..."}}` then stop (per §2.4). Fallback is NOT attempted mid-stream.

## Acceptance criteria
- [ ] `stream:true` yields a valid SSE sequence ending in `data: [DONE]`.
- [ ] First chunk carries `role:"assistant"`; subsequent chunks carry only content deltas.
- [ ] Gemini streaming is translated to OpenAI chunk format.
- [ ] Upstream mid-stream error emits an error event and terminates cleanly.
- [ ] Content-Type is `text/event-stream`; chunks are not buffered.

## Review checklist
- Chunk shape matches §2.4 exactly (ids consistent across chunks).
- No fallback attempted once streaming has begun.
- Proxy buffering note (Nginx) not required locally but documented behavior preserved.
