"""4-tier fallback engine with context handoff.

When the primary model/provider fails, this module walks down a chain of
alternatives and injects a context handoff note when the model changes.
"""

from __future__ import annotations

import asyncio
import json
import logging

from src.core import cache, circuit, diagnostics, health, key_manager, rate_limiter
from src.core.config_loader import get_config

logger = logging.getLogger("gateway.fallback")
from src.core.quality_router import select_best_model
from src.core.registry import get_registry
from src.core.router import get_provider, invalidate_provider
from src.core.sticky import set_sticky_model
from src.core.types import (
    AllRateLimitedError,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
    ModelNotFoundError,
    NoHealthyProviderError,
    ProviderError,
)

COOLDOWN: dict[str, int | None] = {
    "429": 60,
    "5xx": 30,
    # A timeout used to be retried instantly (0s), which let "auto" hammer a
    # dead provider. Cool it for 30s so failover moves on and stays moved on.
    "timeout": 30,
    "401": None,
    "404": None,
}

# Provider failure code -> health status to record, so the health gate skips
# this provider for the rest of the run and subsequent requests until the next
# successful probe clears it.
_FAILURE_HEALTH: dict[str, str] = {
    "429": HealthStatus.RATE_LIMITED.value,
    "5xx": HealthStatus.ERROR.value,
    "timeout": HealthStatus.UNREACHABLE.value,
    "401": HealthStatus.INVALID.value,
}

_HANDOFF_TEMPLATE = (
    "[Note: This conversation was started with {original_model}.\n"
    "The current model ({new_model}) is continuing the conversation\n"
    "because the original was unavailable. Please maintain the same\n"
    "tone, style, and follow the existing conversation flow.\n"
    "Please continue where the previous model left off."
)

# In-process counter exposed to the /health endpoint.
_fallback_count = 0

# Recent Smart-Diagnostic remediations, surfaced to the user/dashboard.
_recent_remediations: list[dict[str, str]] = []
_MAX_REMEDIATION_LOG = 50


def get_fallback_count() -> int:
    """Return the number of fallback (tier >= 2) successes so far."""
    return _fallback_count


def get_recent_remediations() -> list[dict[str, str]]:
    """Return recent 'problem X in model Y fixed via Z' remediation records."""
    return list(_recent_remediations)


def _record_remediation(model_id: str, explanation: str) -> None:
    _recent_remediations.append({"model": model_id, "remediation": explanation})
    del _recent_remediations[:-_MAX_REMEDIATION_LOG]


async def _call_with_remediation(
    provider, request: ChatRequest, model: ModelInfo
) -> ChatResponse:
    """Call the provider, letting the diagnostics engine repair recoverable
    failures (413 shrink, 429/5xx/timeout backoff) before giving up."""
    cfg = get_config().diagnostics
    current = request
    attempt = 0
    while True:
        try:
            return await provider.chat(current.model_copy(update={"model": model.id}))
        except ProviderError as exc:
            if not cfg.enabled or attempt >= cfg.max_remediation_attempts:
                raise
            plan = diagnostics.diagnose(
                exc.code, current, attempt, max_backoff_seconds=cfg.max_backoff_seconds
            )
            if not plan.will_retry:
                raise
            logger.info("remediation: model %s — %s", model.id, plan.explanation)
            _record_remediation(model.id, plan.explanation)
            if plan.action == "retry_modified" and plan.request is not None:
                current = plan.request
            elif plan.action == "retry_after":
                await asyncio.sleep(plan.delay_seconds)
            attempt += 1


async def _handle_provider_error(
    provider_id: str, model: ModelInfo, exc: ProviderError
) -> None:
    """Apply the correct penalty for a provider failure (§6).

    - 401 (bad key): disable the provider, mark its key invalid, drop the
      cached provider instance so a fixed key is picked up later.
    - 404 (model removed upstream): mark the *model* removed; keep the
      provider — its other models are unaffected.
    - everything else: temporary cooldown (unknown codes default to 30s, never
      a permanent disable).
    """
    code = exc.code
    # Record the failure in the health map so the routing gate skips this
    # provider immediately (404 is model-specific, not a provider fault).
    if code in _FAILURE_HEALTH:
        health.set_status(provider_id, _FAILURE_HEALTH[code])

    if code == "401":
        rate_limiter.disable(provider_id)
        try:
            await key_manager.update_health(provider_id, "invalid")
        except Exception:
            pass
        await invalidate_provider(provider_id)
    elif code == "404":
        registry = await get_registry()
        registry.mark_removed(model.id)
    else:
        rate_limiter.cooldown(provider_id, COOLDOWN.get(code, 30))


