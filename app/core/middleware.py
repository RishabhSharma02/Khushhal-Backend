"""ASGI middleware: request-id + structlog context binding.

Every request gets an `X-Request-ID` (honoured if the caller supplied one,
otherwise generated). The id is bound to structlog's contextvars for the
lifetime of the request and echoed back in the response header — makes
grep-ing production logs after a bug report trivial.
"""
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get(_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=req_id,
            path=request.url.path,
            method=request.method,
        )
        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[_HEADER] = req_id
        return response
