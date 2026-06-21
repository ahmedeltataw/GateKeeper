"""Observability: collect gateway metrics and render Prometheus exposition text.

``collect()`` snapshots the same runtime sources ``/health`` reads (request
counters, per-provider analytics, circuit states, last boot probe). ``to_prometheus()``
is a pure function over that snapshot so the formatting is unit-testable without
a running server.
"""

from __future__ import annotations

from typing import Any

from src.core import cache, circuit, health
from src.core import probe as probe_mod
from src.core.fallback import get_fallback_count


def collect() -> dict[str, Any]:
    """Snapshot gateway metrics into a JSON-friendly dict."""
    stats = health.get_request_stats()
    analytics = health.get_provider_analytics()
    statuses = health.get_all_statuses()

    state_counts = {circuit.STATE_CLOSED: 0, circuit.STATE_OPEN: 0, circuit.STATE_BLACKLISTED: 0}
    for breaker in circuit.snapshot().values():
        state = breaker.get("state", circuit.STATE_CLOSED)
        state_counts[state] = state_counts.get(state, 0) + 1

    providers = {
        pid: {
            **analytics.get(pid, {"requests": 0, "tokens": 0, "avg_latency_ms": 0.0}),
            "status": details.get("status", "unknown"),
            "up": 1 if health.is_routable(pid) else 0,
        }
        for pid, details in statuses.items()
    }
    # Providers with analytics but no health status yet still count.
    for pid, entry in analytics.items():
        providers.setdefault(
            pid, {**entry, "status": "unknown", "up": 1 if health.is_routable(pid) else 0}
        )

    return {
        "requests_total": stats["requests_total"],
        "requests_last_hour": stats["requests_last_hour"],
        "uptime_seconds": stats["uptime_seconds"],
        "cache_hits": cache.get_hits(),
        "fallback_total": get_fallback_count(),
        "circuit": state_counts,
        "probe": probe_mod.get_summary(),
        "providers": providers,
    }


def _line(name: str, value: Any, labels: dict[str, str] | None = None) -> str:
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


def to_prometheus(snapshot: dict[str, Any]) -> str:
    """Render a metrics snapshot as Prometheus text exposition format."""
    lines: list[str] = []

    def gauge(name: str, help_text: str, value: Any, labels: dict[str, str] | None = None) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(_line(name, value, labels))

    gauge("gatekeeper_requests_total", "Total requests since start.", snapshot["requests_total"])
    gauge("gatekeeper_requests_last_hour", "Requests in the last hour.", snapshot["requests_last_hour"])
    gauge("gatekeeper_uptime_seconds", "Uptime in seconds.", snapshot["uptime_seconds"])
    gauge("gatekeeper_cache_hits", "Cache hits since start.", snapshot["cache_hits"])
    gauge("gatekeeper_fallback_total", "Successful fallbacks (tier>=2).", snapshot["fallback_total"])

    lines.append("# HELP gatekeeper_models_circuit Models per circuit-breaker state.")
    lines.append("# TYPE gatekeeper_models_circuit gauge")
    for state, count in snapshot["circuit"].items():
        lines.append(_line("gatekeeper_models_circuit", count, {"state": state}))

    probe = snapshot.get("probe") or {}
    if probe:
        for key in ("probed", "healthy", "failed", "blacklisted"):
            gauge(f"gatekeeper_probe_{key}", f"Boot probe: {key}.", probe.get(key, 0))

    lines.append("# HELP gatekeeper_provider_up Provider routable (1) or not (0).")
    lines.append("# TYPE gatekeeper_provider_up gauge")
    for pid, p in snapshot["providers"].items():
        lines.append(_line("gatekeeper_provider_up", p["up"], {"provider": pid}))
    lines.append("# HELP gatekeeper_provider_requests_total Per-provider request count.")
    lines.append("# TYPE gatekeeper_provider_requests_total gauge")
    for pid, p in snapshot["providers"].items():
        lines.append(_line("gatekeeper_provider_requests_total", p.get("requests", 0), {"provider": pid}))
    lines.append("# HELP gatekeeper_provider_avg_latency_ms Per-provider average latency.")
    lines.append("# TYPE gatekeeper_provider_avg_latency_ms gauge")
    for pid, p in snapshot["providers"].items():
        lines.append(_line("gatekeeper_provider_avg_latency_ms", p.get("avg_latency_ms", 0.0), {"provider": pid}))

    return "\n".join(lines) + "\n"
