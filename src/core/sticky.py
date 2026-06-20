"""Sticky session cache.

A session keeps a conversation pinned to the first successful model for a
configurable TTL (default 30 minutes).  The session id is derived from the
``X-Session-Id`` request header when provided, otherwise from a deterministic
hash of the first system and user messages in the conversation.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from src.core.config_loader import get_config

_session_cache: dict[str, dict[str, Any]] = {}


def _ttl() -> int:
    return get_config().sticky_sessions.ttl


def _enabled() -> bool:
    return get_config().sticky_sessions.enabled


def _derive_from_messages(messages: list[dict[str, Any]]) -> str:
    """Derive a stable session id from the first system and user messages."""
    parts: list[str] = []
    for message in messages:
        if message.get("role") in ("system", "user"):
            parts.append(f"{message.get('role')}:{message.get('content', '')}")
        if len(parts) >= 2:
            break
    content = "|".join(parts)
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def derive_session_id(messages: list[dict[str, Any]], header: str | None = None) -> str:
    """Return a session id from the client header or the conversation content."""
    if header:
        return hashlib.sha256(header.encode()).hexdigest()[:32]
    return _derive_from_messages(messages)


def get_sticky_model(session_id: str) -> str | None:
    """Return the pinned model for a session if still within TTL."""
    if not _enabled():
        return None
    entry = _session_cache.get(session_id)
    if entry is None:
        return None
    if time.time() - entry["time"] > _ttl():
        _session_cache.pop(session_id, None)
        return None
    return entry["model_id"]


def set_sticky_model(session_id: str, model_id: str) -> None:
    """Pin a model to a session, refreshing the timestamp."""
    if not _enabled():
        return
    _session_cache[session_id] = {"model_id": model_id, "time": time.time()}


def clear_session(session_id: str) -> None:
    """Remove a session from the cache."""
    _session_cache.pop(session_id, None)
