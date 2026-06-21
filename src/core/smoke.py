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
    """
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
    content = (response.choices[0].message.get("content") or "") if response.choices else ""
    if not content.strip():
        return {"ok": False, "code": "empty", "detail": "empty completion", "latency_ms": latency_ms}
    return {"ok": True, "latency_ms": latency_ms}