def _inject_context_handoff(request: ChatRequest, original: str, new: str) -> ChatRequest:
    """Insert the context handoff system message at index 1."""
    from src.core.types import Message

    handoff_message = Message(
        role="system",
        content=_HANDOFF_TEMPLATE.format(original_model=original, new_model=new),
    )
    messages = [request.messages[0]] if request.messages else []
    messages.append(handoff_message)
    messages.extend(request.messages[1:])
    return request.model_copy(update={"messages": messages})


async def _try_single_model(
    request: ChatRequest,
    model: ModelInfo,
    original_model: str,
    tier: int,
    tried: set[str],
) -> ChatResponse | None:
    """Try one model on its own provider, using its own gateway id.

    Each ``ModelInfo`` carries the correct ``provider_id`` + gateway ``id``, so
    we always call ``chat()`` with an id the target provider actually knows.
    """
    global _fallback_count

    if model.id in tried:
        return None
    tried.add(model.id)

    provider_id = model.provider_id
    # Health gate: never route to a provider the last probe found broken
    # (error / unreachable / invalid / rate_limited). This is what stops "auto"
    # from stalling on a dead provider.
    if not health.is_routable(provider_id):
        return None
    # Circuit gate: skip models whose breaker is open (cooling down) or
    # blacklisted after repeated, non-recoverable failures.
    if circuit.is_open(model.id):
        return None
    if not await rate_limiter.allow(provider_id, model.id):
        return None

    provider = await get_provider(provider_id)
    resolved_request = request
    if tier >= 2 and model.id != original_model:
        resolved_request = _inject_context_handoff(request, original_model, model.id)
    # Proactive remediation: clamp the request to the model's limits before send.
    resolved_request = diagnostics.preflight_clamp(resolved_request, model)

    try:
        response = await _call_with_remediation(provider, resolved_request, model)
    except ProviderError as exc:
        logger.warning("provider %s failed on %s: [%s] %s", provider_id, model.id, exc.code, exc)
        await circuit.record_failure(model.id, exc.code, str(exc))
        await _handle_provider_error(provider_id, model, exc)
        return None
    except Exception as exc:
        # Resilience: an unexpected provider failure must never crash the
        # gateway. Mark it down, cool it briefly, and fall through to the next.
        logger.warning("provider %s raised unexpectedly on %s: %r", provider_id, model.id, exc)
        await circuit.record_failure(model.id, "5xx", repr(exc))
        health.set_status(provider_id, HealthStatus.ERROR.value)
        rate_limiter.cooldown(provider_id, COOLDOWN["5xx"])
        return None

    # A real success clears any stale unhealthy mark and resets the breaker so
    # the model is routable again without waiting for a background probe.
    health.set_status(provider_id, HealthStatus.HEALTHY.value)
    await circuit.record_success(model.id)
    response.provider = provider_id
    response.original_model = original_model
    response.fallback_used = tier >= 2
    if tier >= 2:
        response.fallback_chain.append(model.id)
        _fallback_count += 1
    return response


async def _models_by_strength(strength: str) -> list[ModelInfo]:
    registry = await get_registry()
    return registry.get_by_strength(strength)


async def _try_tier(
    request: ChatRequest,
    models: list[ModelInfo],
    original_model: str,
    tier: int,
    tried: set[str],
) -> ChatResponse | None:
    """Walk a list of models and try each one on its provider."""
    for model in models:
        response = await _try_single_model(request, model, original_model, tier, tried)
        if response is not None:
            return response
    return None


