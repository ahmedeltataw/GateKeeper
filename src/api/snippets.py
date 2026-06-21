"""Self-describing onboarding: connection info + per-agent config snippets.

Powers ``GET /v1/connection-info`` and ``GET /v1/agent-snippet``. The goal
(UX_INTEGRATION_AND_ONBOARDING.md) is that the gateway tells an agent how to
connect to it, so a user never hunts the README for env var names or model ids.

Security: the client ``api_key`` is only echoed when the gateway is bound to a
loopback address. On a LAN/public bind the value is withheld (returned as null
with a note) so a public ``/v1/connection-info`` cannot leak the key.
"""

from __future__ import annotations

from typing import Any

from src.core.config_loader import get_config
from src.core.registry import get_registry

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", ""})

# Display host: a 0.0.0.0 bind is not dialable, so advertise loopback for local
# use; a concrete LAN/public host is advertised as-is.
def _display_host(host: str) -> str:
    if host in _LOOPBACK_HOSTS or host == "0.0.0.0":
        return "127.0.0.1"
    return host


def _is_loopback(host: str) -> bool:
    return host in _LOOPBACK_HOSTS or host == "0.0.0.0"


def base_url(*, with_v1: bool = True) -> str:
    """Return the gateway base URL, optionally with the ``/v1`` suffix."""
    cfg = get_config().server
    root = f"http://{_display_host(cfg.host)}:{cfg.port}"
    return f"{root}/v1" if with_v1 else root


def _api_key() -> str | None:
    """Return the client api_key, or None when withheld on a non-loopback bind."""
    cfg = get_config()
    if not cfg.auth.enabled:
        return None
    if _is_loopback(cfg.server.host):
        return cfg.auth.api_key
    return None  # withheld: don't leak the key over a LAN/public bind


# --------------------------------------------------------------------------- #
# Agent snippet library                                                        #
# --------------------------------------------------------------------------- #
SUPPORTED_AGENTS = (
    "opencode",
    "claude-code",
    "hermes",
    "cursor",
    "continue-dev",
    "custom-script",
)


def _key_or_placeholder(key: str | None) -> str:
    return key if key is not None else "<YOUR_API_KEY>"


def _snippet_text(agent: str, v1: str, root: str, key: str | None) -> str:
    k = _key_or_placeholder(key)
    if agent == "opencode":
        return (
            f"export OPENAI_BASE_URL={v1}\n"
            f"export OPENAI_API_KEY={k}\n"
            f"opencode --model auto"
        )
    if agent == "claude-code":
        return (
            f"export ANTHROPIC_BASE_URL={root}\n"
            f"export ANTHROPIC_API_KEY={k}\n"
            f"claude --model auto\n"
            f"# If the Anthropic adapter misbehaves, use OpenAI provider mode "
            f"against {v1}."
        )
    if agent == "hermes":
        return (
            "# Add to your Hermes config.yaml custom providers:\n"
            "custom_providers:\n"
            "  gatekeeper:\n"
            f"    base_url: {v1}\n"
            f"    api_key: {k}\n"
            "# Then select gatekeeper/auto or gatekeeper/<model-id>."
        )
    if agent in ("cursor", "continue-dev"):
        return (
            f"# {agent}: Settings -> Custom OpenAI provider\n"
            f"Base URL: {v1}\n"
            f"API Key: {k}\n"
            f"Model: auto"
        )
    # custom-script
    return (
        "from openai import OpenAI\n"
        f'client = OpenAI(base_url="{v1}", api_key="{k}")\n'
        'resp = client.chat.completions.create(\n'
        '    model="auto",\n'
        '    messages=[{"role": "user", "content": "Hello"}],\n'
        ")\n"
        "print(resp.choices[0].message.content)\n"
        "\n"
        f"# curl:\n"
        f"# curl {v1}/chat/completions -H 'Authorization: Bearer {k}' \\\n"
        f"#   -H 'Content-Type: application/json' \\\n"
        f"#   -d '{{\"model\":\"auto\",\"messages\":[{{\"role\":\"user\",\"content\":\"hi\"}}]}}'"
    )


def _snippet_json(agent: str, v1: str, root: str, key: str | None) -> dict[str, Any]:
    if agent == "claude-code":
        return {
            "type": "env",
            "vars": {"ANTHROPIC_BASE_URL": root, "ANTHROPIC_API_KEY": key},
        }
    if agent == "hermes":
        return {
            "type": "config",
            "path": "config.yaml",
            "block": {"custom_providers": {"gatekeeper": {"base_url": v1, "api_key": key}}},
        }
    if agent in ("cursor", "continue-dev"):
        return {"type": "ui", "base_url": v1, "api_key": key, "model": "auto"}
    # opencode + custom-script use OpenAI env vars
    return {"type": "env", "vars": {"OPENAI_BASE_URL": v1, "OPENAI_API_KEY": key}}


def agent_snippet(agent: str, fmt: str = "text") -> dict[str, Any]:
    """Return a snippet for ``agent`` in ``fmt`` ('text' | 'json').

    The returned dict always carries ``agent`` and ``format``; for text it adds
    ``snippet`` (a string), for json it adds ``config`` (a structured object).
    Raises ``ValueError`` for an unknown agent or format.
    """
    agent = agent.lower()
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(
            f"Unknown agent '{agent}'. Supported: {', '.join(SUPPORTED_AGENTS)}"
        )
    if fmt not in ("text", "json"):
        raise ValueError("format must be 'text' or 'json'")

    v1 = base_url(with_v1=True)
    root = base_url(with_v1=False)
    key = _api_key()
    if fmt == "json":
        return {"agent": agent, "format": "json", "config": _snippet_json(agent, v1, root, key)}
    return {"agent": agent, "format": "text", "snippet": _snippet_text(agent, v1, root, key)}


# --------------------------------------------------------------------------- #
# Connection info                                                             #
# --------------------------------------------------------------------------- #
async def connection_info() -> dict[str, Any]:
    """Build the self-describing connection document for the gateway."""
    cfg = get_config()
    v1 = base_url(with_v1=True)
    root = base_url(with_v1=False)
    key = _api_key()

    registry = await get_registry()
    sample_ids = ["auto"] + [m.id for m in registry.get_active()[:4]]

    notes = [
        "Use `auto` to let the Quality Router pick the best available model.",
        "Authenticate with `Authorization: Bearer <key>` or the `X-API-Key` header.",
        "Per-agent setup: /v1/agent-snippet?agent=<name>&format=text|json",
    ]
    if not _is_loopback(cfg.server.host):
        notes.append(
            "api_key withheld: gateway is bound to a non-loopback host. "
            "Retrieve it from your server's config.yaml / .env."
        )

    doc: dict[str, Any] = {
        "gateway": {
            "base_url": v1,
            "api_key": key,
            "auth_enabled": cfg.auth.enabled,
            "cors_origins": cfg.server.cors_origins,
        },
        "models": {
            "default": "auto",
            "list_url": "/v1/models",
            "sample_ids": sample_ids,
        },
        "agents": {
            agent: agent_snippet(agent, "json")["config"] for agent in SUPPORTED_AGENTS
        },
        "snippet_url": "/v1/agent-snippet?agent=<name>",
        "notes": notes,
    }
    if not _is_loopback(cfg.server.host):
        doc["remote"] = {
            "host": cfg.server.host,
            "advice": "Set ADMIN_TOKEN before exposing the gateway beyond loopback.",
            "root_url": root,
        }
    return doc
