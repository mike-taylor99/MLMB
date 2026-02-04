"""Middleware for request processing.

Includes request ID tracing for debugging and observability.
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Context variable for request ID - accessible anywhere in the request lifecycle
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique ID to each request.

    - Checks for existing X-Request-ID header (from load balancer, API gateway, etc.)
    - Generates a new UUID if not present
    - Adds X-Request-ID to response headers
    - Makes request ID available via get_request_id() throughout the request
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use existing request ID or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in context variable for access in services/logging
        request_id_var.set(request_id)

        # Add to request state for easy access in route handlers
        request.state.request_id = request_id

        # Process request and measure time
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        logging.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration_ms:.1f}ms "
            f"request_id={request_id}"
        )

        return response


class RequestIDLogFilter(logging.Filter):
    """
    Logging filter that adds request_id to all log records.

    Usage in logging config:
        format = "%(asctime)s [%(request_id)s] %(levelname)s: %(message)s"
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True
