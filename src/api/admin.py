"""HTTP/JSON admin endpoints for the standalone dashboard.

This router exposes read-mostly gateway state under ``/admin`` for a separate
Streamlit process. Every endpoint requires ``Authorization: Bearer
<ADMIN_TOKEN>``; the middleware returns ``403`` when the token is not
configured and ``401`` when the client token is missing or wrong.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from src.core import cache, circuit, health, key_manager, probe, tenant
from src.core.fallback import get_fallback_count
from src.core.registry import get_registry

router = APIRouter(prefix="/admin", tags=["admin"])


def _provider_status_rows(statuses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert provider status mappings into sorted API rows."""
    return [
        {
            "id": provider_id,
            "status": details.get("status", "unknown"),
            "last_checked": details.get("last_check"),
        }
        for provider_id, details in sorted(statuses.items())
    ]


def _stats_payload() -> dict[str, int]:
    """Build the admin stats payload from runtime counters."""
    return {
        **health.get_request_stats(),
        "cache_hits": cache.get_hits(),
        "fallback_count": get_fallback_count(),
    }


async def _parse_key_write_request(request: Request) -> tuple[str, str]:
    """Validate the key write payload without echoing sensitive input values."""
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    provider = payload.get("provider")
    api_key = payload.get("api_key")
    if not isinstance(provider, str) or not provider.strip():
        raise HTTPException(status_code=400, detail="provider is required")
    if not isinstance(api_key, str) or not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    return provider.strip(), api_key


@router.get("/stats")
async def admin_stats() -> dict[str, int]:
    """Return gateway request, cache, fallback, and uptime counters."""
    return _stats_payload()


@router.get("/providers")
async def admin_providers() -> list[dict[str, Any]]:
    """Return provider statuses or an empty list when none were checked yet."""
    return _provider_status_rows(health.get_all_statuses())


@router.get("/keys")
async def admin_keys() -> list[dict[str, str]]:
    """Return masked provider keys and health metadata without plaintext values."""
    return await key_manager.list_key_summaries()


@router.post("/keys", status_code=status.HTTP_201_CREATED)
async def admin_set_key(request: Request) -> dict[str, str]:
    """Store an encrypted provider key or raise 400 for an invalid JSON payload."""
    provider, api_key = await _parse_key_write_request(request)
    await key_manager.set_key(provider, api_key)
    metadata = await key_manager.get_key_metadata(provider)
    return {
        "provider": provider,
        "masked": "\u25cf\u25cf\u25cf\u25cf\u25cf",
        "health_status": "unknown" if metadata is None else str(metadata.get("health_status", "unknown")),
    }


@router.delete("/keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_key(provider: str) -> Response:
    """Delete one stored provider key and return 204 even if it did not exist."""
    await key_manager.delete_key(provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/models")
async def admin_models() -> list[dict[str, Any]]:
    """Return every registered model serialized from the in-memory registry."""
    registry = await get_registry()
    return [model.model_dump(mode="json") for model in registry.all_models()]


@router.post("/models/{model_id}/enable")
async def admin_enable_model(model_id: str) -> dict[str, Any]:
    """Re-enable a model at runtime (no restart). Also resets its breaker."""
    registry = await get_registry()
    if not registry.set_enabled(model_id, True):
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    await circuit.reset(model_id)  # clear any open/blacklisted state so it routes
    return {"id": model_id, "enabled": True, "circuit": "reset"}


@router.post("/models/{model_id}/disable")
async def admin_disable_model(model_id: str) -> dict[str, Any]:
    """Disable a model at runtime (no restart). Drops it from routing + /v1/models."""
    registry = await get_registry()
    if not registry.set_enabled(model_id, False):
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    return {"id": model_id, "enabled": False}


@router.post("/models/{model_id}/retry")
async def admin_retry_model(model_id: str) -> dict[str, Any]:
    """Clear a model's circuit breaker (un-quarantine a blacklisted model)."""
    registry = await get_registry()
    if registry.get(model_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    await circuit.reset(model_id)
    return {"id": model_id, "circuit": "reset"}


@router.get("/quarantine")
async def admin_quarantine() -> dict[str, Any]:
    """Return quarantined models (open/blacklisted breakers) + last probe run."""
    rows = [
        {"model_id": mid, **state}
        for mid, state in circuit.snapshot().items()
        if state.get("state") in (circuit.STATE_OPEN, circuit.STATE_BLACKLISTED)
    ]
    return {"quarantined": rows, "last_probe": probe.get_summary()}


@router.get("/analytics")
async def admin_analytics() -> dict[str, dict[str, float | int]]:
    """Return per-provider request counts, token totals, and average latency."""
    return health.get_provider_analytics()


@router.get("/usage")
async def admin_usage() -> list[dict[str, Any]]:
    """Return per-tenant usage-vs-quota for the current period (all clients)."""
    from src.api.routes import build_usage_view  # local import avoids a cycle

    principals = await tenant.list_principals()
    return [await build_usage_view(principal) for principal in principals]
