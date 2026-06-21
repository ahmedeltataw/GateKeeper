"""Tests for /metrics, the Prometheus builder, and dynamic router scoring."""

from __future__ import annotations

import pytest

from src.core import circuit, health, metrics
from src.core.quality_router import _dynamic_key


# --------------------------------------------------------------------------- #
# Prometheus builder (pure)                                                   #
# --------------------------------------------------------------------------- #
def test_to_prometheus_renders_expected_series():
    snapshot = {
        "requests_total": 5,
        "requests_last_hour": 2,
        "uptime_seconds": 99,
        "cache_hits": 1,
        "fallback_total": 3,
        "circuit": {"closed": 10, "open": 1, "blacklisted": 2},
        "probe": {"probed": 10, "healthy": 8, "failed": 2, "blacklisted": 2},
        "providers": {"groq": {"requests": 4, "tokens": 100, "avg_latency_ms": 50.0, "up": 1}},
    }
    text = metrics.to_prometheus(snapshot)
    assert "gatekeeper_requests_total 5" in text
    assert 'gatekeeper_models_circuit{state="blacklisted"} 2' in text
    assert 'gatekeeper_provider_up{provider="groq"} 1' in text
    assert "gatekeeper_probe_healthy 8" in text
    # Every metric must declare a TYPE for a valid exposition format.
    assert text.count("# TYPE") >= 5


# --------------------------------------------------------------------------- #
# /metrics endpoint                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_metrics_endpoint_public_prometheus(test_app, loaded_registry):
    resp = await test_app.get("/metrics")  # no auth header — must be public
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "gatekeeper_requests_total" in resp.text


@pytest.mark.asyncio
async def test_metrics_endpoint_json(test_app, loaded_registry):
    resp = await test_app.get("/metrics", params={"format": "json"})
    assert resp.status_code == 200
    body = resp.json()
    assert "requests_total" in body
    assert "circuit" in body
    assert "providers" in body


# --------------------------------------------------------------------------- #
# Dynamic router scoring                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_dynamic_key_demotes_flaky_model(loaded_registry):
    model = loaded_registry.get_active()[0]
    clean_key = _dynamic_key(model)
    assert clean_key[0] == 0  # open_count starts at zero

    # Trip the breaker: failures_to_open (default 3) opens it once.
    for _ in range(3):
        await circuit.record_failure(model.id, "5xx", "boom")

    flaky_key = _dynamic_key(model)
    assert flaky_key[0] >= 1            # open_count incremented
    assert flaky_key > clean_key       # sorts strictly after the clean version


def test_dynamic_key_factors_provider_latency(loaded_registry):
    model = loaded_registry.get_active()[0]
    health.record_provider_result(model.provider_id, tokens=10, latency_ms=999.0)
    key = _dynamic_key(model)
    assert key[3] == pytest.approx(999.0)  # latency surfaces as the 4th sort factor
