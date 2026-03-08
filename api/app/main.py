"""
MLMB API - FastAPI application factory.

Creates and configures the FastAPI application with middleware,
exception handlers, and routers.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError

from app.exceptions import APIError
from app.middleware import RequestIDMiddleware, RequestIDLogFilter, get_request_id
from app.routers import predictions, rankings, teams
from app.schemas import HealthResponse, ErrorResponse, ErrorDetail

# The "/api" prefix is defined in ONE place — see create_app().
API_PREFIX = "/api"


def _configure_logging() -> None:
    """Configure logging with request ID filter."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIDLogFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(request_id)s] %(levelname)s: %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # Suppress verbose Azure SDK HTTP request/response logging
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
        logging.WARNING
    )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown lifespan handler — kicks off background data loading."""
    from app.config import get_settings

    settings = get_settings()

    if settings.azure_storage_connection_string:
        from shared.blob_service import get_blob_service

        blob_service = get_blob_service()
        try:
            blob_service.start_preload()
        except Exception as e:
            logging.error(f"Preload failed (app will lazy-load on demand): {e}")
    else:
        logging.warning("No Azure Storage connection string — skipping preload")

    yield  # App runs here


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    _configure_logging()

    app = FastAPI(
        title="MLMB API",
        description="Machine Learning on Men's Basketball - NCAA Basketball Prediction API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    # Request ID middleware (must be added first to wrap everything)
    app.add_middleware(RequestIDMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    _register_exception_handlers(app)

    # Routers — all nested under a single parent router (/api prefix)
    api_router = APIRouter(prefix=API_PREFIX)
    api_router.include_router(predictions.router, tags=["Predictions"])
    api_router.include_router(rankings.router, tags=["Rankings"])
    api_router.include_router(teams.router, tags=["Teams"])

    # Health check
    @api_router.get("/health", tags=["Health"], response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse()

    app.include_router(api_router)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle custom API errors."""
        request_id = get_request_id()
        logging.warning(f"API error: {exc.code} - {exc.message}")
        response = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        request_id = get_request_id()
        errors = exc.errors()
        message = "; ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors])
        response = ErrorResponse(
            error=ErrorDetail(code="validation_error", message=message)
        )
        return JSONResponse(
            status_code=400,
            content=response.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors."""
        request_id = get_request_id()
        logging.exception(f"Unexpected error: {exc}")
        response = ErrorResponse(
            error=ErrorDetail(code="internal_error", message="Internal server error")
        )
        return JSONResponse(
            status_code=500,
            content=response.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )
