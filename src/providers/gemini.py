"""Google Gemini provider with OpenAI ↔ Gemini format translation."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from src.core.registry import get_registry
from src.core.types import ChatRequest, ChatResponse, HealthStatus, ModelInfo, ProviderError
from src.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Gateway provider for Google Gemini (AI Studio)."""

    async def _resolve_provider_model(self, gateway_model_id: str) -> str:
        """Map a gateway model id to Gemini's provider_model_id."""
        registry = await get_registry()
        model = registry.get(gateway_model_id)
        if model is None:
            raise ProviderError(
                f"Model '{gateway_model_id}' not found in registry", "404"
            )
        if model.provider_id != "gemini":
            raise ProviderError(
                f"Model '{gateway_model_id}' is not a Gemini model", "404"
            )
        return model.provider_model_id

    def _build_request_body(self, request: ChatRequest) -> dict[str, Any]:
        """Translate an OpenAI chat request into a Gemini generateContent body."""
        system_instruction: str | None = None
        contents: list[dict[str, Any]] = []

        for message in request.messages:
            if message.role == "system":
                system_instruction = message.content or ""
                continue
            gemini_role = "model" if message.role == "assistant" else "user"
            contents.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": message.content or ""}],
                }
            )

        body: dict[str, Any] = {"contents": contents}
        if system_instruction:
            body["system_instruction"] = {"parts": [{"text": system_instruction}]}

        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
            "topP": request.top_p,
        }
        if request.stop is not None:
            generation_config["stopSequences"] = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )
        body["generationConfig"] = generation_config

        return body

    def _map_http_error(self, exc: httpx.HTTPStatusError) -> ProviderError:
        status = exc.response.status_code
        if status == 429:
            return ProviderError("Gemini rate limited", "429")
        if status == 401:
            return ProviderError("Gemini invalid key", "401")
        if status == 404:
            return ProviderError("Gemini model not found", "404")
        if 500 <= status < 600:
            return ProviderError(f"Gemini server error {status}", "5xx")
        return ProviderError(f"Gemini HTTP error {status}", "5xx")

    def _map_finish_reason(self, reason: str | None) -> str:
        mapping = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "RECITATION": "content_filter",
            "OTHER": "error",
        }
        return mapping.get(reason or "", "stop")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        provider_model_id = await self._resolve_provider_model(request.model)
        body = self._build_request_body(request)
        suffix = ":streamGenerateContent" if request.stream else ":generateContent"
        url = (
            f"{self.config.base_url}/models/{provider_model_id}{suffix}"
            f"?key={self.config.api_key}"
        )

        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError("Gemini request timed out", "timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc

        data = response.json()
        return self._translate_response(data, request.model)

    def _translate_response(self, data: dict[str, Any], gateway_model_id: str) -> ChatResponse:
        candidate = data.get("candidates", [{}])[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in content_parts)
        usage_meta = data.get("usageMetadata", {})

        return ChatResponse(
            id=f"chatcmpl-gemini-{int(time.time())}",
            object="chat.completion",
            created=int(time.time()),
            model=gateway_model_id,
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": self._map_finish_reason(
                        candidate.get("finishReason")
                    ),
                }
            ],
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                "total_tokens": usage_meta.get(
                    "totalTokenCount",
                    usage_meta.get("promptTokenCount", 0)
                    + usage_meta.get("candidatesTokenCount", 0),
                ),
            },
            provider="gemini",
        )

    async def chat_stream(self, request: ChatRequest):
        """Stream Gemini chunks translated to OpenAI SSE format."""
        provider_model_id = await self._resolve_provider_model(request.model)
        body = self._build_request_body(request)
        # alt=sse makes Gemini emit OpenAI-style "data: {...}" SSE frames.
        # Without it the endpoint streams a raw JSON ARRAY, so the "data: "
        # line filter below matched nothing and the generator yielded zero
        # chunks — the stream silently failed over every time.
        url = (
            f"{self.config.base_url}/models/{provider_model_id}:streamGenerateContent"
            f"?alt=sse&key={self.config.api_key}"
        )

        stream_id = f"chatcmpl-gemini-{int(time.time())}"
        first_chunk = True

        try:
            async with self.client.stream("POST", url, json=body) as response:
                # Pre-first-byte errors are RAISED so the fallback engine can
                # fail over to another provider (mirrors openai_compatible).
                if response.status_code >= 400:
                    await response.aread()
                    raise self._map_http_error(
                        httpx.HTTPStatusError(
                            f"Gemini stream error {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return

                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    candidate = data.get("candidates", [{}])[0]
                    content_parts = candidate.get("content", {}).get("parts", [])
                    text = "".join(part.get("text", "") for part in content_parts)

                    delta: dict[str, Any] = {"content": text}
                    if first_chunk:
                        delta["role"] = "assistant"
                    first_chunk = False

                    chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": delta,
                                "finish_reason": self._map_finish_reason(
                                    candidate.get("finishReason")
                                )
                                if candidate.get("finishReason")
                                else None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
        except httpx.TimeoutException as exc:
            if first_chunk:
                raise ProviderError("Gemini stream timed out", "timeout") from exc
            yield f'data: {json.dumps({"error": {"message": "Gemini stream timed out", "type": "timeout"}})}\n\n'
        except httpx.HTTPError as exc:
            if first_chunk:
                raise ProviderError("Gemini stream transport error", "5xx") from exc
            yield f'data: {json.dumps({"error": {"message": str(exc), "type": "5xx"}})}\n\n'

    async def list_models(self) -> list[ModelInfo]:
        registry = await get_registry()
        return registry.get_by_provider("gemini")

    async def check_health(self) -> HealthStatus:
        """Ping Gemini with a tiny request to determine availability."""
        try:
            url = (
                f"{self.config.base_url}/models/gemini-3.5-flash"
                f"?key={self.config.api_key}"
            )
            response = await self.client.get(url)
            if response.status_code == 200:
                return HealthStatus.HEALTHY
            if response.status_code == 429:
                return HealthStatus.RATE_LIMITED
            if response.status_code == 401:
                return HealthStatus.INVALID
            return HealthStatus.ERROR
        except httpx.TimeoutException:
            return HealthStatus.UNREACHABLE
        except httpx.HTTPError:
            return HealthStatus.ERROR
