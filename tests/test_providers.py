"""Tests for provider translation and envelope correctness."""

from __future__ import annotations

import pytest

from src.core.types import ChatRequest, Message
from src.providers.base import ProviderConfig, build_openai_envelope
from src.providers.gemini import GeminiProvider


@pytest.mark.asyncio
async def test_openai_envelope_has_required_fields():
    response = build_openai_envelope(
        "codestral",
        "hello",
        "mistral",
        {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    )
    data = response.model_dump(mode="json")
    assert data["object"] == "chat.completion"
    assert data["model"] == "codestral"
    assert data["provider"] == "mistral"
    assert data["choices"][0]["message"]["content"] == "hello"
    assert data["usage"]["total_tokens"] == 3


@pytest.mark.asyncio
async def test_gemini_request_translation():
    provider = GeminiProvider(
        ProviderConfig(name="gemini", base_url="http://x", api_key="k", models=[], rate_limits={})
    )
    request = ChatRequest(
        model="gemini-3.5-flash",
        messages=[
            Message(role="system", content="be helpful"),
            Message(role="user", content="hi"),
        ],
    )
    body = provider._build_request_body(request)
    assert "system_instruction" in body
    assert body["contents"][0]["role"] == "user"
    assert body["contents"][0]["parts"][0]["text"] == "hi"
    assert body["generationConfig"]["maxOutputTokens"] == request.max_tokens


@pytest.mark.asyncio
async def test_gemini_response_translation():
    provider = GeminiProvider(
        ProviderConfig(name="gemini", base_url="http://x", api_key="k", models=[], rate_limits={})
    )
    raw = {
        "candidates": [
            {
                "content": {"parts": [{"text": "hello"}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 2,
            "candidatesTokenCount": 1,
            "totalTokenCount": 3,
        },
    }
    response = provider._translate_response(raw, "gemini-3.5-flash")
    assert response.model == "gemini-3.5-flash"
    assert response.choices[0].message["content"] == "hello"
    assert response.choices[0].finish_reason == "stop"
    assert response.usage.total_tokens == 3
    assert response.provider == "gemini"
