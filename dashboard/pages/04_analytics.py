"""Analytics — client-facing Usage & Limits view.

Fetches ``GET /v1/usage`` with the client's own API key and renders one card per
contracted model with animated, dark-mode progress bars whose color tracks
consumption (green < 70%, yellow < 90%, red >= 90%). The card list is driven
entirely by the API response, so it always reflects the client's current plan:
two contracted models -> two cards; a backend plan change shows up on the next
refresh.
"""

from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from config import load_dashboard_config
from session import require_auth  # keeps the page behind the dashboard gate

_REQUEST_TIMEOUT_SECONDS = 10.0
_CLIENT_KEY_STATE = "client_api_key"

# Dark-mode palette.
_GREEN = "#22c55e"
_AMBER = "#f59e0b"
_RED = "#ef4444"
_TRACK = "#1f2937"
_MUTED = "#9ca3af"
_CARD_BG = "#111827"
_CARD_BORDER = "#1f2937"


# --- data ------------------------------------------------------------------

def _gateway_url() -> str:
    """Resolve the gateway base URL from the session, falling back to config."""
    url = st.session_state.get("dashboard_gateway_url")
    if url:
        return str(url).rstrip("/")
    return load_dashboard_config().gateway_url.rstrip("/")


def _fetch_usage(api_key: str) -> dict[str, Any] | None:
    """Call ``GET /v1/usage`` with the client key.

    Returns the usage document, or ``None`` for any auth/network/HTTP failure so
    the caller can show a friendly message instead of a traceback.
    """
    try:
        with httpx.Client(base_url=_gateway_url(), timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = client.get(
                "/v1/usage", headers={"Authorization": f"Bearer {api_key}"}
            )
    except httpx.RequestError:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


# --- presentation helpers --------------------------------------------------

def _bar_color(percent: float, limit: int) -> str:
    """Traffic-light color for a usage percentage. Unlimited (0) stays green."""
    if limit <= 0:
        return _GREEN
    if percent >= 90:
        return _RED
    if percent >= 70:
        return _AMBER
    return _GREEN


def _fmt(n: int) -> str:
    """Compact number: 1500 -> 1.5K, 2_000_000 -> 2.0M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def _limit_label(limit: int) -> str:
    """Render a limit, treating 0 as unlimited."""
    return "∞" if limit <= 0 else _fmt(limit)


def _progress_bar_html(label: str, used: int, limit: int, percent: float) -> str:
    """Return HTML for one animated, rounded progress bar.

    The string is deliberately free of leading whitespace/newlines: indented
    lines would be parsed by Markdown as a code block and shown as raw text.
    """
    color = _bar_color(percent, limit)
    width = min(100.0, percent) if limit > 0 else 0.0
    pct_text = "—" if limit <= 0 else f"{percent:.0f}%"
    return (
        '<div style="margin:8px 0 14px 0;">'
        '<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'font-size:0.82rem;color:{_MUTED};margin-bottom:4px;">'
        f"<span>{label}</span>"
        f"<span>{_fmt(used)} / {_limit_label(limit)}&nbsp;"
        f'<b style="color:{color};">{pct_text}</b></span></div>'
        f'<div style="background:{_TRACK};border-radius:999px;height:12px;width:100%;'
        'overflow:hidden;box-shadow:inset 0 1px 2px rgba(0,0,0,.4);">'
        f'<div style="background:linear-gradient(90deg,{color}cc,{color});height:12px;'
        f"width:{width}%;border-radius:999px;"
        'transition:width .6s cubic-bezier(.4,0,.2,1);"></div></div></div>'
    )


def render_progress_bar(label: str, used: int, limit: int, percent: float) -> None:
    """Render one usage bar inline. Reusable for any model or metric.

    Always renders via ``st.markdown(..., unsafe_allow_html=True)`` with
    whitespace-free HTML, so the bar can never regress into raw text.
    """
    st.markdown(
        _progress_bar_html(label, used, limit, percent), unsafe_allow_html=True
    )


def _tier_badge(tier: str) -> str:
    """Small colored pill marking a model's tier."""
    color = "#a855f7" if tier == "dedicated" else "#3b82f6"
    return (
        f'<span style="background:{color}22;color:{color};font-size:0.7rem;'
        f'padding:2px 9px;border-radius:999px;border:1px solid {color}55;'
        f'margin-left:8px;vertical-align:middle;">{tier}</span>'
    )


def _render_model_card(model: dict[str, Any]) -> None:
    """Render one model's usage card inside a bordered dark container."""
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:1.05rem;font-weight:600;margin-bottom:2px;">'
            f'{model["name"]}{_tier_badge(model.get("tier", "auto"))}</div>'
            f'<div style="color:{_MUTED};font-size:0.75rem;margin-bottom:8px;">'
            f'<code>{model["id"]}</code></div>',
            unsafe_allow_html=True,
        )
        render_progress_bar(
            "Tokens", model["usage"]["tokens"],
            model["limit"]["tokens"], model["percent"]["tokens"],
        )
        render_progress_bar(
            "Requests", model["usage"]["requests"],
            model["limit"]["requests"], model["percent"]["requests"],
        )


