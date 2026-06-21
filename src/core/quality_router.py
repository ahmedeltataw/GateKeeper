"""Quality Router — selects the strongest task-appropriate model with budget."""

from __future__ import annotations

from src.providers import list_provider_ids

from src.core import circuit, health
from src.core.registry import get_registry
from src.core.types import ModelInfo

# Preferred model chains per IMPLEMENTATION_PLAN.md §5.  Each chain lists gateway
# model ids in priority order; the router walks the chain and returns the first
# active, budget-available model.
#
# Ordering rule: doc-verified models come FIRST. Roadmap candidates (unverified
# 2025/2026 ids, see sync_models.py) are appended LAST, so "auto" only routes to
# a candidate when every verified option is exhausted — and if a candidate id is
# broken the boot probe / circuit breaker has already quarantined it.
_PREFERRED_CHAINS: dict[str, list[str]] = {
    "coding": [
        "or-qwen3-coder",
        "mistral-codestral",
        "nv-qwen2.5-coder-32b",
        "groq-llama-3.3-70b",
        "cf-qwen2.5-coder-32b",
        "gemini-2.5-pro",
        "groq-gpt-oss-120b",
        # candidates:
        "oczen-deepseek-v4-flash",
        "gh-deepseek-v3-0324",
        "groq-qwen3.6-27b",
        "or-qwen3-next-80b",
        "cf-kimi-k2.7-code",
        "glm-5.2-flash",
    ],
    "search": [
        "gemini-2.5-flash",
        "groq-llama-3.3-70b",
        "or-llama-3.3-70b",
        "mistral-large",
        "gh-gpt-4o",
        # candidates:
        "gemini-3.5-flash",
        "gemini-3-flash",
        "cf-kimi-k2.6",
        "or-gemma-4-26b",
    ],
    "reasoning": [
        "gemini-2.5-pro",
        "nv-deepseek-r1",
        "groq-gpt-oss-120b",
        "cb-gpt-oss-120b",
        "or-glm-4.5-air",
        # candidates:
        "oczen-deepseek-v4-flash",
        "gh-deepseek-r1-0528",
        "gh-o4-mini",
        "or-nemotron-3-super-120b",
        "groq-compound",
    ],
    "creative": [
        "gh-gpt-4o",
        "gemini-2.5-flash",
        "or-llama-3.3-70b",
        "mistral-medium",
        "or-gemma-4-31b",
        # candidates:
        "or-gemma-4-26b",
        "cf-gemma-4-26b",
        "oczen-big-pickle-stealth",
    ],
    "data": [
        "gh-gpt-4o",
        "mistral-large",
        "groq-llama-3.3-70b",
        "gemini-2.5-flash",
        "nv-llama-3.3-70b",
        # candidates:
        "gemini-3.1-flash-lite",
        "or-nemotron-3-nano-30b",
        "glm-5.2-air",
    ],
    "vision": [
        "gemini-2.5-flash",
        "mistral-pixtral",
        "cf-llama-3.2-11b-vision",
        "glm-4.6v-flash",
        # candidates:
        "gemini-3.5-flash",
    ],
    "default": [
        "gemini-2.5-flash",
        "groq-llama-3.3-70b",
        "or-llama-3.3-70b",
        "groq-gpt-oss-120b",
        # candidates:
        "gemini-3.5-flash",
        "oczen-deepseek-v4-flash",
        "groq-qwen3.6-27b",
    ],
}


async def select_best_model(
    task_type: str,
    rate_limiter,
) -> ModelInfo | None:
    """Return the best model for ``task_type`` that still has budget.

    Walks the preferred chain for the task type, then falls back to all active
    models matching the use case sorted by strength.
    """
    registry = await get_registry()

    registered_providers = set(list_provider_ids())

    def _is_available(model: ModelInfo) -> bool:
        return (
            model.enabled
            and model.status == "active"
            and model.provider_id in registered_providers
            and health.is_routable(model.provider_id)
            and not circuit.is_open(model.id)
        )

    # Try the explicit preferred chain first.
    for model_id in _PREFERRED_CHAINS.get(task_type, []):
        model = registry.get(model_id)
        if model is None or not _is_available(model):
            continue
        if await rate_limiter.allow(model.provider_id, model.id):
            return model

    # Fall back to every active model that supports the use case. Instead of a
    # pure strength sort, score dynamically (§3.2): demote models whose breaker
    # has tripped recently and providers that are slow, so a degraded-but-active
    # model never outranks a healthy one of equal strength.
    candidates = sorted(registry.get_best_for_task(task_type), key=_dynamic_key)
    for model in candidates:
        if not _is_available(model):
            continue
        if await rate_limiter.allow(model.provider_id, model.id):
            return model

    return None


def _dynamic_key(model: ModelInfo) -> tuple[int, int, int, float]:
    """Sort key: healthy + strong + fast first. Lower is better.

    Order of influence: how many times the breaker opened, recent consecutive
    failures, declared strength, then provider average latency. Pulls live state
    from the circuit snapshot and provider analytics.
    """
    breaker = circuit.snapshot().get(model.id, {})
    open_count = int(breaker.get("open_count", 0))
    consecutive = int(breaker.get("consecutive_failures", 0))
    analytics = health.get_provider_analytics().get(model.provider_id, {})
    avg_latency = float(analytics.get("avg_latency_ms", 0.0))
    return (open_count, consecutive, model.strength_order, avg_latency)
