"""Configuration loading for the standalone Streamlit dashboard.

This module reads ``GATEWAY_URL`` and ``ADMIN_TOKEN`` from the environment,
with lightweight ``.env`` fallback support for both ``dashboard/.env`` and the
project-root ``.env``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_GATEWAY_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    """Runtime configuration for the Streamlit dashboard."""

    gateway_url: str
    admin_token: str | None


def _candidate_env_paths() -> list[Path]:
    """Return dashboard-local and project-root .env paths in lookup order."""
    dashboard_dir = Path(__file__).resolve().parent
    return [dashboard_dir / ".env", dashboard_dir.parent / ".env"]


def _parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file without extra dependencies."""
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned_value = value.strip().strip('"').strip("'")
        values[key.strip()] = cleaned_value
    return values


def _load_env_values() -> dict[str, str]:
    """Load environment values with OS env taking precedence over .env files."""
    merged: dict[str, str] = {}
    for env_path in _candidate_env_paths():
        merged.update(_parse_env_file(env_path))
    merged.update(os.environ)
    return merged


def load_dashboard_config() -> DashboardConfig:
    """Return the dashboard configuration from env and .env sources."""
    env_values = _load_env_values()
    admin_token = env_values.get("ADMIN_TOKEN") or None
    return DashboardConfig(
        gateway_url=env_values.get("GATEWAY_URL", _DEFAULT_GATEWAY_URL).rstrip("/"),
        admin_token=admin_token,
    )
