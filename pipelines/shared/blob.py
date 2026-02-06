"""
Azure Blob Storage upload helper.
"""

import logging
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)

CONTAINER_NAME = "mlmb-api"


def upload_blob(connection_string: str, blob_name: str, data: str) -> None:
    """
    Upload JSON string to Azure Blob Storage.

    Args:
        connection_string: Azure Storage connection string.
        blob_name: Blob path within the container (e.g. "ncaam_basketball/team-stats").
        data: JSON string to upload.
    """
    client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )
    logger.info(f"Uploaded blob: {CONTAINER_NAME}/{blob_name} ({len(data)} bytes)")
