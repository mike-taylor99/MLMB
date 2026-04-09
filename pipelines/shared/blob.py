"""
Azure Blob Storage upload helper.
"""

import logging
import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)

CONTAINER_NAME = "mlmb-api"


def _get_blob_client() -> BlobServiceClient:
    """Create a BlobServiceClient using managed identity."""
    account_url = os.environ.get("AZURE_STORAGE_ACCOUNT_URL", "")
    if not account_url:
        raise ValueError("AZURE_STORAGE_ACCOUNT_URL not set")
    return BlobServiceClient(account_url, credential=DefaultAzureCredential())


def upload_blob(blob_name: str, data: str) -> None:
    """
    Upload JSON string to Azure Blob Storage.

    Uses DefaultAzureCredential (managed identity in production,
    az login locally).

    Args:
        blob_name: Blob path within the container (e.g. "ncaam_basketball/team-stats").
        data: JSON string to upload.
    """
    client = _get_blob_client()
    blob_client = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )
    logger.info(f"Uploaded blob: {CONTAINER_NAME}/{blob_name} ({len(data)} bytes)")
