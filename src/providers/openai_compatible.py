"""Generic OpenAI-compatible provider used by most gateway providers."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from src.core.registry import get_registry
from src.core.types import ChatRequest, ChatResponse, HealthStatus, ModelInfo, ProviderError
from src.providers.base import BaseProvider


class OpenAICompatibleProvider(BaseProvider):
    """Provider for backends that expose an OpenAI-compatible chat API."""

    def __init__(
        self,
        config,
        *,
        provider_id: str,
        health_model: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ):
        super().__init__(config)
        self.provider_id = provider_id
        self.health_model = health_model
        self.extra_headers = extra_headers or {}

    def _headers(self) -> dict[str, str]:
        """Auth header plus any provider-specific extra headers."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            **self.extra_headers,
        }

    async def _resolve_provider_model(self, gateway_model_id: str) -> str:
        registry = await get_registry()
        model = registry.get(gateway_model_id)
        if model is None:
            raise ProviderError(
                f"Model '{gateway_model_id}' not found in registry", "404"
            )
        if model.provider_id != self.provider_id:
            raise ProviderError(
                f"Model '{gateway_model_id}' is not a {self.provider_id} model", "404"
            )
        return model.provider_model_id

    def _build_request_body(self, request: ChatRequest, provider_model_id: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": provider_model_id,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream,
        }
        if request.stop is not None:
            body["stop"] = request.stop
        return body

    def _map_http_error(self, exc: httpx.HTTPStatusError) -> ProviderError:
        status = exc.response.status_code
        name = self.provider_id
        if status == 429:
            return ProviderError(f"{name} rate limited", "429")
        if status == 413:
            return ProviderError(f"{name} payload too large", "413")
        if status == 401:
            return ProviderError(f"{name} invalid key", "401")
        if status == 404:
            return ProviderError(f"{name} model not found", "404")
        if 500 <= status < 600:
            return ProviderError(f"{name} server error {status}", "5xx")
        return ProviderError(f"{name} HTTP error {status}", "5xx")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        if not self.config.api_key:
            raise ProviderError(f"{self.provider_id} has no API key configured", "401")
        provider_model_id = await self._resolve_provider_model(request.model)
        body = self._build_request_body(request, provider_model_id)
        url = f"{self.config.base_url}/chat/completions"
        headers = self._headers()

        try:
            response = await self.client.post(url, json=body, headers=headers)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError(f"{self.provider_id} request timed out", "timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc

        data = response.json()
        return self._translate_response(data, request.model)

    def _translate_response(self, data: dict[str, Any], gateway_model_id: str) -> ChatResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        content = message.get("content")
        if not content and not message.get("tool_calls"):
            # Reasoning models (e.g. gpt-oss) may return their answer in a
            # separate reasoning field with content empty. Surface it.
            content = message.get("reasoning") or message.get("reasoning_content") or content

        return ChatResponse(
            id=data.get("id", f"chatcmpl-{int(time.time())}"),
            object="chat.completion",
            created=data.get("created", int(time.time())),
            model=gateway_model_id,
            choices=[
                {
                    "index": choice.get("index", 0),
                    "message": {
                        "role": message.get("role", "assistant"),
                        "content": content,
                    },
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            ],
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get(
                    "total_tokens",
                    usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
                ),
            },
            provider=self.provider_id,
        )

    async def chat_stream(self, request: ChatRequest):
        if not self.config.api_key:
            raise ProviderError(f"{self.provider_id} has no API key configured", "401")
        provider_model_id = await self._resolve_provider_model(request.model)
        body = self._build_request_body(request, provider_model_id)
        url = f"{self.config.base_url}/chat/completions"
        headers = self._headers()

        stream_id = f"chatcmpl-{int(time.time())}"
        first_chunk = True

        try:
            async with self.client.stream(
                "POST", url, json=body, headers=headers
            ) as response:
                # Errors before any byte is yielded are RAISED (not yielded) so
                # the streaming fallback can remediate / fail over to another
                # provider. Once content starts flowing we can't unsend it, so
                # mid-stream failures degrade to an inline error chunk below.
                if response.status_code >= 400:
                    await response.aread()
                    raise self._map_http_error(
                        httpx.HTTPStatusError(
                            f"{self.provider_id} stream error {response.status_code}",
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

                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        if first_chunk:
                            delta.setdefault("role", "assistant")
                        first_chunk = False
                        # Reasoning models (gpt-oss, qwq, deepseek-r1) put their
                        # tokens in `reasoning`/`reasoning_content` with `content`
                        # empty. Clients that render only `delta.content` (e.g.
                        # OpenCode) would show a silent stream. Surface it as
                        # content — mirrors the non-stream _translate_response.
                        if not delta.get("content"):
                            reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                            if reasoning:
                                delta["content"] = reasoning

                    chunk = {
                        "id": data.get("id", stream_id),
                        "object": "chat.completion.chunk",
                        "created": data.get("created", int(time.time())),
                        "model": request.model,
                        "choices": choices,
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
        except httpx.TimeoutException as exc:
            if first_chunk:
                raise ProviderError(f"{self.provider_id} stream timed out", "timeout") from exc
            yield f'data: {json.dumps({"error": {"message": f"{self.provider_id} stream timed out", "type": "timeout"}})}\n\n'
        except httpx.HTTPError as exc:
            if first_chunk:
                raise ProviderError(f"{self.provider_id} stream transport error", "5xx") from exc
            yield f'data: {json.dumps({"error": {"message": str(exc), "type": "5xx"}})}\n\n'

    async def list_models(self) -> list[ModelInfo]:
        registry = await get_registry()
        return registry.get_by_provider(self.provider_id)

    async def check_health(self) -> HealthStatus:
        try:
            model = self.health_model
            if model is None:
                registry = await get_registry()
                models = registry.get_by_provider(self.provider_id)
                if not models:
                    return HealthStatus.UNKNOWN
                model = models[0].provider_model_id

            url = f"{self.config.base_url}/chat/completions"
            body = {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            response = await self.client.post(url, json=body, headers=self._headers())
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