def _render_account_summary(doc: dict[str, Any]) -> None:
    """Render the plan header and account-level totals."""
    quota, totals, pct = doc["quota"], doc["totals"], doc["percent"]

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<h3 style="margin:0;">👤 {doc["client_id"]}</h3>'
        f'<span style="background:#3b82f622;color:#3b82f6;padding:3px 12px;'
        f'border-radius:999px;border:1px solid #3b82f655;font-size:0.85rem;">'
        f'{doc["plan"].upper()} · {doc["period"]}</span></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    col1.metric("Tokens today", f"{_fmt(totals['tokens'])} / {_limit_label(quota['tokens'])}")
    col2.metric("Requests today", f"{_fmt(totals['requests'])} / {_limit_label(quota['requests'])}")

    render_progress_bar("Account tokens", totals["tokens"], quota["tokens"], pct["tokens"])
    render_progress_bar("Account requests", totals["requests"], quota["requests"], pct["requests"])


def _render_welcome(message: str) -> None:
    """Polite, non-technical empty/error state."""
    st.markdown(
        f'<div style="text-align:center;padding:48px 24px;background:{_CARD_BG};'
        f'border:1px dashed {_CARD_BORDER};border-radius:16px;margin-top:8px;">'
        f'<div style="font-size:2.4rem;">📊</div>'
        f'<h3 style="margin:8px 0 4px 0;">Welcome to your usage dashboard</h3>'
        f'<p style="color:{_MUTED};max-width:480px;margin:0 auto;">{message}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# --- page ------------------------------------------------------------------

def main() -> None:
    """Render the client Usage & Limits page."""
    require_auth()
    st.title("Usage & Limits")

    top = st.columns([4, 1])
    with top[0]:
        api_key = st.text_input(
            "Your API key",
            type="password",
            value=st.session_state.get(_CLIENT_KEY_STATE, ""),
            placeholder="sk-...",
            help="Your client key. The dashboard calls /v1/usage with it.",
        )
    with top[1]:
        st.write("")  # vertical spacer to align the button with the input
        st.write("")
        refreshed = st.button("🔄 Refresh", width="stretch")

    st.session_state[_CLIENT_KEY_STATE] = api_key

    if not api_key:
        _render_welcome("Enter your API key above to see your live consumption per model.")
        return

    if refreshed:
        st.rerun()  # force a fresh fetch so numbers feel live after using a model

    doc = _fetch_usage(api_key)
    if doc is None:
        _render_welcome(
            "We couldn't load your usage right now. Check your API key, or try "
            "Refresh in a moment — the gateway may still be starting."
        )
        return

    _render_account_summary(doc)
    st.divider()

    models = doc.get("models", [])
    if not models:
        _render_welcome(
            "You're all set! No requests recorded yet today — send your first "
            "request through the gateway and your numbers will appear here."
        )
        return

    st.markdown("##### Per-model consumption")
    # Two-column responsive grid; the count follows the plan automatically.
    columns = st.columns(2)
    for index, model in enumerate(models):
        with columns[index % 2]:
            _render_model_card(model)


main()
