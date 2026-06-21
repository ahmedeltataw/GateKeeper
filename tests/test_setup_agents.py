"""Tests for the agent-integration wizard's pure writer helpers."""

from __future__ import annotations

from scripts.agent_writers import (
    MARK_BEGIN,
    MARK_END,
    hermes_block,
    opencode_config_merge,
    shell_env_block,
    upsert_marker_block,
)

_V1 = "http://127.0.0.1:8000/v1"
_KEY = "sk-local"


def test_marker_block_idempotent():
    block = hermes_block(_V1, _KEY)
    once = upsert_marker_block("", block)
    twice = upsert_marker_block(once, hermes_block(_V1, "rotated-key"))
    # Only one GateKeeper block ever exists.
    assert twice.count(MARK_BEGIN) == 1
    assert twice.count(MARK_END) == 1
    # The block was updated to the new key, not duplicated.
    assert "rotated-key" in twice
    assert "sk-local" not in twice


def test_upsert_preserves_user_content():
    user = "custom_providers:\n  myown:\n    base_url: http://x\n"
    result = upsert_marker_block(user, hermes_block(_V1, _KEY))
    assert "myown" in result
    assert MARK_BEGIN in result


def test_opencode_merge_preserves_existing_and_adds_provider():
    existing = {"theme": "dark", "provider": {"openai": {"options": {"apiKey": "x"}}}}
    merged = opencode_config_merge(existing, _V1, _KEY)
    assert merged["theme"] == "dark"            # untouched
    assert "openai" in merged["provider"]        # untouched
    gk = merged["provider"]["gatekeeper"]
    assert gk["options"]["baseURL"] == _V1
    assert gk["options"]["apiKey"] == _KEY


def test_opencode_merge_from_empty():
    merged = opencode_config_merge(None, _V1, _KEY)
    assert merged["provider"]["gatekeeper"]["options"]["baseURL"] == _V1


def test_shell_env_block_anthropic_strips_v1():
    block = shell_env_block(_V1, _KEY, anthropic=True)
    assert "ANTHROPIC_BASE_URL=http://127.0.0.1:8000\n" in block
    assert "/v1" not in block.split("ANTHROPIC_BASE_URL=")[1].split("\n")[0]


def test_shell_env_block_openai_keeps_v1():
    block = shell_env_block(_V1, _KEY)
    assert "OPENAI_BASE_URL=http://127.0.0.1:8000/v1" in block
