"""API routes for GateKeeper."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from src.core.fallback import get_fallback_count, stream_with_fallback, try_with_fallback
from src.core.registry import get_registry
from src.core.sticky import derive_session_id, get_sticky_model
from src.core.config_loader import get_config
from src.core.tenant import OWNER, Principal
from src.core.types import ChatRequest
from src.api import snippets
from src.core import cache, health, metrics, probe, usage

router = APIRouter()


def _principal(http_request: Request) -> Principal:
    """Return the caller's Principal, defaulting to OWNER (sees everything).

    OWNER is the safe default for auth-disabled / non-multi-tenant setups, so
    routes never crash on a missing ``request.state.principal``.
    """
    return getattr(http_request.state, "principal", OWNER)

def error_response(
    message: str, error_type: str, code: int, param: str | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
                "param": param,
                "doc_url": "http://localhost:8000/v1/models",
            }
        },
    )


@router.get("/health")
async def health_endpoint() -> dict[str, Any]:
    """Public health endpoint."""
    provider_statuses = health.get_all_statuses()
    request_stats = health.get_request_stats()
    providers = {
        pid: info["status"]
        for pid, info in provider_statuses.items()
    }
    return {
        "status": "healthy",
        "version": "1.0.0",
        "providers": providers,
        **request_stats,
        "cache_hits": cache.get_hits(),
        "fallback_count": get_fallback_count(),
        "catalog_probe": probe.get_summary(),
    }


@router.get("/metrics")
async def metrics_endpoint(format: str = Query("prometheus")):
    """Public metrics: Prometheus exposition text, or JSON with ?format=json."""
    snapshot = metrics.collect()
    if format == "json":
        return JSONResponse(snapshot)
    return PlainTextResponse(metrics.to_prometheus(snapshot), media_type="text/plain; version=0.0.4")


@router.get("/v1/models")
async def list_models(
    http_request: Request, task_type: str | None = Query(None)
) -> dict[str, Any]:
    """List available models, filtered by task type and the caller's plan."""
    registry = await get_registry()
    models = registry.get_active()

    if task_type:
        models = registry.get_by_use_case(task_type)

    # Entitlement filter: each client sees only the models its plan grants.
    principal = _principal(http_request)
    models = [m for m in models if principal.can_see(m)]

    data = []
    for model in models:
        data.append(
            {
                "id": model.id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": model.provider_id,
                "permission": [],
                "root": model.id,
                "parent": None,
                "strength": model.strength,
                "provider": model.provider_id,
                "use_cases": model.use_cases,
                "context_window": model.context_window,
                "max_output": model.max_output_tokens,
                "rate_limits": model.rate_limits,
            }
        )

    return {"object": "list", "data": data}


@router.get("/v1/opencode/models")
async def list_models_opencode(http_request: Request) -> dict[str, Any]:
    """OpenCode-shaped model list, filtered by the caller's plan.

    OpenCode wants a minimal ``{"models": {id: {"name": ...}}}`` object (an
    array there trips its session parser). Same Registry + Principal filter as
    :func:`list_models`; only the output shape differs.
    """
    registry = await get_registry()
    principal = _principal(http_request)

    models = {
        m.id: {"name": m.display_name}
        for m in registry.get_active()
        if principal.can_see(m)
    }
    return {"models": models}


def _percent(used: int, limit: int) -> float:
    """Usage as a percentage of limit. 0 limit (unlimited) -> 0.0."""
    if limit <= 0:
        return 0.0
    return round(min(100.0, used / limit * 100.0), 1)


def _quota_exceeded(principal: Principal) -> JSONResponse | None:
    """Return a 429 if quota enforcement is on and the daily account cap is hit.

    Returns ``None`` (allow) when enforcement is off, the caller is the owner,
    or the plan is unlimited (quota 0). Reads live in-memory counters only.
    """
    if principal.is_owner or not get_config().usage.enforce:
        return None
    used = usage.get_client_usage(principal.client_id)
    req_used = sum(c["requests"] for c in used.values())
    tok_used = sum(c["tokens"] for c in used.values())
    if principal.quota_requests and req_used >= principal.quota_requests:
        return error_response(
            "Daily request quota exceeded for your plan", "rate_limit_error", 429
        )
    if principal.quota_tokens and tok_used >= principal.quota_tokens:
        return error_response(
            "Daily token quota exceeded for your plan", "rate_limit_error", 429
        )
    return None


