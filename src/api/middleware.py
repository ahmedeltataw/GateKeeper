"""FastAPI middleware: CORS, authentication, and request logging."""

from __future__ import annotations

import secrets
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.core import tenant
from src.core.config_loader import get_config


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer-token auth for all routes except public health checks."""

    # First-run onboarding (see src/api/setup.py). `status` is always public;
    # `bootstrap` is public ONLY until a token exists, after which it falls
    # through to normal admin auth and the endpoint itself returns 409.
    _SETUP_STATUS_PATH = "/admin/setup/status"
    _SETUP_BOOTSTRAP_PATH = "/admin/setup/bootstrap"

    @staticmethod
    def _auth_error(message: str) -> Response:
        """Return a fixed OpenAI-style 401 for client auth failures."""
        return Response(
            content=(
                '{"error":{"message":"' + message + '",'
                '"type":"authentication_error","code":401}}'
            ),
            status_code=401,
            media_type="application/json",
        )

    @staticmethod
    def _admin_not_configured_response() -> JSONResponse:
        """Return the fixed 403 response when admin auth is unavailable."""
        return JSONResponse(status_code=403, content={"error": "admin token not configured"})

    @staticmethod
    def _admin_unauthorized_response() -> JSONResponse:
        """Return the fixed 401 response for bad or missing admin credentials."""
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    @staticmethod
    def _extract_bearer_token(auth_header: str) -> str | None:
        """Return the bearer token value when the header uses the expected scheme."""
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        config = get_config()

        if request.url.path.startswith("/admin") and not config.dashboard.enabled:
            return await call_next(request)

        if config.dashboard.enabled and request.url.path.startswith("/admin"):
            admin_token = config.dashboard.admin_token

            # First-run onboarding: let the dashboard reach setup without a token.
            path = request.url.path
            if path == self._SETUP_STATUS_PATH:
                return await call_next(request)
            if path == self._SETUP_BOOTSTRAP_PATH and not admin_token:
                return await call_next(request)

            # 403 differentiates server misconfiguration from a bad client token.
            if not admin_token:
                return self._admin_not_configured_response()

            token = self._extract_bearer_token(request.headers.get("Authorization", ""))
            if token is None or not secrets.compare_digest(token, admin_token):
                return self._admin_unauthorized_response()
            return await call_next(request)

        if not config.auth.enabled:
            request.state.principal = tenant.OWNER
            return await call_next(request)

        if request.url.path == "/health":
            return await call_next(request)

        token = self._extract_bearer_token(request.headers.get("Authorization", ""))
        if token is None:
            return self._auth_error("Missing or invalid Authorization header")

        # Path A — multi-tenant SaaS: the key resolves to a client Principal.
        if config.auth.multi_tenant:
            principal = await tenant.resolve_principal(token)
            if principal is None:
                # The configured owner key still works as a superuser.
                if secrets.compare_digest(token, config.auth.api_key):
                    principal = tenant.OWNER
                else:
                    return self._auth_error("Invalid API key")
            request.state.principal = principal
            return await call_next(request)

        # Path B — legacy single shared key (unchanged behavior).
        if not secrets.compare_digest(token, config.auth.api_key):
            return self._auth_error("Invalid API key")
        request.state.principal = tenant.OWNER
        return await call_next(request)


class LoggerMiddleware(BaseHTTPMiddleware):
    """Log request metadata without exposing secrets or bodies."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        path = request.url.path
        client = request.client.host if request.client else "unknown"
        method = request.method

        # Pull model/task_type from known path/query params only.
        model = request.query_params.get("model") or "-"
        task_type = request.query_params.get("task_type") or "-"

        print(
            f"{method} {path} {response.status_code} {duration:.3f}s "
            f"ip={client} model={model} task_type={task_type}"
        )
        return response


def attach_cors(app) -> None:
    """Attach CORS middleware based on the configured server host."""
    config = get_config()
    allow_credentials = config.server.host != "127.0.0.1"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
