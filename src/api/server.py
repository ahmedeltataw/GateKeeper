"""FastAPI application server for GateKeeper."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api import admin, dashboard, setup
from src.api.middleware import AuthMiddleware, LoggerMiddleware, attach_cors
from src.api.routes import error_response, router
from src.core import (
    benchmark,
    catalog,
    circuit,
    health,
    key_manager,
    probe,
    rate_limiter,
    tenant,
    usage,
)
from src.core.config_loader import get_config
from src.core.registry import get_registry
from src.core.types import GatewayError


async def _usage_flush_loop(interval: int) -> None:
    """Periodically persist in-memory usage counters to SQLite (write-behind)."""
    while True:
        await asyncio.sleep(interval)
        try:
            await usage.flush()
        except Exception:
            pass  # never let the flush loop crash the app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    await get_registry()
    await key_manager.init()
    await tenant.init()
    await usage.init()
    await circuit.init()
    await rate_limiter.load_state()
    await dashboard.init()
    health.start()
    catalog.start()
    benchmark.start()

    # Boot-time smoke probe: quarantine broken models before any user hits them.
    # Best-effort — a probe failure must never stop the gateway from serving.
    if get_config().probe.enabled:
        try:
            await probe.probe_all_models()
        except Exception:
            pass

    usage_cfg = get_config().usage
    flush_task: asyncio.Task | None = None
    if usage_cfg.enabled:
        flush_task = asyncio.create_task(_usage_flush_loop(usage_cfg.flush_seconds))

    yield

    if flush_task is not None:
        flush_task.cancel()
        try:
            await flush_task
        except asyncio.CancelledError:
            pass
    await usage.flush()  # final durable write on shutdown
    await benchmark.stop()
    await catalog.stop()
    await health.stop()
    await rate_limiter.save_state()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="GateKeeper",
        description="مجمع النماذج المجانية في API واحد",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    attach_cors(app)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(LoggerMiddleware)
    app.include_router(router)

    if get_config().dashboard.enabled:
        app.include_router(setup.router)  # public first-run onboarding
        app.include_router(admin.router)

    @app.exception_handler(GatewayError)
    async def _gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
        error_type = {
            404: "not_found",
            429: "rate_limit_error",
            503: "service_unavailable",
        }.get(exc.status_code, "api_error")
        return error_response(str(exc), error_type, exc.status_code)

    return app


app = create_app()


def main() -> None:
    config = get_config()
    uvicorn.run(
        "src.api.server:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
    )


if __name__ == "__main__":
    main()