async def try_with_fallback(
    request: ChatRequest,
    task_type: str,
    session_id: str | None = None,
    sticky_model_id: str | None = None,
) -> ChatResponse:
    """Execute a chat request with the 4-tier fallback chain."""
    if not request.stream:
        cached = cache.get(
            request.model,
            [m.model_dump(exclude_none=True) for m in request.messages],
            request.temperature,
            request.max_tokens,
        )
        if cached is not None:
            return cached

    registry = await get_registry()

    preferred: ModelInfo | None = None
    if request.model == "auto":
        # Auto: honour a sticky pin first, else let the Quality Router choose.
        if sticky_model_id:
            preferred = registry.get(sticky_model_id)
        if preferred is None:
            preferred = await select_best_model(task_type, rate_limiter)
    else:
        # Explicit model: ALWAYS honour it. A sticky pin never overrides an
        # explicit choice (it only applies to "auto" requests).
        preferred = registry.get(request.model)
        if preferred is None:
            # Explicit unknown model → 404, per the API contract (§3.5).
            available = ", ".join(sorted(m.id for m in registry.get_active()))
            raise ModelNotFoundError(
                f"Model '{request.model}' not found. Available models: {available}"
            )

    if preferred is None:
        raise NoHealthyProviderError("No suitable model found for task")

    original_model = preferred.id
    tried: set[str] = set()

    # Tier 1: preferred/sticky model, then any sibling sharing its
    # provider_model_id on a different provider (each tried with its own id).
    response: ChatResponse | None = None
    for model in registry.get_models_sharing(preferred.id):
        response = await _try_single_model(request, model, original_model, 1, tried)
        if response is not None:
            break

    # Tier 2: same strength, different models.
    if response is None:
        same_strength = [
            m
            for m in await _models_by_strength(preferred.strength)
            if m.id != original_model
        ]
        response = await _try_tier(request, same_strength, original_model, 2, tried)

    # Tier 3: one strength lower.
    if response is None:
        lower_order = preferred.strength_order + 1
        strength_values = ["S", "A", "B", "C"]
        if lower_order < len(strength_values):
            lower_strength = strength_values[lower_order]
            lower_models = await _models_by_strength(lower_strength)
            response = await _try_tier(request, lower_models, original_model, 3, tried)

    # Tier 4: any available active model with budget.
    if response is None:
        all_models = registry.get_active()
        response = await _try_tier(request, all_models, original_model, 4, tried)

    if response is not None:
        if session_id:
            set_sticky_model(session_id, response.model)
        if not request.stream:
            cache.set(
                request.model,
                [m.model_dump(exclude_none=True) for m in request.messages],
                request.temperature,
                request.max_tokens,
                response,
            )
        return response

    # Determine the most appropriate error based on cooldown state.
    provider_ids = {m.provider_id for m in registry.get_active()}
    if provider_ids:
        all_rate_limited = all(
            not allowed for allowed in await asyncio.gather(
                *(rate_limiter.allow(pid) for pid in provider_ids)
            )
        )
        if all_rate_limited:
            raise AllRateLimitedError("All providers are rate limited")
    raise NoHealthyProviderError("No healthy provider available")


# --------------------------------------------------------------------------- #
# Streaming path — same gates + remediation as the non-streaming engine.
# Failover is possible only until the first byte is sent; after that a
# mid-stream failure ends the stream with an inline error chunk.
# --------------------------------------------------------------------------- #


def _stream_error(message: str, error_type: str) -> str:
    """Build a terminal SSE error frame followed by [DONE]."""
    payload = json.dumps({"error": {"message": message, "type": error_type}})
    return f"data: {payload}\n\ndata: [DONE]\n\n"


def _ordered_stream_candidates(registry, preferred: ModelInfo) -> list[ModelInfo]:
    """Return candidate models in 4-tier fallback order, de-duplicated."""
    seen: set[str] = set()
    ordered: list[ModelInfo] = []

    def _add(models: list[ModelInfo]) -> None:
        for model in models:
            if model.id not in seen:
                seen.add(model.id)
                ordered.append(model)

    _add(registry.get_models_sharing(preferred.id))
    _add([m for m in registry.get_by_strength(preferred.strength) if m.id != preferred.id])
    lower_order = preferred.strength_order + 1
    strength_values = ["S", "A", "B", "C"]
    if lower_order < len(strength_values):
        _add(registry.get_by_strength(strength_values[lower_order]))
    _add(registry.get_active())
    return ordered


