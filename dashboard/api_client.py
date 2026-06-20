"""Typed HTTP client for the gateway's `/admin/*` API.

This module is the dashboard's only HTTP boundary. It injects the bearer admin
token and translates gateway/network failures into user-safe exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

_REQUEST_TIMEOUT_SECONDS = 10.0


class AdminApiError(Exception):
    """Base error for admin API client failures."""


class AdminUnauthorizedError(AdminApiError):
    """Raised when the supplied admin token is missing or invalid."""


class AdminTokenNotConfiguredError(AdminApiError):
    """Raised when the gateway has no ADMIN_TOKEN configured."""


class GatewayUnavailableError(AdminApiError):
    """Raised when the gateway cannot be reached over HTTP."""


class SetupAlreadyDoneError(AdminApiError):
    """Raised when first-run bootstrap is attempted but a token already exists."""


@dataclass(frozen=True, slots=True)
class AdminStats:
    """Counters returned by `GET /admin/stats`."""

    requests_total: int
    requests_last_hour: int
    cache_hits: int
    fallback_count: int
    uptime_seconds: int


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    """Provider state returned by `GET /admin/providers`."""

    id: str
    status: str
    last_checked: float | None


@dataclass(frozen=True, slots=True)
class KeySummary:
    """Masked key metadata returned by `GET /admin/keys` and `POST /admin/keys`."""

    provider: str
    masked: str
    health_status: str


@dataclass(frozen=True, slots=True)
class AnalyticsEntry:
    """Per-provider analytics returned by `GET /admin/analytics`."""

    requests: int
    tokens: int
    avg_latency_ms: float


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Registry model shape returned by `GET /admin/models`."""

    id: str
    display_name: str
    provider_id: str
    provider_model_id: str
    strength: str
    strength_order: int
    use_cases: list[str]
    category: str
    context_window: int
    max_output_tokens: int
    modalities: list[str]
    pricing: dict[str, float] | None
    rate_limits: dict[str, Any]
    enabled: bool
    status: str
    fallback_models: list[str]
    notes: str | None
    source_url: str | None
    added_at: str
    removed_at: str | None
    last_verified: str
    verification_source: str | None


def _raise_for_status(response: httpx.Response) -> None:
    """Translate known gateway auth failures and generic errors into client exceptions."""
    if response.status_code == 401:
        raise AdminUnauthorizedError("The gateway rejected the admin token.")
    if response.status_code == 403:
        raise AdminTokenNotConfiguredError("The gateway does not have ADMIN_TOKEN configured yet.")
    if response.is_error:
        raise AdminApiError(f"Gateway returned HTTP {response.status_code}.")


def _as_admin_stats(payload: dict[str, Any]) -> AdminStats:
    """Convert a stats JSON object into a typed `AdminStats` result."""
    return AdminStats(
        requests_total=int(payload["requests_total"]),
        requests_last_hour=int(payload["requests_last_hour"]),
        cache_hits=int(payload["cache_hits"]),
        fallback_count=int(payload["fallback_count"]),
        uptime_seconds=int(payload["uptime_seconds"]),
    )


def _as_provider_status(payload: dict[str, Any]) -> ProviderStatus:
    """Convert one provider JSON object into a typed `ProviderStatus` result."""
    last_checked = payload.get("last_checked")
    return ProviderStatus(
        id=str(payload["id"]),
        status=str(payload["status"]),
        last_checked=None if last_checked is None else float(last_checked),
    )


def _as_key_summary(payload: dict[str, Any]) -> KeySummary:
    """Convert one masked key JSON object into a typed `KeySummary` result."""
    return KeySummary(
        provider=str(payload["provider"]),
        masked=str(payload["masked"]),
        health_status=str(payload["health_status"]),
    )


def _as_analytics_entry(payload: dict[str, Any]) -> AnalyticsEntry:
    """Convert one analytics JSON object into a typed `AnalyticsEntry` result."""
    return AnalyticsEntry(
        requests=int(payload["requests"]),
        tokens=int(payload["tokens"]),
        avg_latency_ms=float(payload["avg_latency_ms"]),
    )


def _as_model_info(payload: dict[str, Any]) -> ModelInfo:
    """Convert one model JSON object into a typed `ModelInfo` result."""
    pricing = payload.get("pricing")
    typed_pricing = None if pricing is None else {str(key): float(value) for key, value in pricing.items()}
    return ModelInfo(
        id=str(payload["id"]),
        display_name=str(payload["display_name"]),
        provider_id=str(payload["provider_id"]),
        provider_model_id=str(payload["provider_model_id"]),
        strength=str(payload["strength"]),
        strength_order=int(payload["strength_order"]),
        use_cases=[str(item) for item in payload["use_cases"]],
        category=str(payload["category"]),
        context_window=int(payload["context_window"]),
        max_output_tokens=int(payload["max_output_tokens"]),
        modalities=[str(item) for item in payload["modalities"]],
        pricing=typed_pricing,
        rate_limits=dict(payload["rate_limits"]),
        enabled=bool(payload["enabled"]),
        status=str(payload["status"]),
        fallback_models=[str(item) for item in payload["fallback_models"]],
        notes=None if payload.get("notes") is None else str(payload["notes"]),
        source_url=None if payload.get("source_url") is None else str(payload["source_url"]),
        added_at=str(payload["added_at"]),
        removed_at=None if payload.get("removed_at") is None else str(payload["removed_at"]),
        last_verified=str(payload["last_verified"]),
        verification_source=None
        if payload.get("verification_source") is None
        else str(payload["verification_source"]),
    )


