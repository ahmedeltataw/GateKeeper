#!/usr/bin/env python3
"""GateKeeper agent-integration wizard.

Fetches the gateway's ``/v1/connection-info`` and live model catalogue from
``GET /v1/models`` (authenticated with ``Authorization: Bearer <key>``), then
writes the correct config for the agents you pick — OpenCode, Hermes, Claude
Code — or just prints the snippets. Safe by design: JSON configs are merged,
text configs are confined to a ``GATEKEEPER_BEGIN/END`` marker block, and
``--dry-run`` shows what would change without writing.

The gateway key is resolved from ``--api-key``, then ``GATEKEEPER_API_KEY`` in
the environment, then the project ``.env``, then ``config.yaml`` (``auth.api_key``),
falling back to ``sk-local``.

Examples:
    python scripts/setup_agents.py                       # interactive
    python scripts/setup_agents.py --agent opencode --yes
    python scripts/setup_agents.py --agents opencode,hermes --yes
    python scripts/setup_agents.py --print               # just show snippets
    python scripts/setup_agents.py --url http://host:8000 --api-key sk-local --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Allow running as a loose script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The wizard prints emoji status lines; on a legacy Windows console (cp1252)
# that raises UnicodeEncodeError. Force UTF-8 so the tool runs everywhere.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):  # pre-3.7 or already-wrapped stream
        pass

from scripts.agent_writers import (  # noqa: E402
    hermes_block,
    opencode_config_merge,
    opencode_config_text,
    shell_env_block,
    upsert_marker_block,
)

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_API_KEY = "sk-local"
AGENT_CHOICES = ("opencode", "hermes", "claude-code")
_ROOT = Path(__file__).resolve().parents[1]


def _key_from_env_file() -> str | None:
    """Read the gateway key from a project ``.env`` (GATEKEEPER_API_KEY / API_KEY)."""
    env_path = _ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() in ("GATEKEEPER_API_KEY", "API_KEY", "AUTH_API_KEY"):
            return value.strip().strip('"').strip("'") or None
    return None


def _key_from_config() -> str | None:
    """Read ``auth.api_key`` from the project ``config.yaml`` if present."""
    cfg_path = _ROOT / "config.yaml"
    if not cfg_path.exists():
        return None
    try:
        import yaml  # lazy: only needed when falling back to config.yaml
    except ImportError:
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    return (cfg.get("auth") or {}).get("api_key") or None


def _resolve_api_key(cli_key: str | None) -> str:
    """Resolve the gateway key: --api-key > env > .env > config.yaml > default.

    Mirrors how a curl call authenticates: the value becomes the
    ``Authorization: Bearer <key>`` header on every gateway request.
    """
    return (
        cli_key
        or os.environ.get("GATEKEEPER_API_KEY")
        or _key_from_env_file()
        or _key_from_config()
        or DEFAULT_API_KEY
    )


def _get_json(url: str, api_key: str) -> dict:
    """GET ``url`` as JSON, authenticating with ``Authorization: Bearer``."""
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (local)
        return json.loads(resp.read().decode("utf-8"))


def _fetch_connection_info(base: str, api_key: str) -> dict:
    url = base.rstrip("/") + "/v1/connection-info"
    try:
        return _get_json(url, api_key)
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(
            f"✗ Could not reach GateKeeper at {url}.\n"
            f"  Start the gateway first, or pass --url. ({exc})"
        )


def _fetch_models(base: str, api_key: str) -> list[str]:
    """Fetch model IDs from ``GET /v1/models`` (OpenAI-shaped ``data`` list).

    Returns the list of IDs, or an empty list (with a clear warning) when the
    server is unreachable or rejects the key — the config is still generated,
    just without the model catalogue.
    """
    url = base.rstrip("/") + "/v1/models"
    try:
        payload = _get_json(url, api_key)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            print(
                f"✗ Gateway rejected the API key at {url} (HTTP {exc.code}).\n"
                "  Check the key in .env / config.yaml, or pass --api-key."
            )
        else:
            print(f"✗ Gateway returned HTTP {exc.code} for {url}.")
        return []
    except (urllib.error.URLError, OSError) as exc:
        print(f"✗ Could not fetch models from {url}. ({exc})")
        return []

    data = payload.get("data", []) if isinstance(payload, dict) else []
    return [m["id"] for m in data if isinstance(m, dict) and m.get("id")]


def _gateway_creds(info: dict, api_key: str) -> tuple[str, str]:
    gw = info.get("gateway", {})
    base_url = gw.get("base_url") or (DEFAULT_URL + "/v1")
    return base_url, api_key


def _plan(
    agent: str, base_url: str, api_key: str, models: list[str] | None = None
) -> tuple[Path, str, str]:
    """Return (target_path, new_content, kind) for an agent without writing."""
    home = Path.home()
    if agent == "opencode":
        path = home / ".config" / "opencode" / "config.json"
        existing = json.loads(path.read_text()) if path.exists() else None
        merged = opencode_config_merge(existing, base_url, api_key, models)
        return path, opencode_config_text(merged), "json-merge"
    if agent == "hermes":
        path = home / ".hermes" / "config.yaml"
        existing = path.read_text() if path.exists() else ""
        block = hermes_block(base_url, api_key)
        return path, upsert_marker_block(existing, block), "marker"
    # claude-code -> shell rc
    path = home / ".gatekeeper.env.sh"
    existing = path.read_text() if path.exists() else ""
    block = shell_env_block(base_url, api_key, anthropic=True)
    return path, upsert_marker_block(existing, block), "marker"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".gatekeeper.bak")
        backup.write_text(path.read_text(), encoding="utf-8")
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure agents to use GateKeeper.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Gateway root URL.")
    parser.add_argument("--api-key", dest="api_key",
                        help="Gateway key for Authorization: Bearer. "
                             "Defaults to env/.env/config.yaml, else sk-local.")
    parser.add_argument("--agents", help="Comma list: opencode,hermes,claude-code.")
    parser.add_argument("--agent", help="Single agent (alias of --agents).")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="Only print snippets; write nothing.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes, write nothing.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts.")
    args = parser.parse_args()

    print("🔌 GateKeeper Agent Integration Setup")
    api_key = _resolve_api_key(args.api_key)
    info = _fetch_connection_info(args.url, api_key)
    base_url, api_key = _gateway_creds(info, api_key)
    print(f"✔ Gateway: {base_url}")
    print(f"✔ API key: {api_key}")

    models = _fetch_models(args.url, api_key)
    if models:
        print(f"✔ Models: {len(models)} fetched from /v1/models\n")
    else:
        print("⚠ No models fetched; configs will omit the model catalogue.\n")

    agents_arg = args.agents or args.agent
    if agents_arg:
        agents = [a.strip() for a in agents_arg.split(",") if a.strip()]
    elif args.print_only or not sys.stdin.isatty():
        agents = list(AGENT_CHOICES)
    else:
        print("Which agents? (comma-separated, or Enter for all)")
        print("  " + ", ".join(AGENT_CHOICES))
        raw = input("> ").strip()
        agents = [a.strip() for a in raw.split(",") if a.strip()] or list(AGENT_CHOICES)

    unknown = [a for a in agents if a not in AGENT_CHOICES]
    if unknown:
        raise SystemExit(f"✗ Unknown agent(s): {', '.join(unknown)}")

    for agent in agents:
        path, content, kind = _plan(agent, base_url, api_key, models)
        if args.print_only:
            print(f"\n# ── {agent} → {path} ({kind}) ──\n{content}")
            continue
        if args.dry_run:
            print(f"\n# ── {agent} → {path} ({kind}) [DRY RUN] ──\n{content}")
            continue
        if not args.yes:
            ok = input(f"Write {agent} config to {path}? [y/N] ").strip().lower()
            if ok not in ("y", "yes"):
                print(f"  skipped {agent}")
                continue
        _write(path, content)
        print(f"✔ Wrote {path}")

    if "claude-code" in agents and not (args.print_only or args.dry_run):
        print("\nℹ Claude Code: `source ~/.gatekeeper.env.sh` then `claude --model auto`.")
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
