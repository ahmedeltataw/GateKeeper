"""Shared session, auth, and client helpers for the dashboard.

``app.py`` routes pages with ``st.navigation`` after the auth gate, but each
page also calls ``require_auth`` as defense-in-depth. Centralizing the session
keys, the authenticated API client, and error rendering here keeps ``app.py``
and every page in ``pages/`` behaving identically.
"""

from __future__ import annotations

import streamlit as st

from api_client import (
    AdminApiClient,
    AdminApiError,
    AdminTokenNotConfiguredError,
    AdminUnauthorizedError,
    GatewayUnavailableError,
    SetupAlreadyDoneError,
)

_AUTHENTICATED_FLAG = "dashboard_authenticated"
_ACTIVE_TOKEN = "dashboard_admin_token"
_GATEWAY_URL_KEY = "dashboard_gateway_url"


def is_authenticated() -> bool:
    """Return whether this Streamlit session has passed the admin token gate."""
    return bool(st.session_state.get(_AUTHENTICATED_FLAG))


def remember_auth(token: str, gateway_url: str) -> None:
    """Persist successful admin auth in the current Streamlit session."""
    st.session_state[_AUTHENTICATED_FLAG] = True
    st.session_state[_ACTIVE_TOKEN] = token
    st.session_state[_GATEWAY_URL_KEY] = gateway_url


def clear_auth() -> None:
    """Remove admin auth state from the current Streamlit session."""
    st.session_state.pop(_AUTHENTICATED_FLAG, None)
    st.session_state.pop(_ACTIVE_TOKEN, None)
    st.session_state.pop(_GATEWAY_URL_KEY, None)


def get_client() -> AdminApiClient:
    """Build an authenticated API client from the session token and gateway URL."""
    return AdminApiClient(
        gateway_url=st.session_state.get(_GATEWAY_URL_KEY, ""),
        admin_token=st.session_state.get(_ACTIVE_TOKEN, ""),
    )


def get_gateway_url() -> str:
    """Return the gateway base URL remembered for this session (or empty)."""
    return st.session_state.get(_GATEWAY_URL_KEY, "")


def require_auth() -> AdminApiClient:
    """Stop the page with a sign-in hint when unauthenticated, else return a client."""
    if not is_authenticated():
        st.warning("Please sign in from the main page before opening dashboard pages.")
        st.stop()
    return get_client()


def render_api_error(error: Exception) -> None:
    """Map gateway/auth exceptions to friendly UI messages without tracebacks."""
    if isinstance(error, AdminTokenNotConfiguredError):
        st.error("The gateway admin token is not configured. Set `ADMIN_TOKEN` in the gateway `.env` and restart it.")
        return
    if isinstance(error, AdminUnauthorizedError):
        st.error("The admin token was rejected. Sign out and reconnect with a valid token.")
        return
    if isinstance(error, GatewayUnavailableError):
        st.error("The gateway is unavailable right now. Start it first, then refresh.")
        return
    if isinstance(error, SetupAlreadyDoneError):
        st.error("An admin key already exists. Sign in instead.")
        return
    if isinstance(error, AdminApiError):
        st.error("The gateway returned an unexpected error. Please try again.")
        return
    raise error