class AdminApiClient:
    """Thin typed wrapper over the gateway's admin API."""

    def __init__(self, gateway_url: str, admin_token: str) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._admin_token = admin_token

    def _headers(self) -> dict[str, str]:
        """Return request headers for authenticated admin API calls."""
        return {"Authorization": f"Bearer {self._admin_token}"}

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> httpx.Response:
        """Execute one HTTP request and normalize connection/auth failures."""
        try:
            with httpx.Client(base_url=self._gateway_url, timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = client.request(
                    method,
                    path,
                    headers=self._headers(),
                    json=json_body,
                )
        except httpx.RequestError as exc:
            raise GatewayUnavailableError(
                f"Could not reach the gateway at {self._gateway_url}."
            ) from exc

        _raise_for_status(response)
        return response

    def validate_token(self) -> list[ProviderStatus]:
        """Call `GET /admin/providers`, returning provider rows or auth/unreachable errors."""
        return self.get_providers()

    def get_stats(self) -> AdminStats:
        """Call `GET /admin/stats`, returning counters or auth/unreachable errors."""
        payload = self._request("GET", "/admin/stats").json()
        return _as_admin_stats(payload)

    def get_providers(self) -> list[ProviderStatus]:
        """Call `GET /admin/providers`, returning provider rows or auth/unreachable errors."""
        provider_rows = self._request("GET", "/admin/providers").json()
        return [_as_provider_status(provider_row) for provider_row in provider_rows]

    def get_keys(self) -> list[KeySummary]:
        """Call `GET /admin/keys`, returning masked keys or auth/unreachable errors."""
        key_rows = self._request("GET", "/admin/keys").json()
        return [_as_key_summary(key_row) for key_row in key_rows]

    def set_key(self, provider: str, api_key: str) -> KeySummary:
        """Call `POST /admin/keys`, returning one masked key summary or request/auth errors."""
        payload = self._request(
            "POST",
            "/admin/keys",
            json_body={"provider": provider, "api_key": api_key},
        ).json()
        return _as_key_summary(payload)

    def delete_key(self, provider: str) -> None:
        """Call `DELETE /admin/keys/{provider}`, returning nothing or auth/unreachable errors."""
        self._request("DELETE", f"/admin/keys/{provider}")

    def get_models(self) -> list[ModelInfo]:
        """Call `GET /admin/models`, returning typed model rows or auth/unreachable errors."""
        model_rows = self._request("GET", "/admin/models").json()
        return [_as_model_info(model_row) for model_row in model_rows]

    def get_analytics(self) -> dict[str, AnalyticsEntry]:
        """Call `GET /admin/analytics`, returning per-provider analytics or auth/unreachable errors."""
        payload = self._request("GET", "/admin/analytics").json()
        return {
            str(provider_id): _as_analytics_entry(entry)
            for provider_id, entry in payload.items()
        }

    def get_usage(self) -> list[dict[str, Any]]:
        """Call `GET /admin/usage`, returning per-tenant usage-vs-quota documents.

        The payload is already frontend-shaped (totals/quota/percent/models), so
        it is returned as-is for the analytics page to render.
        """
        return list(self._request("GET", "/admin/usage").json())


def fetch_setup_status(gateway_url: str) -> bool:
    """Return whether the gateway still needs first-run admin setup (no auth)."""
    url = gateway_url.rstrip("/")
    try:
        with httpx.Client(base_url=url, timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = client.get("/admin/setup/status")
    except httpx.RequestError as exc:
        raise GatewayUnavailableError(f"Could not reach the gateway at {url}.") from exc
    if response.is_error:
        raise AdminApiError(f"Gateway returned HTTP {response.status_code}.")
    return bool(response.json().get("needs_setup", False))


def bootstrap_admin_token(gateway_url: str) -> str:
    """Mint the first-run admin token (no auth). Raise if one already exists."""
    url = gateway_url.rstrip("/")
    try:
        with httpx.Client(base_url=url, timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post("/admin/setup/bootstrap")
    except httpx.RequestError as exc:
        raise GatewayUnavailableError(f"Could not reach the gateway at {url}.") from exc
    if response.status_code == 409:
        raise SetupAlreadyDoneError("The gateway already has an admin token configured.")
    if response.is_error:
        raise AdminApiError(f"Gateway returned HTTP {response.status_code}.")
    return str(response.json()["admin_token"])
