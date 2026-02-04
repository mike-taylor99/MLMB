"""FastAPI dependencies for dependency injection.

Use these with Depends() in route handlers for clean, testable code.
"""

from typing import Annotated
from fastapi import Depends

from app.config import Settings, get_settings
from shared.blob_service import BlobStorageService, get_blob_service as _get_blob_service
from shared.predictions_store import PredictionsStore, get_predictions_store as _get_predictions_store


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
