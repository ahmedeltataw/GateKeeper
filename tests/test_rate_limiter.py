"""Tests for the token-bucket rate limiter."""

from __future__ import annotations

import pytest

from src.core import rate_limiter
from src.core.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_allow_uses_provider_defaults():
    assert await rate_limiter.allow("openrouter")


@pytest.mark.parametrize(
    ("limits", "allowed_calls"),
    [
        ({"rpm": 2, "rpd": 10}, 2),
        ({"concurrent": 1}, 1),
        ({"neurons": 1}, 1),
        ({"rps": 1}, 1),
    ],
)
def test_bucket_allows_up_to_quota_then_blocks(limits, allowed_calls):
    bucket = TokenBucket(limits)
    for _ in range(allowed_calls):
        assert bucket.allow()
    assert not bucket.allow()


@pytest.mark.asyncio
async def test_cooldown_blocks_provider():
    rate_limiter.cooldown("gemini", 60)
    assert await rate_limiter.allow("gemini") is False


@pytest.mark.asyncio
async def test_disable_permanently_blocks_provider():
    rate_limiter.disable("groq")
    assert await rate_limiter.allow("groq") is False


def test_bucket_state_roundtrip():
    bucket = TokenBucket({"rpm": 5, "rpd": 10})
    bucket.tokens_minute = 3
    bucket.tokens_day = 7
    data = bucket.to_dict()
    restored = TokenBucket.from_dict(data)
    assert restored.tokens_minute == 3
    assert restored.tokens_day == 7
    assert restored.limits == bucket.limits
