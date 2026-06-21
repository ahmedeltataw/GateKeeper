"""Dashboard models page showing the full gateway model registry."""

from __future__ import annotations

import streamlit as st

from components.tables import render_model_table
from session import render_api_error, require_auth


def main() -> None:
    """Render the models registry page with a dataframe table + runtime controls."""
    st.title("Model Registry")
    client = require_auth()

    try:
        models = client.get_models()
        st.write(f"{len(models)} models registered.")
        render_model_table(models)
    except Exception as exc:  # noqa: BLE001 — mapped to a friendly message, real bugs re-raise
        render_api_error(exc)
        return

    st.divider()
    st.subheader("Runtime controls")
    st.caption("Enable / disable a model or clear its circuit breaker — no restart.")
    model_ids = sorted(m.id for m in models)
    chosen = st.selectbox("Model", model_ids)
    c1, c2, c3 = st.columns(3)
    try:
        if c1.button("Enable", use_container_width=True):
            client.enable_model(chosen)
            st.success(f"Enabled {chosen} (breaker reset).")
        if c2.button("Disable", use_container_width=True):
            client.disable_model(chosen)
            st.warning(f"Disabled {chosen}.")
        if c3.button("Retry (un-quarantine)", use_container_width=True):
            client.retry_model(chosen)
            st.success(f"Cleared breaker for {chosen}.")
    except Exception as exc:  # noqa: BLE001
        render_api_error(exc)

    st.divider()
    st.subheader("Quarantined models")
    try:
        q = client.get_quarantine()
    except Exception as exc:  # noqa: BLE001
        render_api_error(exc)
        return
    rows = q.get("quarantined", [])
    if not rows:
        st.success("No quarantined models. 🎉")
    else:
        st.dataframe(rows, use_container_width=True)
    probe = q.get("last_probe") or {}
    if probe:
        st.caption(
            f"Last boot probe: {probe.get('healthy', 0)} healthy / "
            f"{probe.get('failed', 0)} failed / {probe.get('blacklisted', 0)} blacklisted "
            f"of {probe.get('probed', 0)} probed."
        )


main()
