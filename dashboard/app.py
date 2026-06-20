"""Streamlit entrypoint for the standalone GateKeeper dashboard."""

from __future__ import annotations

import streamlit as st

from api_client import (
    AdminApiClient,
    AdminTokenNotConfiguredError,
    AdminUnauthorizedError,
    GatewayUnavailableError,
)
from config import DashboardConfig, load_dashboard_config
from session import clear_auth, is_authenticated, remember_auth, render_api_error


def _candidate_token(config: DashboardConfig, entered_token: str) -> str | None:
    """Prefer the entered token, otherwise fall back to the configured token."""
    cleaned_token = entered_token.strip()
    if cleaned_token:
        return cleaned_token
    return config.admin_token


def _render_auth_gate(config: DashboardConfig) -> None:
    """Render the local admin-token gate and validate via `GET /admin/providers`."""
    st.title("GateKeeper")
    st.subheader("Admin Dashboard")
    st.write("Enter an admin token to unlock the dashboard. If left blank, the dashboard uses `ADMIN_TOKEN` from its env when available.")
    st.caption(f"Gateway target: `{config.gateway_url}`")

    with st.form("admin-auth"):
        entered_token = st.text_input("Admin token", type="password")
        submitted = st.form_submit_button("Connect")

    if not submitted:
        return

    token = _candidate_token(config, entered_token)
    if token is None:
        st.warning("No admin token is available yet. Set `ADMIN_TOKEN` in the dashboard env or enter it manually.")
        return

    try:
        AdminApiClient(gateway_url=config.gateway_url, admin_token=token).validate_token()
    except (AdminTokenNotConfiguredError, AdminUnauthorizedError, GatewayUnavailableError) as exc:
        clear_auth()
        render_api_error(exc)
        return

    remember_auth(token, config.gateway_url)
    st.rerun()


def _render_authenticated_ui() -> None:
    """Render the navigation sidebar and route to the selected page."""
    pages = [
        st.Page("pages/01_overview.py", title="Overview"),
        st.Page("pages/02_keys.py", title="Keys"),
        st.Page("pages/03_models.py", title="Models"),
        st.Page("pages/04_analytics.py", title="Analytics"),
    ]

    with st.sidebar:
        st.title("Navigation")
        selected_page = st.navigation(pages)
        if st.button("Sign out"):
            clear_auth()
            st.rerun()

    selected_page.run()


def main() -> None:
    """Boot the Streamlit app, enforce the admin gate, then route to the selected page."""
    st.set_page_config(page_title="GateKeeper Dashboard", page_icon="🧩", layout="wide")
    config = load_dashboard_config()

    if not is_authenticated():
        _render_auth_gate(config)
        return

    _render_authenticated_ui()


if __name__ == "__main__":
    main()
