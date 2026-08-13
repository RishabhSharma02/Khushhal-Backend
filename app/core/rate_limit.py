"""slowapi rate-limit wiring.

Global default is generous; the tighter buckets are applied per-route with
`@limiter.limit(...)` decorators on `POST /auth/session`, entry writes, and
the dev insights refresh endpoint. Uses the client IP as key — perfectly
reasonable for the mobile-first traffic pattern where sessions are short-lived
Firebase tokens.

Rate limiting silently no-ops when `DEV_TOOLS_ENABLED=true` so local testing
never gets blocked.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.core.config import get_settings


def _key_func(request: Request) -> str:
    settings = get_settings()
    if settings.dev_tools_enabled:
        return "dev-shared"
    return get_remote_address(request)


limiter = Limiter(key_func=_key_func, default_limits=["120/minute"])


async def _rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": f"Too many requests: {exc.detail}"}},
    )


def install_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
