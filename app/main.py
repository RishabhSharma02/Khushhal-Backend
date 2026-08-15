from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.officer import router as officer_router
from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware
from app.core.rate_limit import install_rate_limiting


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    log = get_logger("app")
    settings = get_settings()

    # Warm the ML pipeline so first-request latency isn't the cost of a
    # cold sklearn/LightGBM load. Non-fatal if artifacts aren't present
    # — insights endpoints will raise 5xx until they are.
    try:
        import asyncio

        from app.ml.pipeline import load_models

        await asyncio.to_thread(load_models)
        log.info("ml_pipeline_ready")
    except Exception as e:
        log.warning("ml_pipeline_unavailable", err=str(e))

    from app.jobs.scheduler import start as start_scheduler, stop as stop_scheduler

    try:
        start_scheduler()
    except Exception as e:
        log.warning("scheduler_start_failed", err=str(e))

    log.info("startup", env=settings.env, dev_tools=settings.dev_tools_enabled)
    yield
    stop_scheduler()
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Khushhal Backend", version="0.2.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    install_rate_limiting(app)
    install_exception_handlers(app)
    app.include_router(api_v1_router)
    app.include_router(officer_router)

    @app.get("/")
    async def root() -> dict:
        return {"service": "khushhal-backend", "status": "ok"}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
