"""Token-bucket rate limiter with per-provider buckets and state persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.core.config_loader import get_config

# Per-provider defaults from IMPLEMENTATION_PLAN.md §8.
RATE_LIMITS: dict[str, dict[str, Any]] = {
    "openrouter": {"rpm": 20, "rpd": 50},
    "gemini": {"rpm": 15, "rpd": 1500},
    "groq": {"rpm": 30, "rpd": 1000, "tpm": 6000},
    "mistral": {"rps": 1, "tpm": 500_000},
    "github_models": {"rpm": 15, "rpd": 150},
    "nvidia": {"rpm": 40, "rpd": 1000},
    "cerebras": {"rpm": 30, "rpd": 14_400},
    "cloudflare": {"neurons": 10_000},
    "zai": {"concurrent": 1},
    "huggingface": {"rpm": 10, "rpd": 100},
    "aion": {"rpm": 15, "rpd": 20, "tpd": 20_000},
    "cohere": {"rpm": 20, "rpd": 33},
}


class TokenBucket:
    """Tracks request/token budgets for a single provider."""

    def __init__(self, limits: dict[str, Any]) -> None:
        self.limits = limits
        self.tokens_minute = float(limits.get("rpm", 0))
        self.tokens_day = float(limits.get("rpd", 0))
        self.tokens_tpm = float(limits.get("tpm", 0))
        self.tokens_tpd = float(limits.get("tpd", 0))
        self.tokens_second = float(limits.get("rps", 0))
        self.tokens_neurons = float(limits.get("neurons", 0))
        self.concurrent_max = int(limits.get("concurrent", 0))
        self.concurrent_used = 0
        self.last_refill = time.time()
        self.cooldown_until: float | None = None
        self.disabled = False

    def refill(self) -> None:
        """Refill buckets according to their time windows."""
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed >= 60:
            self.tokens_minute = float(self.limits.get("rpm", 0))
            self.tokens_tpm = float(self.limits.get("tpm", 0))
            self.concurrent_used = 0
            self.last_refill = now
        if elapsed >= 1:
            self.tokens_second = float(self.limits.get("rps", 0))
        if elapsed >= 86400:
            self.tokens_day = float(self.limits.get("rpd", 0))
            self.tokens_tpd = float(self.limits.get("tpd", 0))
            self.tokens_neurons = float(self.limits.get("neurons", 0))

    def is_cooled_down(self) -> bool:
        if self.disabled:
            return True
        if self.cooldown_until is None:
            return False
        if time.time() >= self.cooldown_until:
            self.cooldown_until = None
            return False
        return True

    def allow(self) -> bool:
        """Check and reserve one request unit across all configured buckets."""
        self.refill()
        if self.is_cooled_down():
            return False

        if self.limits.get("rpm", 0) and self.tokens_minute < 1:
            return False
        if self.limits.get("rpd", 0) and self.tokens_day < 1:
            return False
        if self.limits.get("tpm", 0) and self.tokens_tpm < 1:
            return False
        if self.limits.get("tpd", 0) and self.tokens_tpd < 1:
            return False
        if self.limits.get("rps", 0) and self.tokens_second < 1:
            return False
        if self.limits.get("neurons", 0) and self.tokens_neurons < 1:
            return False
        if self.concurrent_max and self.concurrent_used >= self.concurrent_max:
            return False

        self._consume_one()
        return True

    def _consume_one(self) -> None:
        if self.limits.get("rpm", 0):
            self.tokens_minute -= 1
        if self.limits.get("rpd", 0):
            self.tokens_day -= 1
        if self.limits.get("tpm", 0):
            self.tokens_tpm -= 1
        if self.limits.get("tpd", 0):
            self.tokens_tpd -= 1
        if self.limits.get("rps", 0):
            self.tokens_second -= 1
        if self.limits.get("neurons", 0):
            self.tokens_neurons -= 1
        if self.concurrent_max:
            self.concurrent_used += 1

    def consume_tokens(self, tokens: int) -> None:
        """Deduct generated tokens from the TPM budget if configured."""
        if self.limits.get("tpm", 0):
            self.tokens_tpm = max(0, self.tokens_tpm - tokens)
        if self.limits.get("tpd", 0):
            self.tokens_tpd = max(0, self.tokens_tpd - tokens)

    def cooldown(self, duration: int | None) -> None:
        """Apply a cooldown. ``None`` disables the provider permanently."""
        if duration is None:
            self.disabled = True
        else:
            self.cooldown_until = time.time() + duration

    def disable(self) -> None:
        """Permanently disable the provider."""
        self.disabled = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "limits": self.limits,
            "tokens_minute": self.tokens_minute,
            "tokens_day": self.tokens_day,
            "tokens_tpm": self.tokens_tpm,
            "tokens_tpd": self.tokens_tpd,
            "tokens_second": self.tokens_second,
            "tokens_neurons": self.tokens_neurons,
            "concurrent_used": self.concurrent_used,
            "last_refill": self.last_refill,
            "cooldown_until": self.cooldown_until,
            "disabled": self.disabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenBucket":
        bucket = cls(data.get("limits", {}))
        bucket.tokens_minute = float(data.get("tokens_minute", bucket.tokens_minute))
        bucket.tokens_day = float(data.get("tokens_day", bucket.tokens_day))
        bucket.tokens_tpm = float(data.get("tokens_tpm", bucket.tokens_tpm))
        bucket.tokens_tpd = float(data.get("tokens_tpd", bucket.tokens_tpd))
        bucket.tokens_second = float(data.get("tokens_second", bucket.tokens_second))
        bucket.tokens_neurons = float(data.get("tokens_neurons", bucket.tokens_neurons))
        bucket.concurrent_used = int(data.get("concurrent_used", 0))
        bucket.last_refill = float(data.get("last_refill", time.time()))
        bucket.cooldown_until = data.get("cooldown_until")
        bucket.disabled = bool(data.get("disabled", False))
        return bucket


_buckets: dict[str, TokenBucket] = {}


def _get_bucket(provider_id: str) -> TokenBucket:
    if provider_id not in _buckets:
        _buckets[provider_id] = TokenBucket(RATE_LIMITS.get(provider_id, {}))
    return _buckets[provider_id]


def _is_enabled() -> bool:
    return get_config().rate_limiter.enabled


def _state_path() -> Path:
    return Path(get_config().rate_limiter.state_file)


async def allow(provider_id: str, model_id: str = "") -> bool:
    """Check and reserve one request unit for the provider."""
    if not _is_enabled():
        return True
    return _get_bucket(provider_id).allow()


def consume(provider_id: str, tokens: int) -> None:
    """Deduct generated tokens from the provider's token budget."""
    if not _is_enabled():
        return
    _get_bucket(provider_id).consume_tokens(tokens)


def cooldown(provider_id: str, duration: int | None) -> None:
    """Apply a temporary or permanent cooldown to a provider."""
    _get_bucket(provider_id).cooldown(duration)


def disable(provider_id: str) -> None:
    """Permanently disable a provider."""
    _get_bucket(provider_id).disable()


async def save_state() -> None:
    """Persist bucket states to disk."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {pid: bucket.to_dict() for pid, bucket in _buckets.items()}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


async def load_state() -> None:
    """Load bucket states from disk."""
    path = _state_path()
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for provider_id, bucket_data in data.items():
        _buckets[provider_id] = TokenBucket.from_dict(bucket_data)
