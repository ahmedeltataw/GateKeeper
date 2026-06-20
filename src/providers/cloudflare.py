"""Cloudflare Workers AI provider (non-OpenAI, neurons-based quota)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from src.core.registry import get_registry
from src.core.types import ChatRequest, ChatResponse, HealthStatus, ModelInfo, ProviderError
from src.providers.base import BaseProvider


class CloudflareProvider(BaseProvider):
    """Gateway provider for Cloudflare Workers AI.

    Requires ``CLOUDFLARE_ACCOUNT_ID`` in the environment and a Cloudflare API
    token as the api_key.  Quota is measured in neurons, managed by the rate
    limiter.
    """

    def __init__(self, config):
        super().__init__(config)
        self.account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")

    async def _resolve_provider_model(self, gateway_model_id: str) -> str:
        registry = await get_registry()
        model = registry.get(gateway_model_id)
        if model is None:
            raise ProviderError(
                f"Model '{gateway_model_id}' not found in registry", "404"
            )
        if model.provider_id != "cloudflare":
            raise ProviderError(
                f"Model '{gateway_model_id}' is not a Cloudflare model", "404"
            )
        return model.provider_model_id

    def _build_request_body(self, request: ChatRequest) -> dict[str, Any]:
        return {
            "messages": [
                {"role": m.role, "content": m.content or ""}
                for m in request.messages
            ],
            "max_tokens": request.max_tokens,
        }

    def _url(self, provider_model_id: str) -> str:
        if not self.account_id:
            raise ProviderError("CLOUDFLARE_ACCOUNT_ID is not set", "401")
        base = self.config.base_url.replace("{account_id}", self.account_id)
        return f"{base}/{provider_model_id}"

    def _map_http_error(self, exc: httpx.HTTPStatusError) -> ProviderError:
        status = exc.response.status_code
        if status == 429:
            return ProviderError("Cloudflare rate limited (neurons)", "429")
        if status == 401:
            return ProviderError("Cloudflare invalid token", "401")
        if status == 404:
            return ProviderError("Cloudflare model not found", "404")
        if 500 <= status < 600:
            return ProviderError(f"Cloudflare server error {status}", "5xx")
        return ProviderError(f"Cloudflare HTTP error {status}", "5xx")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        provider_model_id = await self._resolve_provider_model(request.model)
        body = self._build_request_body(request)
        url = self._url(provider_model_id)
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        try:
            response = await self.client.post(url, json=body, headers=headers)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError("Cloudflare request timed out", "timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc

        data = response.json()
        return self._translate_response(data, request.model)

    def _translate_response(self, data: dict[str, Any], gateway_model_id: str) -> ChatResponse:
        result = data.get("result", {})
        raw = result.get("response", "")
        if isinstance(raw, list):
            # Some CF models return a list of token/segment dicts.
            response_text = "".join(
                part.get("response", "") if isinstance(part, dict) else str(part)
                for part in raw
            )
        else:
            response_text = raw or ""

        return ChatResponse(
            id=f"chatcmpl-cf-{int(time.time())}",
            object="chat.completion",
            created=int(time.time()),
            model=gateway_model_id,
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop",
                }
            ],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            provider="cloudflare",
        )

    async def chat_stream(self, request: ChatRequest):
        """Cloudflare streaming is not implemented; fall back to non-streaming."""
        response = await self.chat(request)
        yield f"data: {json.dumps(response.model_dump(mode='json'))}\n\n"
        yield "data: [DONE]\n\n"

    async def list_models(self) -> list[ModelInfo]:
        registry = await get_registry()
        return registry.get_by_provider("cloudflare")

    async def check_health(self) -> HealthStatus:
        try:
            registry = await get_registry()
            models = registry.get_by_provider("cloudflare")
            if not models:
                return HealthStatus.UNKNOWN
            url = self._url(models[0].provider_model_id)
            response = await self.client.get(url, headers={"Authorization": f"Bearer {self.config.api_key}"})
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
