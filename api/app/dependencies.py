"""FastAPI dependencies for dependency injection.

Use these with Depends() in route handlers for clean, testable code.
"""

import base64
import json
import logging
from typing import Annotated, Optional

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.exceptions import AuthenticationError
from shared.blob_service import BlobStorageService, get_blob_service as _get_blob_service
from shared.predictions_store import PredictionsStore, get_predictions_store as _get_predictions_store

logger = logging.getLogger(__name__)

# Type aliases for cleaner route signatures
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_blob_service() -> BlobStorageService:
    """Get the blob storage service singleton."""
    return _get_blob_service()


def get_predictions_store() -> PredictionsStore:
    """Get the predictions store singleton."""
    return _get_predictions_store()


# Type aliases for dependency injection
BlobServiceDep = Annotated[BlobStorageService, Depends(get_blob_service)]
PredictionsStoreDep = Annotated[PredictionsStore, Depends(get_predictions_store)]


# ---------------------------------------------------------------------------
# Auth — require either SWA user identity OR a valid API key
# ---------------------------------------------------------------------------

def _parse_client_principal(header_value: str) -> Optional[dict]:
    """Decode the base64-encoded x-ms-client-principal header from SWA."""
    try:
        decoded = base64.b64decode(header_value)
        return json.loads(decoded)
    except Exception:
        return None


def require_auth(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Dependency that enforces authentication on a route.

    Accepts EITHER:
      - x-ms-client-principal header (user via SWA proxy)
      - X-API-Key header matching settings.api_key (server-to-server jobs)

    Returns the decoded client principal dict, or a synthetic one for API key auth.
    """
    # 1. Check SWA user identity
    principal_header = request.headers.get("x-ms-client-principal")
    if principal_header:
        principal = _parse_client_principal(principal_header)
        if principal:
            return principal

    # 2. Check API key (for jobs/pipelines)
    api_key = request.headers.get("x-api-key")
    if api_key and settings.api_key and api_key == settings.api_key:
        return {"auth_type": "api_key", "userDetails": "service-account"}

    raise AuthenticationError()


RequireAuthDep = Annotated[dict, Depends(require_auth)]
