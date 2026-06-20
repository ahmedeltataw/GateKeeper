"""Pure render helpers for metric cards and provider status grids.

These functions accept typed data and return Streamlit widgets. No business
logic, no HTTP calls, no side effects beyond rendering.
"""

from __future__ import annotations

import streamlit as st

from api_client import AdminStats, ProviderStatus


def render_metric_cards(stats: AdminStats) -> None:
    """Display five labeled metric cards from gateway counters."""
    col1, col2, col3, col4, col5 = st.columns(5)
    uptime_minutes = stats.uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_label = f"{uptime_hours}h {uptime_minutes % 60}m" if uptime_hours else f"{uptime_minutes}m"

    col1.metric("Total Requests", str(stats.requests_total))
    col2.metric("Requests (1h)", str(stats.requests_last_hour))
    col3.metric("Cache Hits", str(stats.cache_hits))
    col4.metric("Fallbacks", str(stats.fallback_count))
    col5.metric("Uptime", uptime_label)


def render_provider_status_grid(providers: list[ProviderStatus]) -> None:
    """Display each provider's status as a labelled badge row."""
    if not providers:
        st.caption("No providers have been checked yet.")
        return

    cols = st.columns(min(len(providers), 4))
    for idx, provider in enumerate(providers):
        with cols[idx % 4]:
            st.markdown(f"**{provider.id}** — {provider.status}")
