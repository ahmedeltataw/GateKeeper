#!/usr/bin/env python3
"""GateKeeper agent-integration wizard.

Fetches the gateway's own ``/v1/connection-info`` and writes the correct config
for the agents you pick — OpenCode, Hermes, Claude Code — or just prints the
snippets. Safe by design: JSON configs are merged, text configs are confined to
a ``GATEKEEPER_BEGIN/END`` marker block, and ``--dry-run`` shows what would
change without writing.

Examples:
    python scripts/setup_agents.py                       # interactive
    python scripts/setup_agents.py --agents opencode,hermes --yes
    python scripts/setup_agents.py --print               # just show snippets
    python scripts/setup_agents.py --url http://host:8000 --dry-run
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
AGENT_CHOICES = ("opencode", "hermes", "claude-code")


def _fetch_connection_info(base: str) -> dict:
    url = base.rstrip("/") + "/v1/connection-info"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (local)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"✗ Could not reach GateKeeper at {url}.\n"
            f"  Start the gateway first, or pass --url. ({exc})"
        )


def _gateway_creds(info: dict) -> tuple[str, str]:
    gw = info.get("gateway", {})
    base_url = gw.get("base_url") or (DEFAULT_URL + "/v1")
    api_key = gw.get("api_key")
    if not api_key:
        api_key = os.environ.get("GATEKEEPER_API_KEY", "<YOUR_API_KEY>")
    return base_url, api_key


def _plan(agent: str, base_url: str, api_key: str) -> tuple[Path, str, str]:
    """Return (target_path, new_content, kind) for an agent without writing."""
    home = Path.home()
    if agent == "opencode":
        path = home / ".config" / "opencode" / "config.json"
        existing = json.loads(path.read_text()) if path.exists() else None
        merged = opencode_config_merge(existing, base_url, api_key)
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
    parser.add_argument("--agents", help="Comma list: opencode,hermes,claude-code.")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="Only print snippets; write nothing.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes, write nothing.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts.")
    args = parser.parse_args()

    print("🔌 GateKeeper Agent Integration Setup")
    info = _fetch_connection_info(args.url)
    base_url, api_key = _gateway_creds(info)
    print(f"✔ Gateway: {base_url}")
    print(f"✔ API key: {api_key}\n")

    if args.agents:
        agents = [a.strip() for a in args.agents.split(",") if a.strip()]
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
        path, content, kind = _plan(agent, base_url, api_key)
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
