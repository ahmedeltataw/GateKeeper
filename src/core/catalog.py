"""Auto-generated ``models.json`` catalog (OpenCode-style user reference).

Snapshots the live, routable state of the gateway — registry metadata joined
with each model's circuit-breaker and provider-health status — into a single
JSON file. The source ``models_registry.json`` is never mutated; this is a
derived, read-only artifact, written atomically (temp file + rename) so a reader
never sees a half-written file.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from src.core import circuit, health
from src.core.config_loader import get_config
from src.core.registry import get_registry_sync

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_loop_task: asyncio.Task | None = None


def _model_entry(model: Any, breaker: dict[str, Any] | None) -> dict[str, Any]:
    """Build one catalog entry for a model, including its live usability."""
    breaker_state = breaker["state"] if breaker else "closed"
    usable = (
        model.enabled
        and model.status == "active"
        and breaker_state == "closed"
        and health.is_routable(model.provider_id)
    )
    entry: dict[str, Any] = {
        "id": model.id,
        "name": model.display_name,
        "provider": model.provider_id,
        "strength": model.strength,
        "use_cases": model.use_cases,
        "context_window": model.context_window,
        "max_output_tokens": model.max_output_tokens,
        "usable": usable,
        "circuit_state": breaker_state,
        "provider_health": health.get_status(model.provider_id).get("status"),
    }
    if breaker and breaker_state == "blacklisted":
        entry["blacklist_reason"] = breaker.get("blacklist_reason", "")
    return entry


def build_catalog() -> dict[str, Any]:
    """Return the catalog document from current registry + live state.

    ``models`` is an OBJECT keyed by model id (not an array) to match the shape
    OpenCode-style consumers expect; an array there triggers their
    "Failed to load sessions" parse error.
    """
    registry = get_registry_sync()
    breakers = circuit.snapshot()
    models = {
        model.id: _model_entry(model, breakers.get(model.id))
        for model in registry.all_models()
    }
    usable_count = sum(1 for entry in models.values() if entry["usable"])
    return {
        "generated_at": int(time.time()),
        "total": len(models),
        "usable": usable_count,
        "models": models,
    }


def _output_path() -> Path:
    configured = Path(get_config().catalog.output_file)
    return configured if configured.is_absolute() else _PROJECT_ROOT / configured


def write_catalog() -> Path:
    """Write ``models.json`` atomically and return its path."""
    path = _output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build_catalog(), indent=2, ensure_ascii=False)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, path)  # atomic on POSIX and Windows
    return path


async def _run_loop() -> None:
    """Periodically refresh the catalog to reflect circuit/health changes."""
    interval = max(10, get_config().catalog.refresh_seconds)
    while True:
        try:
            write_catalog()
        except Exception:
            # A catalog write must never crash the gateway.
            pass
        await asyncio.sleep(interval)


def start() -> None:
    """Write an initial catalog and start the periodic refresh loop."""
    global _loop_task
    if not get_config().catalog.enabled:
        return
    try:
        write_catalog()
    except Exception:
        pass
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_run_loop())


async def stop() -> None:
    """Cancel the periodic refresh loop."""
    global _loop_task
    if _loop_task is not None and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    _loop_task = None
