"""Per-model smoke test — a tiny real completion to prove a model works.

This is the model-level analogue of the provider reachability check in
``health.py``. ``health`` answers "is the provider's endpoint up?"; ``smoke``
answers "does *this specific model* return a non-empty completion for my key?".

A smoke test is the unit the boot probe (``probe.py``) runs across the whole
catalog. It is deliberately the same shape as ``benchmark._benchmark_model`` but
narrower: one tiny prompt, a hard timeout, and a structured pass/fail result the
circuit breaker can consume. It never raises — the loop must keep going.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.router import get_provider
from src.core.types import ChatRequest, Message, ProviderError


def _as_text(content: Any) -> str:
    """Flatten a completion's ``content`` to text.

    Most providers return a plain string, but some (multimodal / Anthropic-style)
    return a list of content parts like ``[{"type": "text", "text": "OK"}]``.
    Normalise both so the smoke check never crashes on a non-string payload.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text") or part.get("content") or "")
        return "".join(parts)
    return str(content)


# When a model answers with an empty completion at the tiny default budget, the
# cause is usually that 4 tokens isn't enough room for any visible text (a
# reasoning model can burn the whole budget before emitting a word). Retry once
# with a roomier budget to coax a real text response before calling it dead.
_EMPTY_RETRY_MAX_TOKENS = 64

# Cloudflare's AI edges sit behind a CDN whose first hit can cold-start or get
# dropped, surfacing as a timeout. One cheap retry recovers most of those.
_RETRYABLE_PROVIDERS = {"cloudflare"}
_MAX_RETRIES = 2


async def _one_completion(
    model: Any, prompt: str, max_tokens: int, timeout: float
) -> dict[str, Any]:
    """Run a single completion attempt and classify the outcome. Never raises."""
    request = ChatRequest(
        model=model.id,
        messages=[Message(role="user", content=prompt)],
        max_tokens=max_tokens,
    )
    start = time.time()
    try:
        provider = await get_provider(model.provider_id)
        response = await asyncio.wait_for(provider.chat(request), timeout=timeout)
    except asyncio.TimeoutError:
        return {"ok": False, "code": "timeout", "detail": f"no response in {timeout}s"}
    except ProviderError as exc:
        return {"ok": False, "code": exc.code, "detail": str(exc)}
    except Exception as exc:  # never let a probe crash the loop
        return {"ok": False, "code": "5xx", "detail": repr(exc)}

    latency_ms = round((time.time() - start) * 1000, 1)
    raw = response.choices[0].message.get("content") if response.choices else ""
    content = _as_text(raw)
    if not content.strip():
        return {"ok": False, "code": "empty", "detail": "empty completion", "latency_ms": latency_ms}
    return {"ok": True, "latency_ms": latency_ms}


async def smoke_test_model(
    model: Any,
    *,
    prompt: str = "Reply with the single word: OK",
    max_tokens: int = 4,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Send one tiny completion to ``model`` and report a structured result.

    Returns a dict with ``ok`` plus, on failure, an error ``code``/``detail``
    that maps onto the circuit breaker's vocabulary (``401``/``404``/``429``/
    ``timeout``/``5xx``). Never raises.

    The probe is patient about *transient* failures: an ``empty`` completion is
    retried once with a larger token budget, and a Cloudflare ``timeout`` is
    retried once for a cold/dropped edge. Hard errors (``401``/``404``/``429``)
    are returned immediately — retrying them only wastes rate budget.
    """
    is_retryable_provider = getattr(model, "provider_id", "") in _RETRYABLE_PROVIDERS
    current_max_tokens = max_tokens

    result = await _one_completion(model, prompt, current_max_tokens, timeout)
    retries = 0
    while not result["ok"] and retries < _MAX_RETRIES:
        code = result.get("code")
        if code == "empty" and current_max_tokens < _EMPTY_RETRY_MAX_TOKENS:
            current_max_tokens = _EMPTY_RETRY_MAX_TOKENS  # give it room to speak
        elif code == "timeout" and is_retryable_provider:
            pass  # cold CDN edge — just hit it again
        else:
            break  # not a transient condition we know how to recover
        retries += 1
        result = await _one_completion(model, prompt, current_max_tokens, timeout)

    return result
