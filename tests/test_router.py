"""Tests for the Quality Router / model routing."""

from __future__ import annotations

import pytest

from src.core import health, rate_limiter
from src.core.quality_router import select_best_model
from src.core.registry import get_registry
from src.core.types import HealthStatus


@pytest.mark.asyncio
async def test_quality_router_prefers_task_appropriate_model(loaded_registry):
    model = await select_best_model("coding", rate_limiter)
    assert model is not None
    assert "coding" in model.use_cases


@pytest.mark.asyncio
async def test_quality_router_respects_explicit_chain(loaded_registry):
    model = await select_best_model("reasoning", rate_limiter)
    # Preferred reasoning chain starts with gemini-2.5-pro.
    assert model.id == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_quality_router_skips_over_budget_provider(loaded_registry):
    # Exhaust gemini RPM so the router must fall through the reasoning chain.
    for _ in range(15):
        await rate_limiter.allow("gemini")
    model = await select_best_model("reasoning", rate_limiter)
    assert model.id != "gemini-2.5-pro"
    assert "reasoning" in model.use_cases


@pytest.mark.asyncio
async def test_quality_router_default_uses_general_chain(loaded_registry):
    model = await select_best_model("default", rate_limiter)
    assert model is not None
    # Default chain leads with the best general free model.
    assert model.id == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_quality_router_skips_unhealthy_provider(loaded_registry):
    """The router must not select a model whose provider last probed unhealthy."""
    # Default chain leads with gemini-2.5-flash (provider 'gemini').
    health.set_status("gemini", HealthStatus.ERROR.value)
    model = await select_best_model("default", rate_limiter)
    assert model is not None
    assert model.provider_id != "gemini"


@pytest.mark.asyncio
async def test_registry_get_best_for_task_sorts_by_strength(loaded_registry):
    registry = await get_registry()
    coding = registry.get_best_for_task("coding")
    strengths = [m.strength for m in coding[:5]]
    assert strengths == sorted(strengths, key=lambda s: {"S": 0, "A": 1, "B": 2, "C": 3}[s])
