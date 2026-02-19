"""CORS, request-id, and logging middleware."""

import uuid
import time
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.config import settings

logger = logging.getLogger("etl_platform")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add a unique request ID to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        response: Response = await call_next(request)

        duration = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration)

        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID + timing
    app.add_middleware(RequestIdMiddleware)
