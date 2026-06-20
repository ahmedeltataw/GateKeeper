"""Dashboard keys page for viewing, adding, and deleting provider API keys.

Keys are always rendered masked (``●●●●●``). The add-key form uses a password
input and the submitted value is never echoed back or logged after submit.
"""

from __future__ import annotations

import streamlit as st

from api_client import AdminApiClient
from session import render_api_error, require_auth


def _render_key_list(client: AdminApiClient) -> None:
    """Display existing keys and a delete button per row."""
    keys = client.get_keys()
    if not keys:
        st.caption("No provider keys stored yet. Add one below.")
        return

    st.subheader("Stored Keys")
    for key in keys:
        cols = st.columns([3, 2, 2, 1])
        cols[0].write(key.provider)
        cols[1].write(key.masked)
        cols[2].write(key.health_status)
        if cols[3].button("Delete", key=f"delete_{key.provider}"):
            client.delete_key(key.provider)
            st.rerun()


def _render_add_key_form(client: AdminApiClient) -> None:
    """Show a form to add a new provider key."""
    st.subheader("Add Key")
    with st.form("add-key-form"):
        provider = st.text_input("Provider ID")
        api_key = st.text_input("API Key", type="password")
        submitted = st.form_submit_button("Add Key")

    if not submitted:
        return
    if not provider.strip():
        st.error("Provider ID is required.")
        return
    if not api_key:
        st.error("API Key is required.")
        return
    client.set_key(provider.strip(), api_key)
    st.rerun()


def main() -> None:
    """Render the keys management page with list, add, and delete actions."""
    st.title("Provider Keys")
    client = require_auth()

    try:
        _render_key_list(client)
        st.divider()
        _render_add_key_form(client)
    except Exception as exc:  # noqa: BLE001 — mapped to a friendly message, real bugs re-raise
        render_api_error(exc)


main()
