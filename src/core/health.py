"""Provider health monitoring and status tracking."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

from src.core import key_manager, rate_limiter
from src.core.registry import get_registry_sync
from src.core.router import get_provider
from src.core.types import HealthStatus

# Active probes spend a provider's real rate budget, so keep them rare and
# passive-first: a provider exercised by real traffic within this window is
# trusted and not actively re-probed.
_CHECK_INTERVAL_SECONDS = 300
_REQUEST_WINDOW_SECONDS = 3600

_status: dict[str, dict[str, Any]] = {}
_loop_task: asyncio.Task | None = None
_start_time = time.time()
_request_total = 0
_request_timestamps: deque[float] = deque()
_provider_analytics: dict[str, dict[str, float]] = {}


def _prune_request_window(now: float) -> None:
    """Keep only request timestamps that fall inside the rolling hour window."""
    cutoff = now - _REQUEST_WINDOW_SECONDS
    while _request_timestamps and _request_timestamps[0] < cutoff:
        _request_timestamps.popleft()


def record_request() -> None:
    """Record one gateway request for uptime and rolling-hour counters."""
    global _request_total
    now = time.time()
    _request_total += 1
    _request_timestamps.append(now)
    _prune_request_window(now)


def record_provider_result(provider_id: str, tokens: int, latency_ms: float) -> None:
    """Accumulate per-provider request, token, and latency analytics."""
    metrics = _provider_analytics.setdefault(
        provider_id,
        {"requests": 0.0, "tokens": 0.0, "latency_ms_total": 0.0},
    )
    metrics["requests"] += 1
    metrics["tokens"] += tokens
    metrics["latency_ms_total"] += latency_ms


def get_request_stats() -> dict[str, int]:
    """Return gateway request totals and uptime counters."""
    now = time.time()
    _prune_request_window(now)
    return {
        "uptime_seconds": int(now - _start_time),
        "requests_total": _request_total,
        "requests_last_hour": len(_request_timestamps),
    }


def get_provider_analytics() -> dict[str, dict[str, float | int]]:
    """Return per-provider request counts, token totals, and average latency."""
    analytics: dict[str, dict[str, float | int]] = {}
    for provider_id, metrics in _provider_analytics.items():
        request_count = int(metrics["requests"])
        latency_total = metrics["latency_ms_total"]
        analytics[provider_id] = {
            "requests": request_count,
            "tokens": int(metrics["tokens"]),
            "avg_latency_ms": 0.0 if request_count == 0 else round(latency_total / request_count, 2),
        }
    return analytics


async def _check_provider(provider_id: str) -> None:
    """Probe a single provider and update its status."""
    try:
        provider = await get_provider(provider_id)
        status = await provider.check_health()
    except Exception:
        status = HealthStatus.ERROR

    _status[provider_id] = {
        "status": status.value,
        "last_check": time.time(),
    }

    # Reflect permanent auth failures in the key manager health column.
    if status == HealthStatus.INVALID:
        await key_manager.update_health(provider_id, "invalid")


async def _run_loop() -> None:
    """Background loop that probes every registered provider."""
    while True:
        try:
            registry = get_registry_sync()
            provider_ids = {m.provider_id for m in registry.all_models()}
            now = time.time()
            for provider_id in provider_ids:
                # Passive-first: if real traffic (or a recent probe) already set
                # this provider's status inside the window, trust it and skip the
                # active probe so we don't burn the provider's rate budget.
                info = _status.get(provider_id)
                if info is not None and now - info.get("last_check", 0.0) < _CHECK_INTERVAL_SECONDS:
                    continue
                # Skip providers that are permanently disabled / out of budget.
                if not await rate_limiter.allow(provider_id):
                    _status[provider_id] = {
                        "status": HealthStatus.RATE_LIMITED.value,
                        "last_check": time.time(),
                    }
                    continue
                await _check_provider(provider_id)
        except Exception:
            # Never let the health loop crash the application.
            pass
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


def start() -> None:
    """Start the background health-check loop."""
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_run_loop())


async def stop() -> None:
    """Cancel the background health-check loop."""
    global _loop_task
    if _loop_task is not None and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    _loop_task = None


def get_status(provider_id: str) -> dict[str, Any]:
    """Return the last known status for a provider."""
    return _status.get(provider_id, {"status": HealthStatus.UNKNOWN.value, "last_check": None})


def reset() -> None:
    """Clear all recorded provider statuses. Used for test isolation."""
    _status.clear()


def set_status(provider_id: str, status_value: str) -> None:
    """Record a provider's status from a live request outcome (not just probes).

    Lets a failure during a real request immediately steer routing away from the
    provider, instead of waiting for the next background health probe.
    """
    _status[provider_id] = {"status": status_value, "last_check": time.time()}


def get_all_statuses() -> dict[str, dict[str, Any]]:
    """Return a copy of all provider statuses."""
    return dict(_status)


# Statuses that mean "the last probe found this provider broken" — never route
# traffic to these. HEALTHY and UNKNOWN (not yet probed, e.g. right after
# startup) remain routable so the gateway is usable before the first probe.
_UNROUTABLE_STATUSES = {
    HealthStatus.ERROR.value,
    HealthStatus.UNREACHABLE.value,
    HealthStatus.INVALID.value,
    HealthStatus.RATE_LIMITED.value,
}


def is_routable(provider_id: str) -> bool:
    """Return whether a provider may receive a request based on its last probe."""
    status = get_status(provider_id).get("status")
    return status not in _UNROUTABLE_STATUSES


def get_healthy_providers(model_id: str) -> list[str]:
    """Return provider ids that offer the model and are currently healthy."""
    registry = get_registry_sync()
    model = registry.get(model_id)
    if model is None:
        return []
    provider_ids = registry.get_providers_for_model(model_id)
    return [
        pid
        for pid in provider_ids
        if get_status(pid).get("status") == HealthStatus.HEALTHY.value
    ]
