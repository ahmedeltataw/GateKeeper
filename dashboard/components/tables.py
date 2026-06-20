"""Pure render helper for displaying model registry data as a table.

This module contains no business logic — it transforms typed data into a
Streamlit dataframe widget.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ModelInfo


def render_model_table(models: list[ModelInfo]) -> None:
    """Render a dataframe of registered models from the gateway registry."""
    if not models:
        st.caption("No models are registered yet.")
        return

    rows = []
    for model in models:
        rows.append(
            {
                "ID": model.id,
                "Name": model.display_name,
                "Provider": model.provider_id,
                "Strength": model.strength,
                "Category": model.category,
                "Context": model.context_window,
                "Max Output": model.max_output_tokens,
                "Status": model.status,
                "Enabled": model.enabled,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
