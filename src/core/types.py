"""Shared data types for the gateway.

These types are used by the API layer, providers, registry, and core modules so
that every component speaks the same language.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: dict[str, Any]


class ChatRequest(BaseModel):
    model: str
    messages: list[Message] = Field(..., min_length=1)
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: str | list[str] | None = None
    task_type: Literal[
        "coding", "search", "reasoning", "creative", "data", "vision", "default"
    ] = "default"

    @field_validator("temperature")
    @classmethod
    def _validate_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return value

    @field_validator("max_tokens")
    @classmethod
    def _validate_max_tokens(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_tokens must be >= 1")
        return value

    @field_validator("frequency_penalty", "presence_penalty")
    @classmethod
    def _validate_penalty(cls, value: float) -> float:
        if not -2.0 <= value <= 2.0:
            raise ValueError("penalty must be between -2.0 and 2.0")
        return value


class ChatChoice(BaseModel):
    index: int = 0
    message: dict[str, Any]
    finish_reason: Literal[
        "stop", "length", "tool_calls", "content_filter", "error"
    ] = "stop"


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatChoice]
    usage: TokenUsage
    provider: str = ""
    fallback_used: bool = False
    original_model: str = ""
    fallback_chain: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    id: str
    display_name: str
    provider_id: str
    provider_model_id: str
    strength: Literal["S", "A", "B", "C"]
    strength_order: int = 0
    use_cases: list[str]
    category: str = "general"
    tier: Literal["auto", "dedicated"] = "auto"
    context_window: int
    max_output_tokens: int
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    pricing: dict[str, float] | None = None
    rate_limits: dict[str, Any]
    enabled: bool = True
    status: Literal["active", "deprecated", "removed", "pending_verification"] = "active"
    fallback_models: list[str] = Field(default_factory=list)
    notes: str | None = None
    source_url: str | None = None
    added_at: str
    removed_at: str | None = None
    last_verified: str
    verification_source: str | None = None

    @field_validator("strength_order", mode="before")
    @classmethod
    def _derive_strength_order(cls, value: Any, info: Any) -> int:
        if value is not None and value != 0:
            return int(value)
        strength = info.data.get("strength")
        return {"S": 0, "A": 1, "B": 2, "C": 3}.get(strength, 99)

    @field_validator("context_window")
    @classmethod
    def _validate_context_window(cls, value: int) -> int:
        if value < 4096:
            raise ValueError("context_window must be >= 4096")
        return value

    @field_validator("max_output_tokens")
    @classmethod
    def _validate_max_output_tokens(cls, value: int) -> int:
        if value < 1024:
            raise ValueError("max_output_tokens must be >= 1024")
        return value


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    INVALID = "invalid"
    ERROR = "error"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"


class ProviderError(Exception):
    """Raised when a provider call fails in a way that may trigger fallback."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"


class GatewayError(Exception):
    """Base for gateway-level errors mapped to HTTP responses."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class ModelNotFoundError(GatewayError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class NoHealthyProviderError(GatewayError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class AllRateLimitedError(GatewayError):
    def __init__(self, message: str):
        super().__init__(message, status_code=429)
