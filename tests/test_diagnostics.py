"""Tests for the Smart Diagnostic remediation engine."""

from __future__ import annotations

import pytest

from src.core import diagnostics
from src.core.types import ChatRequest, Message, ModelInfo


def _model(max_output_tokens: int = 4096) -> ModelInfo:
    return ModelInfo(
        id="m",
        display_name="M",
        provider_id="p",
        provider_model_id="p/m",
        strength="A",
        use_cases=["coding"],
        context_window=128000,
        max_output_tokens=max_output_tokens,
        rate_limits={"rpm": 10},
        added_at="2026-06-19",
        last_verified="2026-06-19",
    )


def test_preflight_clamps_max_tokens_to_model_limit():
    """A request asking for more output than the model allows is clamped down."""
    request = ChatRequest(model="m", messages=[Message(role="user", content="hi")], max_tokens=8192)
    clamped = diagnostics.preflight_clamp(request, _model(max_output_tokens=4096))
    assert clamped.max_tokens == 4096


def test_preflight_is_noop_when_within_limit():
    """A request already within the model's limit is returned unchanged."""
    request = ChatRequest(model="m", messages=[Message(role="user", content="hi")], max_tokens=1000)
    clamped = diagnostics.preflight_clamp(request, _model(max_output_tokens=4096))
    assert clamped is request


def _request(num_messages: int = 6, max_tokens: int = 2048) -> ChatRequest:
    messages = [Message(role="system", content="be brief")]
    for index in range(num_messages - 1):
        messages.append(Message(role="user", content=f"turn {index}"))
    return ChatRequest(model="auto", messages=messages, max_tokens=max_tokens)


def test_413_shrinks_payload_and_retries():
    """A 413 produces a smaller request: halved max_tokens and fewer messages."""
    request = _request(num_messages=6, max_tokens=2048)
    plan = diagnostics.diagnose("413", request, attempt=0)

    assert plan.action == "retry_modified"
    assert plan.request is not None
    assert plan.request.max_tokens == 1024
    assert len(plan.request.messages) < len(request.messages)
    assert "413" in plan.explanation


def test_413_keeps_leading_system_message():
    """Shrinking must preserve a leading system message."""
    request = _request(num_messages=6, max_tokens=2048)
    plan = diagnostics.diagnose("413", request, attempt=0)

    assert plan.request is not None
    assert plan.request.messages[0].role == "system"


def test_429_is_not_retried_on_same_provider():
    """429 must fail over immediately, not back off on the same provider."""
    plan = diagnostics.diagnose("429", _request(), attempt=0)
    assert plan.action == "none"
    assert plan.will_retry is False


@pytest.mark.parametrize("code", ["5xx", "timeout"])
def test_transient_errors_back_off_then_retry(code):
    """Transient server errors retry after a bounded exponential backoff."""
    plan = diagnostics.diagnose(code, _request(), attempt=1, max_backoff_seconds=8.0)
    assert plan.action == "retry_after"
    assert 0 < plan.delay_seconds <= 8.0


@pytest.mark.parametrize("code", ["401", "404"])
def test_unrecoverable_errors_are_not_retried(code):
    """Bad key / removed model are not programmatically recoverable here."""
    plan = diagnostics.diagnose(code, _request(), attempt=0)
    assert plan.action == "none"
