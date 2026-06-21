"""Tests for the boot-time smoke probe and auto-quarantine wiring."""

from __future__ import annotations

import pytest

from src.core import circuit, health, probe, smoke
from src.core.types import HealthStatus, ProviderError


@pytest.fixture(autouse=True)
def _reset_probe():
    probe.reset()
    yield
    probe.reset()


# --------------------------------------------------------------------------- #
# smoke_test_model                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_smoke_ok_on_nonempty_completion(loaded_registry, sample_response, monkeypatch):
    model = loaded_registry.get_active()[0]

    class _OK:
        async def chat(self, request):
            return sample_response

    async def _get_provider(_pid):
        return _OK()

    monkeypatch.setattr(smoke, "get_provider", _get_provider)
    result = await smoke.smoke_test_model(model)
    assert result["ok"] is True
    assert "latency_ms" in result


@pytest.mark.asyncio
async def test_smoke_maps_provider_error_code(loaded_registry, monkeypatch):
    model = loaded_registry.get_active()[0]

    class _Boom:
        async def chat(self, request):
            raise ProviderError("nope", "404")

    async def _get_provider(_pid):
        return _Boom()

    monkeypatch.setattr(smoke, "get_provider", _get_provider)
    result = await smoke.smoke_test_model(model)
    assert result["ok"] is False
    assert result["code"] == "404"


@pytest.mark.asyncio
async def test_smoke_fails_on_empty_completion(loaded_registry, monkeypatch):
    model = loaded_registry.get_active()[0]
    from src.core.types import ChatResponse

    empty = ChatResponse(
        model="x",
        choices=[{"index": 0, "message": {"role": "assistant", "content": "  "},
                  "finish_reason": "stop"}],
        usage={"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1},
    )

    class _Empty:
        async def chat(self, request):
            return empty

    async def _get_provider(_pid):
        return _Empty()

    monkeypatch.setattr(smoke, "get_provider", _get_provider)
    result = await smoke.smoke_test_model(model)
    assert result["ok"] is False
    assert result["code"] == "empty"


# --------------------------------------------------------------------------- #
# probe_all_models                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_probe_all_healthy(loaded_registry, monkeypatch):
    async def _all_ok(model, **kwargs):
        return {"ok": True, "latency_ms": 1.0}

    monkeypatch.setattr(probe, "smoke_test_model", _all_ok)
    summary = await probe.probe_all_models()

    total = len(loaded_registry.get_active())
    assert summary["probed"] == total
    assert summary["healthy"] == total
    assert summary["failed"] == 0
    assert summary["blacklisted"] == 0
    assert probe.get_summary() == summary


@pytest.mark.asyncio
async def test_probe_records_failures_into_circuit(loaded_registry, monkeypatch):
    async def _all_fail(model, **kwargs):
        return {"ok": False, "code": "404", "detail": "gone"}

    monkeypatch.setattr(probe, "smoke_test_model", _all_fail)
    summary = await probe.probe_all_models()

    assert summary["failed"] == summary["probed"] > 0
    assert summary["healthy"] == 0
    # Every failed model now carries breaker state with the probe's error code.
    snap = circuit.snapshot()
    assert snap
    assert all(b["last_code"] == "404" for b in snap.values())


@pytest.mark.asyncio
async def test_probe_blacklists_after_repeated_boots(loaded_registry, monkeypatch):
    """failures_to_open(3) * opens_to_blacklist(3) = 9 failing boots -> blacklist."""
    async def _all_fail(model, **kwargs):
        return {"ok": False, "code": "401", "detail": "bad key"}

    monkeypatch.setattr(probe, "smoke_test_model", _all_fail)
    summary = {}
    for _ in range(9):
        summary = await probe.probe_all_models()

    assert summary["blacklisted"] == summary["probed"] > 0


@pytest.mark.asyncio
async def test_probe_skips_rate_limited_providers(loaded_registry, monkeypatch):
    models = loaded_registry.get_active()
    victim_provider = models[0].provider_id
    health.set_status(victim_provider, HealthStatus.RATE_LIMITED.value)

    async def _all_ok(model, **kwargs):
        return {"ok": True, "latency_ms": 1.0}

    monkeypatch.setattr(probe, "smoke_test_model", _all_ok)
    summary = await probe.probe_all_models()

    skipped_models = sum(1 for m in models if m.provider_id == victim_provider)
    assert summary["skipped"] == skipped_models
    assert summary["probed"] == len(models) - skipped_models
