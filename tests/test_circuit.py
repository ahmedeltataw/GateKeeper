"""Tests for the per-model circuit breaker + auto-blacklist."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core import circuit


@pytest.fixture
def circuit_env(tmp_path, monkeypatch):
    """Point the breaker at an isolated SQLite db and report file."""
    report = tmp_path / "blacklist.md"
    fake_config = SimpleNamespace(
        circuit=SimpleNamespace(
            enabled=True,
            failures_to_open=3,
            open_cooldown_seconds=120,
            opens_to_blacklist=3,
            report_file=str(report),
        ),
        database=SimpleNamespace(path=str(tmp_path / "gateway.db")),
    )
    monkeypatch.setattr(circuit, "get_config", lambda: fake_config)
    circuit.reset_all()
    yield report
    circuit.reset_all()


@pytest.mark.asyncio
async def test_breaker_opens_after_threshold_failures(circuit_env):
    """Three consecutive failures open the breaker and block routing."""
    await circuit.init()
    for _ in range(3):
        await circuit.record_failure("model-a", "5xx", "server error")

    assert circuit.is_open("model-a") is True


@pytest.mark.asyncio
async def test_success_closes_the_breaker(circuit_env):
    """A success after failures resets the breaker so the model routes again."""
    await circuit.init()
    for _ in range(3):
        await circuit.record_failure("model-a", "5xx", "server error")
    await circuit.record_success("model-a")

    assert circuit.is_open("model-a") is False


@pytest.mark.asyncio
async def test_repeated_opens_blacklist_and_write_report(circuit_env):
    """Opening repeatedly blacklists the model and records a failure report."""
    report = circuit_env
    await circuit.init()
    # 3 opens * 3 failures each = blacklist threshold reached.
    for _ in range(9):
        await circuit.record_failure("model-b", "5xx", "server error")

    state = circuit.snapshot()["model-b"]
    assert state["state"] == "blacklisted"
    assert circuit.is_open("model-b") is True
    assert report.exists()
    assert "model-b" in report.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_reset_clears_blacklist(circuit_env):
    """Manual reset returns a blacklisted model to routable."""
    await circuit.init()
    for _ in range(9):
        await circuit.record_failure("model-b", "5xx", "server error")
    await circuit.reset("model-b")

    assert circuit.is_open("model-b") is False
