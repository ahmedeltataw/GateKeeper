"""Exact-match response cache with TTL and size eviction.

The cache key is a hash of the model, messages, temperature, and max_tokens so
that identical requests within the TTL window reuse the same upstream response.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

from src.core.config_loader import get_config
from src.core.types import ChatResponse

_cache_hits = 0


def _enabled() -> bool:
    return get_config().cache.enabled


def _ttl() -> int:
    return get_config().cache.ttl


def _max_size() -> int:
    return get_config().cache.max_size


def _make_key(
    model_id: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> str:
    content = json.dumps(
        {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
    )
    return hashlib.md5(content.encode("utf-8")).hexdigest()


class _CacheEntry:
    def __init__(self, response: ChatResponse, expires_at: float) -> None:
        self.response = response
        self.expires_at = expires_at


_store: OrderedDict[str, _CacheEntry] = OrderedDict()


def get(
    model_id: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> ChatResponse | None:
    """Return a cached response if present and not expired."""
    global _cache_hits
    if not _enabled():
        return None

    key = _make_key(model_id, messages, temperature, max_tokens)
    entry = _store.get(key)
    if entry is None:
        return None
    if time.time() > entry.expires_at:
        _store.pop(key, None)
        return None

    _store.move_to_end(key)
    _cache_hits += 1
    return entry.response


def set(
    model_id: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    response: ChatResponse,
) -> None:
    """Store a response in the cache."""
    if not _enabled():
        return

    key = _make_key(model_id, messages, temperature, max_tokens)
    entry = _CacheEntry(response, time.time() + _ttl())
    _store[key] = entry
    _store.move_to_end(key)

    while len(_store) > _max_size():
        _store.popitem(last=False)


def get_hits() -> int:
    """Return the number of cache hits since startup."""
    return _cache_hits
