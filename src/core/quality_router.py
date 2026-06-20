"""Quality Router — selects the strongest task-appropriate model with budget."""

from __future__ import annotations

from src.providers import list_provider_ids

from src.core import circuit, health
from src.core.registry import get_registry
from src.core.types import ModelInfo

# Preferred model chains per IMPLEMENTATION_PLAN.md §5.  Each chain lists gateway
# model ids in priority order; the router walks the chain and returns the first
# active, budget-available model.
_PREFERRED_CHAINS: dict[str, list[str]] = {
    "coding": [
        "or-qwen3-coder",
        "mistral-codestral",
        "nv-qwen2.5-coder-32b",
        "groq-llama-3.3-70b",
        "cf-qwen2.5-coder-32b",
        "gemini-2.5-pro",
        "groq-gpt-oss-120b",
    ],
    "search": [
        "gemini-2.5-flash",
        "groq-llama-3.3-70b",
        "or-llama-3.3-70b",
        "mistral-large",
        "gh-gpt-4o",
    ],
    "reasoning": [
        "gemini-2.5-pro",
        "nv-deepseek-r1",
        "groq-gpt-oss-120b",
        "cb-gpt-oss-120b",
        "or-glm-4.5-air",
    ],
    "creative": [
        "gh-gpt-4o",
        "gemini-2.5-flash",
        "or-llama-3.3-70b",
        "mistral-medium",
        "or-gemma-4-31b",
    ],
    "data": [
        "gh-gpt-4o",
        "mistral-large",
        "groq-llama-3.3-70b",
        "gemini-2.5-flash",
        "nv-llama-3.3-70b",
    ],
    "vision": [
        "gemini-2.5-flash",
        "mistral-pixtral",
        "cf-llama-3.2-11b-vision",
        "glm-4.6v-flash",
    ],
    "default": [
        "gemini-2.5-flash",
        "groq-llama-3.3-70b",
        "or-llama-3.3-70b",
        "groq-gpt-oss-120b",
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

    # Fall back to every active model that supports the use case, S-tier first.
    candidates = registry.get_best_for_task(task_type)
    for model in candidates:
        if not _is_available(model):
            continue
        if await rate_limiter.allow(model.provider_id, model.id):
            return model

    return None
