"""Streamlit entrypoint for the standalone GateKeeper dashboard."""

from __future__ import annotations

import streamlit as st

from api_client import (
    AdminApiClient,
    AdminApiError,
    AdminTokenNotConfiguredError,
    AdminUnauthorizedError,
    GatewayUnavailableError,
    SetupAlreadyDoneError,
    bootstrap_admin_token,
    fetch_setup_status,
)
from config import DashboardConfig, load_dashboard_config
from session import clear_auth, is_authenticated, remember_auth, render_api_error

_SETUP_TOKEN_KEY = "setup_generated_token"


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


def _needs_setup(config: DashboardConfig) -> bool:
    """Return whether to show the first-run setup screen.

    A freshly generated key still pending display takes priority. Otherwise ask
    the gateway; if it is unreachable, fall back to the normal sign-in gate
    (which surfaces the connection error when the user tries to connect).
    """
    if st.session_state.get(_SETUP_TOKEN_KEY):
        return True
    try:
        return fetch_setup_status(config.gateway_url)
    except AdminApiError:
        return False


def _render_setup_screen(config: DashboardConfig) -> None:
    """First-run welcome: generate the sole admin access key and show it once."""
    st.title("Welcome to GateKeeper")

    token = st.session_state.get(_SETUP_TOKEN_KEY)
    if token:
        st.success("Your admin access key has been generated and saved to the gateway's `.env`.")
        st.code(token, language=None)
        st.warning(
            "This is your **only** access key. Copy and store it securely now — "
            "it will not be shown again."
        )
        if st.button("I've saved it — continue to sign-in"):
            st.session_state.pop(_SETUP_TOKEN_KEY, None)
            st.rerun()
        return

    st.write(
        "First run detected — no admin key is configured yet. Generate one to "
        "secure the dashboard and the `/admin` API. It is written to the gateway's "
        "`.env` and required for every login from now on."
    )
    st.caption(f"Gateway target: `{config.gateway_url}`")

    if st.button("Generate my access key"):
        try:
            new_token = bootstrap_admin_token(config.gateway_url)
        except (SetupAlreadyDoneError, GatewayUnavailableError, AdminApiError) as exc:
            render_api_error(exc)
            return
        st.session_state[_SETUP_TOKEN_KEY] = new_token
        st.rerun()


def _render_authenticated_ui() -> None:
    """Render the navigation sidebar and route to the selected page."""
    pages = [
        st.Page("pages/01_overview.py", title="Overview"),
        st.Page("pages/02_keys.py", title="Keys"),
        st.Page("pages/03_models.py", title="Models"),
        st.Page("pages/04_analytics.py", title="Analytics"),
        st.Page("pages/05_docs.py", title="Docs"),
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

    if is_authenticated():
        _render_authenticated_ui()
        return

    if _needs_setup(config):
        _render_setup_screen(config)
        return

    _render_auth_gate(config)


if __name__ == "__main__":
    main()
