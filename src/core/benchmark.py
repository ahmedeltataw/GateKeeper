"""Opt-in background benchmark for speed and a basic quality signal.

Runs entirely off the request path: a low-priority background task that, on a
long interval, sends one tiny fixed prompt to each usable model and records
latency plus whether the answer contained an expected substring. It is disabled
by default (``benchmark.enabled: false``) so it can never affect API
responsiveness, and it respects the rate limiter and circuit/health gates so it
never spends a provider's budget at the expense of real traffic.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from src.core import circuit, health, rate_limiter
from src.core.config_loader import get_config
from src.core.registry import get_registry_sync
from src.core.router import get_provider
from src.core.types import ChatRequest, Message

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_loop_task: asyncio.Task | None = None
_results: dict[str, dict[str, Any]] = {}


def get_results() -> dict[str, dict[str, Any]]:
    """Return the latest per-model benchmark results."""
    return dict(_results)


async def _benchmark_model(model: Any, prompt: str, expected: str) -> dict[str, Any] | None:
    """Send one tiny prompt and record latency + a basic quality flag.

    Returns ``None`` when the model is skipped (gated or out of budget) so the
    benchmark never steals budget from real requests.
    """
    if circuit.is_open(model.id) or not health.is_routable(model.provider_id):
        return None
    if not await rate_limiter.allow(model.provider_id, model.id):
        return None

    request = ChatRequest(
        model=model.id,
        messages=[Message(role="user", content=prompt)],
        max_tokens=16,
    )
    provider = await get_provider(model.provider_id)
    start = time.time()
    try:
        response = await provider.chat(request)
    except Exception as exc:  # benchmark must never raise into the loop
        return {"ok": False, "error": repr(exc), "checked_at": int(start)}

    latency_ms = round((time.time() - start) * 1000, 1)
    content = (response.choices[0].message.get("content") or "") if response.choices else ""
    return {
        "ok": True,
        "latency_ms": latency_ms,
        "quality_pass": expected.lower() in content.lower(),
        "checked_at": int(start),
    }


async def run_once() -> dict[str, dict[str, Any]]:
    """Benchmark every usable model once and persist the results."""
    cfg = get_config().benchmark
    registry = get_registry_sync()
    for model in registry.get_active():
        result = await _benchmark_model(model, cfg.prompt, cfg.expected_substring)
        if result is not None:
            _results[model.id] = result
    _persist(cfg.output_file)
    return dict(_results)


def _persist(output_file: str) -> None:
    """Write benchmark results to disk (best-effort)."""
    try:
        path = Path(output_file)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_results, indent=2), encoding="utf-8")
    except Exception:
        pass


async def _run_loop() -> None:
    interval = max(60, get_config().benchmark.interval_seconds)
    while True:
        try:
            await run_once()
        except Exception:
            pass
        await asyncio.sleep(interval)


def start() -> None:
    """Start the background benchmark loop if enabled in config."""
    global _loop_task
    if not get_config().benchmark.enabled:
        return
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_run_loop())


async def stop() -> None:
    """Cancel the background benchmark loop."""
    global _loop_task
    if _loop_task is not None and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    _loop_task = None
