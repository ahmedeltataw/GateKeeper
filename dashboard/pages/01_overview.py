"""Dashboard overview page showing gateway stats and provider statuses."""

from __future__ import annotations

import streamlit as st

from components.metric_cards import render_metric_cards, render_provider_status_grid
from session import render_api_error, require_auth


def main() -> None:
    """Render the overview page with stats and provider status."""
    st.title("GateKeeper Overview")
    client = require_auth()

    try:
        render_metric_cards(client.get_stats())
        st.divider()
        st.subheader("Provider Status")
        render_provider_status_grid(client.get_providers())
    except Exception as exc:  # noqa: BLE001 — mapped to a friendly message, real bugs re-raise
        render_api_error(exc)


main()