async def _resolve_stream_preferred(
    registry, request: ChatRequest, task_type: str, sticky_model_id: str | None
) -> ModelInfo | None:
    """Resolve the starting model for a streaming request (mirrors non-stream)."""
    if request.model == "auto":
        if sticky_model_id:
            pinned = registry.get(sticky_model_id)
            if pinned is not None:
                return pinned
        return await select_best_model(task_type, rate_limiter)

    preferred = registry.get(request.model)
    if preferred is None:
        available = ", ".join(sorted(m.id for m in registry.get_active()))
        raise ModelNotFoundError(
            f"Model '{request.model}' not found. Available models: {available}"
        )
    return preferred


async def _open_stream(provider, request: ChatRequest, model: ModelInfo):
    """Try to open a stream, remediating pre-first-byte failures.

    Returns an async iterator that re-emits the first chunk plus the rest, or
    ``None`` when this model could not start a stream (caller moves to the next).
    """
    cfg = get_config().diagnostics
    current = request
    attempt = 0
    while True:
        agen = provider.chat_stream(current.model_copy(update={"model": model.id}))
        try:
            first_chunk = await agen.__anext__()
        except StopAsyncIteration:
            return None
        except ProviderError as exc:
            logger.warning("stream provider failed on %s: [%s] %s", model.id, exc.code, exc)
            await circuit.record_failure(model.id, exc.code, str(exc))
            await _handle_provider_error(model.provider_id, model, exc)
            plan = diagnostics.diagnose(
                exc.code, current, attempt, max_backoff_seconds=cfg.max_backoff_seconds
            )
            if cfg.enabled and plan.will_retry and attempt < cfg.max_remediation_attempts:
                logger.info("stream remediation: model %s — %s", model.id, plan.explanation)
                _record_remediation(model.id, plan.explanation)
                if plan.action == "retry_modified" and plan.request is not None:
                    current = plan.request
                elif plan.action == "retry_after":
                    await asyncio.sleep(plan.delay_seconds)
                attempt += 1
                continue
            return None
        except Exception as exc:
            logger.warning("stream provider raised on %s: %r", model.id, exc)
            await circuit.record_failure(model.id, "5xx", repr(exc))
            health.set_status(model.provider_id, HealthStatus.ERROR.value)
            rate_limiter.cooldown(model.provider_id, COOLDOWN["5xx"])
            return None
        return _resume_stream(first_chunk, agen)


async def _resume_stream(first_chunk: str, agen):
    """Re-emit the already-pulled first chunk, then the remaining stream."""
    yield first_chunk
    async for chunk in agen:
        yield chunk


async def stream_with_fallback(
    request: ChatRequest,
    task_type: str,
    session_id: str | None = None,
    sticky_model_id: str | None = None,
):
    """Stream a chat completion through the health/circuit/remediation gates.

    Walks candidate models in fallback order; for each it applies the same gates
    as the non-streaming engine and a proactive payload clamp, then tries to open
    the stream. Pre-first-byte failures fail over to the next model; once bytes
    flow, the chosen stream runs to completion.
    """
    registry = await get_registry()
    preferred = await _resolve_stream_preferred(registry, request, task_type, sticky_model_id)
    if preferred is None:
        yield _stream_error("No suitable model found for task", "service_unavailable")
        return

    for model in _ordered_stream_candidates(registry, preferred):
        if circuit.is_open(model.id) or not health.is_routable(model.provider_id):
            continue
        if not await rate_limiter.allow(model.provider_id, model.id):
            continue
        provider = await get_provider(model.provider_id)
        clamped = diagnostics.preflight_clamp(request, model)
        stream = await _open_stream(provider, clamped, model)
        if stream is None:
            continue
        health.set_status(model.provider_id, HealthStatus.HEALTHY.value)
        await circuit.record_success(model.id)
        if session_id:
            set_sticky_model(session_id, model.id)
        async for chunk in stream:
            yield chunk
        return

    yield _stream_error("No healthy provider available for streaming", "service_unavailable")
