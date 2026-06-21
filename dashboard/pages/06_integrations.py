"""Dashboard Integrations page — copy-paste agent setup + connection test.

Implements UX_INTEGRATION_AND_ONBOARDING.md §4.5: the GUI counterpart to
``GET /v1/connection-info`` and ``scripts/setup_agents.py``. It shows the
gateway's own connection facts, generates a per-agent snippet, and offers a
"Test Connection" button that sends a real tiny completion.
"""

from __future__ import annotations

import streamlit as st

from api_client import fetch_agent_snippet, fetch_connection_info, test_connection
from session import get_gateway_url, render_api_error, require_auth

_AGENTS = ("opencode", "claude-code", "hermes", "cursor", "continue-dev", "custom-script")


def main() -> None:
    st.title("Integrations")
    st.caption("Connect your agent to GateKeeper in under 30 seconds.")
    require_auth()  # defense-in-depth; the snippets themselves use public endpoints

    gateway_url = get_gateway_url()
    if not gateway_url:
        st.warning("No gateway URL in this session. Sign in from the main page first.")
        st.stop()

    try:
        info = fetch_connection_info(gateway_url)
    except Exception as exc:  # noqa: BLE001 — friendly mapping, real bugs re-raise
        render_api_error(exc)
        return

    gw = info.get("gateway", {})
    api_key = gw.get("api_key")

    col1, col2 = st.columns(2)
    col1.metric("Base URL", gw.get("base_url", "—"))
    col2.metric("Auth", "enabled" if gw.get("auth_enabled") else "disabled")
    if api_key:
        st.code(f"API key: {api_key}", language="text")
    else:
        st.info("API key is withheld (gateway is not on a loopback bind). Read it from the server config.")

    sample_ids = info.get("models", {}).get("sample_ids", [])
    if sample_ids:
        st.write("**Sample model ids:** " + ", ".join(f"`{m}`" for m in sample_ids))

    st.divider()
    st.subheader("Per-agent setup")
    agent = st.selectbox("Choose your agent", _AGENTS, index=0)
    fmt = st.radio("Format", ("text", "json"), horizontal=True)

    try:
        snippet = fetch_agent_snippet(gateway_url, agent, fmt)
    except Exception as exc:  # noqa: BLE001
        render_api_error(exc)
        return

    if fmt == "text":
        st.code(snippet.get("snippet", ""), language="bash")
    else:
        st.json(snippet.get("config", {}))

    st.divider()
    st.subheader("Test connection")
    st.write("Sends a tiny `model: auto` completion to verify an agent could reach the gateway.")
    if st.button("Run test", type="primary"):
        if not api_key:
            st.error("No API key available in this session to test with.")
        else:
            with st.spinner("Calling /v1/chat/completions…"):
                result = test_connection(gateway_url, api_key)
            if result["ok"]:
                st.success(result["detail"])
            else:
                st.error(result["detail"])


main()
