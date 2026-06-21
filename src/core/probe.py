"""Boot-time catalog probe with auto-quarantine.

At startup (opt-in via ``probe.enabled``), smoke-test every active model and
feed the result into the existing circuit breaker. A model that fails is *not*
deleted — the breaker opens and, on repeated boots, blacklists it, so a broken
``:free`` rotation or a key without access disappears from ``/v1/models``
instead of failing a user's 3 AM request.

Design choices that keep this safe and cheap:

* **Reuses the breaker.** ``smoke`` returns a ``code`` and we call
  ``circuit.record_failure`` / ``record_success`` — the same state machine that
  live traffic uses. No parallel quarantine store to drift out of sync.
* **Respects budget.** Bounded concurrency and an option to skip providers the
  health loop already marked ``rate_limited``.
* **Never blocks startup fatally.** Exceptions are swallowed; a probe failure
  must never stop the gateway from serving.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core import circuit, health
from src.core.config_loader import get_config
from src.core.registry import get_registry
from src.core.smoke import smoke_test_model
from src.core.types import HealthStatus

# Last probe run summary, surfaced by /health as ``catalog_probe``.
_summary: dict[str, Any] = {}


def get_summary() -> dict[str, Any]:
    """Return the most recent probe summary (empty until the first run)."""
    return dict(_summary)


def reset() -> None:
    """Clear the cached summary (test isolation)."""
    _summary.clear()


async def _probe_one(model: Any, sem: asyncio.Semaphore, cfg: Any) -> bool:
    async with sem:
        result = await smoke_test_model(
            model,
            prompt=cfg.prompt,
            max_tokens=cfg.max_tokens,
            timeout=cfg.timeout_seconds,
        )
    if result["ok"]:
        await circuit.record_success(model.id)
        return True
    await circuit.record_failure(model.id, result.get("code", "5xx"), result.get("detail", ""))
    return False


async def probe_all_models(concurrency: int | None = None) -> dict[str, Any]:
    """Smoke-test the active catalog and quarantine failures via the breaker.

    Returns the run summary ``{probed, healthy, failed, skipped, blacklisted}``
    and stores it for the ``/health`` endpoint.
    """
    cfg = get_config().probe
    registry = await get_registry()
    sem = asyncio.Semaphore(max(1, concurrency or cfg.concurrency))

    candidates: list[Any] = []
    skipped = 0
    for model in registry.get_active():
        if cfg.skip_rate_limited:
            status = health.get_status(model.provider_id).get("status")
            if status == HealthStatus.RATE_LIMITED.value:
                skipped += 1
                continue
        candidates.append(model)

    results = await asyncio.gather(*(_probe_one(m, sem, cfg) for m in candidates))
    healthy = sum(1 for ok in results if ok)
    failed = len(results) - healthy
    blacklisted = sum(
        1 for b in circuit.snapshot().values() if b.get("state") == circuit.STATE_BLACKLISTED
    )

    _summary.clear()
    _summary.update(
        {
            "probed": len(candidates),
            "healthy": healthy,
            "failed": failed,
            "skipped": skipped,
            "blacklisted": blacklisted,
            "ran_at": int(time.time()),
        }
    )
    return dict(_summary)
