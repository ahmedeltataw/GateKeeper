"""Typed configuration loader.

Loads ``config.yaml`` and overlays environment variables from ``.env`` via
``python-dotenv``. The resulting ``AppConfig`` is cached and returned by
``get_config()``.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


class ServerCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1024 <= value <= 65535:
            raise ValueError(f"port must be between 1024 and 65535, got {value}")
        return value


class AuthCfg(BaseModel):
    enabled: bool = True
    api_key: str = "sk-local"
    multi_tenant: bool = False  # off => single shared api_key (legacy behavior)


class DatabaseCfg(BaseModel):
    path: str = "server/data/gateway.db"


class CacheCfg(BaseModel):
    enabled: bool = True
    ttl: int = 300
    max_size: int = 1000


class RateLimiterCfg(BaseModel):
    enabled: bool = True
    state_file: str = "server/data/rate_limits.json"


class StickyCfg(BaseModel):
    enabled: bool = True
    ttl: int = 1800
    context_handoff: bool = True


class QualityRouterCfg(BaseModel):
    enabled: bool = True
    default_task_type: str = "default"


class ProviderCfg(BaseModel):
    base_url: str


class DashboardCfg(BaseModel):
    enabled: bool = True
    username: str = "admin"
    admin_token: str | None = None


class DiagnosticsCfg(BaseModel):
    """Smart Diagnostic remediation (413 shrink, 429/5xx/timeout backoff)."""

    enabled: bool = True
    max_remediation_attempts: int = 2
    max_backoff_seconds: float = 8.0


class LanguageCfg(BaseModel):
    """Input-language preservation.

    The gateway never translates user content; free models simply default to
    English when not told otherwise. When ``preserve_input_language`` is on, a
    single constant system directive is injected at send time so the model
    mirrors the user's language. The text is constant, so it does not perturb
    the cache key or the sticky-session hash (both derived earlier, upstream).
    """

    preserve_input_language: bool = True
    directive: str = (
        "Always respond in the same language as the user's most recent "
        "message. Do not translate the user's content unless they explicitly "
        "ask you to."
    )


class CircuitCfg(BaseModel):
    """Per-model circuit breaker + auto-blacklist thresholds."""

    enabled: bool = True
    failures_to_open: int = 3
    open_cooldown_seconds: int = 120
    opens_to_blacklist: int = 3
    report_file: str = "server/data/blacklist_report.md"


class UsageCfg(BaseModel):
    """Per-tenant usage tracking (write-behind counters)."""

    enabled: bool = True
    flush_seconds: int = 30
    enforce: bool = False  # when True, exceed daily quota -> 429


class CatalogCfg(BaseModel):
    """Auto-generated models.json snapshot."""

    enabled: bool = True
    output_file: str = "models.json"
    refresh_seconds: int = 60


class BenchmarkCfg(BaseModel):
    """Opt-in background latency/quality benchmark. Off the request path."""

    enabled: bool = False
    interval_seconds: int = 1800
    output_file: str = "server/data/benchmarks.json"
    prompt: str = "Reply with exactly the word: pong"
    expected_substring: str = "pong"


class AppConfig(BaseModel):
    server: ServerCfg = Field(default_factory=ServerCfg)
    auth: AuthCfg = Field(default_factory=AuthCfg)
    database: DatabaseCfg = Field(default_factory=DatabaseCfg)
    cache: CacheCfg = Field(default_factory=CacheCfg)
    rate_limiter: RateLimiterCfg = Field(default_factory=RateLimiterCfg)
    sticky_sessions: StickyCfg = Field(default_factory=StickyCfg)
    quality_router: QualityRouterCfg = Field(default_factory=QualityRouterCfg)
    providers: dict[str, ProviderCfg] = Field(default_factory=dict)
    dashboard: DashboardCfg = Field(default_factory=DashboardCfg)
    diagnostics: DiagnosticsCfg = Field(default_factory=DiagnosticsCfg)
    language: LanguageCfg = Field(default_factory=LanguageCfg)
    circuit: CircuitCfg = Field(default_factory=CircuitCfg)
    catalog: CatalogCfg = Field(default_factory=CatalogCfg)
    usage: UsageCfg = Field(default_factory=UsageCfg)
    benchmark: BenchmarkCfg = Field(default_factory=BenchmarkCfg)
    encryption_key: str | None = None


def _apply_env_overrides(raw: dict) -> dict:
    """Overlay documented environment variables onto the parsed YAML dict."""
    server = raw.setdefault("server", {})
    if "PORT" in os.environ:
        server["port"] = int(os.environ["PORT"])
    if "HOST" in os.environ:
        server["host"] = os.environ["HOST"]
    if "LOG_LEVEL" in os.environ:
        server["log_level"] = os.environ["LOG_LEVEL"]

    encryption_key = os.environ.get("ENCRYPTION_KEY")
    if encryption_key:
        raw["encryption_key"] = encryption_key

    dashboard = raw.setdefault("dashboard", {})
    if "ADMIN_TOKEN" in os.environ:
        dashboard["admin_token"] = os.environ["ADMIN_TOKEN"]

    return raw


def _load_config_file(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def get_config(config_path: Path | None = None) -> AppConfig:
    """Return the cached application configuration."""
    load_dotenv(_PROJECT_ROOT / ".env")

    path = config_path or _CONFIG_PATH
    raw = _load_config_file(path)
    raw = _apply_env_overrides(raw)

    return AppConfig.model_validate(raw)


def reload_config(config_path: Path | None = None) -> AppConfig:
    """Clear the cached config and reload from disk/env."""
    get_config.cache_clear()
    return get_config(config_path)