async def build_usage_view(principal: Principal) -> dict[str, Any]:
    """Assemble the frontend-friendly usage-vs-quota document for a principal."""
    registry = await get_registry()
    period = usage.current_period()
    raw = usage.get_client_usage(principal.client_id, period)

    models = []
    totals = {"requests": 0, "tokens": 0}
    for model_id, counts in sorted(raw.items()):
        model = registry.get(model_id)
        limit = principal.limit_for(model_id)
        totals["requests"] += counts["requests"]
        totals["tokens"] += counts["tokens"]
        models.append(
            {
                "id": model_id,
                "name": model.display_name if model else model_id,
                "tier": model.tier if model else "auto",
                "usage": {"requests": counts["requests"], "tokens": counts["tokens"]},
                "limit": limit,
                "percent": {
                    "requests": _percent(counts["requests"], limit["requests"]),
                    "tokens": _percent(counts["tokens"], limit["tokens"]),
                },
            }
        )

    quota = {"requests": principal.quota_requests, "tokens": principal.quota_tokens}
    return {
        "client_id": principal.client_id,
        "plan": principal.plan,
        "period": period,
        "totals": totals,
        "quota": quota,
        "percent": {
            "requests": _percent(totals["requests"], quota["requests"]),
            "tokens": _percent(totals["tokens"], quota["tokens"]),
        },
        "models": models,
    }


@router.get("/v1/usage")
async def usage_endpoint(http_request: Request) -> dict[str, Any]:
    """Return the caller's own usage vs. quota for the current period."""
    return await build_usage_view(_principal(http_request))


@router.get("/v1/connection-info")
async def connection_info_endpoint() -> dict[str, Any]:
    """Public: self-describing 'how do I connect to this gateway?' document."""
    return await snippets.connection_info()


@router.get("/v1/agent-snippet")
async def agent_snippet_endpoint(
    agent: str = Query(..., description="Agent name, e.g. opencode, claude-code, hermes"),
    format: str = Query("text", description="'text' (snippet) or 'json' (structured config)"),
):
    """Public: a ready-to-use config snippet tailored for the requested agent."""
    try:
        return snippets.agent_snippet(agent, format)
    except ValueError as exc:
        return error_response(str(exc), "invalid_request_error", 400, param="agent")


def _session_id_from_request(http_request: Request, chat_request: ChatRequest) -> str:
    """Derive a session id from the client header or conversation content."""
    header = http_request.headers.get("X-Session-Id")
    messages = [m.model_dump(exclude_none=True) for m in chat_request.messages]
    return derive_session_id(messages, header)


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, http_request: Request):
    """OpenAI-compatible chat completions endpoint."""
    health.record_request()

    principal = _principal(http_request)

    # Entitlement gate: only the REQUESTED model is checked. Fallback targets
    # are an internal detail and stay unrestricted, so failover/circuit are
    # unaffected.
    registry = await get_registry()
    model = registry.get(request.model)
    if model is not None and not principal.can_see(model):
        return error_response(
            f"Model '{request.model}' is not available on your plan",
            "permission_error",
            403,
            param="model",
        )

    # Quota gate (opt-in): block once the daily account cap is reached. Off by
    # default and never applies to the owner, so it cannot regress existing use.
    quota_error = _quota_exceeded(principal)
    if quota_error is not None:
        return quota_error

    session_id = _session_id_from_request(http_request, request)
    sticky_model_id = get_sticky_model(session_id)

    if request.stream:
        # Streaming goes through the SAME remediation/circuit/health gates as the
        # non-streaming path (it used to bypass them, leaking 413/429 to users).
        # Token totals aren't available mid-stream, so we count the request only.
        usage.record(principal.client_id, request.model, tokens=0)
        return StreamingResponse(
            stream_with_fallback(
                request,
                request.task_type,
                session_id=session_id,
                sticky_model_id=sticky_model_id,
            ),
            media_type="text/event-stream",
        )

    start = time.time()
    response = await try_with_fallback(
        request, request.task_type, session_id=session_id, sticky_model_id=sticky_model_id
    )
    health.record_provider_result(
        response.provider,
        response.usage.total_tokens,
        (time.time() - start) * 1000,
    )
    # Bill the request against the CLIENT's gateway model id (what they asked
    # for), not the provider that ultimately served it after failover.
    usage.record(principal.client_id, request.model, tokens=response.usage.total_tokens)
    return JSONResponse(content=response.model_dump(mode="json"))


@router.post("/v1/responses")
async def responses(request: ChatRequest, http_request: Request):
    """Codex CLI compatibility endpoint — delegates to chat completions."""
    return await chat_completions(request, http_request)

