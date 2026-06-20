"""Dashboard models page showing the full gateway model registry."""

from __future__ import annotations

import streamlit as st

from components.tables import render_model_table
from session import render_api_error, require_auth


def main() -> None:
    """Render the models registry page with a dataframe table."""
    st.title("Model Registry")
    client = require_auth()

    try:
        models = client.get_models()
        st.write(f"{len(models)} models registered.")
        render_model_table(models)
    except Exception as exc:  # noqa: BLE001 — mapped to a friendly message, real bugs re-raise
        render_api_error(exc)


main()
