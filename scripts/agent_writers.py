"""Pure, testable helpers for the agent-integration wizard (setup_agents.py).

All filesystem and network effects live in ``setup_agents.py``; everything here
is a pure function so the marker/merge logic can be unit-tested without touching
disk. The guiding safety rule (UX doc §4.3): never clobber a user's config —
either merge structurally (JSON) or confine edits to a clearly delimited marker
block that can be re-written idempotently.
"""

from __future__ import annotations

import json
from typing import Any

MARK_BEGIN = "GATEKEEPER_BEGIN"
MARK_END = "GATEKEEPER_END"


def marker_block(body: str, *, comment: str = "#") -> str:
    """Wrap ``body`` in delimited begin/end markers using ``comment`` syntax."""
    return f"{comment} {MARK_BEGIN}\n{body.rstrip()}\n{comment} {MARK_END}"


def upsert_marker_block(existing: str, block: str, *, comment: str = "#") -> str:
    """Insert ``block`` into ``existing``, replacing any prior GateKeeper block.

    Idempotent: running it twice yields the same file. Existing user content
    outside the markers is preserved verbatim.
    """
    begin = f"{comment} {MARK_BEGIN}"
    end = f"{comment} {MARK_END}"
    if begin in existing and end in existing:
        pre = existing.split(begin, 1)[0].rstrip("\n")
        post = existing.split(end, 1)[1].lstrip("\n")
        parts = [p for p in (pre, block, post) if p]
        return "\n\n".join(parts) + "\n"
    base = existing.rstrip("\n")
    return (f"{base}\n\n{block}\n" if base else f"{block}\n")


# --------------------------------------------------------------------------- #
# Per-agent content builders                                                   #
# --------------------------------------------------------------------------- #
def opencode_config_merge(
    existing: dict[str, Any] | None, base_url: str, api_key: str
) -> dict[str, Any]:
    """Merge a GateKeeper OpenAI-compatible provider into an OpenCode config."""
    config = dict(existing or {})
    providers = dict(config.get("provider", {}))
    providers["gatekeeper"] = {
        "npm": "@ai-sdk/openai-compatible",
        "options": {"baseURL": base_url, "apiKey": api_key},
    }
    config["provider"] = providers
    return config


def hermes_block(base_url: str, api_key: str) -> str:
    """Return a marker-wrapped Hermes ``custom_providers`` YAML block."""
    body = (
        "custom_providers:\n"
        "  gatekeeper:\n"
        f"    base_url: {base_url}\n"
        f"    api_key: {api_key}"
    )
    return marker_block(body, comment="#")


def shell_env_block(base_url: str, api_key: str, *, anthropic: bool = False) -> str:
    """Return a marker-wrapped shell export block (OpenAI or Anthropic vars)."""
    if anthropic:
        # Anthropic base url has no /v1 suffix.
        root = base_url[:-3] if base_url.endswith("/v1") else base_url
        body = (
            f"export ANTHROPIC_BASE_URL={root}\n"
            f"export ANTHROPIC_API_KEY={api_key}"
        )
    else:
        body = (
            f"export OPENAI_BASE_URL={base_url}\n"
            f"export OPENAI_API_KEY={api_key}"
        )
    return marker_block(body, comment="#")


def opencode_config_text(config: dict[str, Any]) -> str:
    """Serialise an OpenCode config dict to pretty JSON."""
    return json.dumps(config, indent=2) + "\n"
