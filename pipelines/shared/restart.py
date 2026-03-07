"""
Restart the MLMB API Container App after a pipeline job finishes.

Uses Azure Managed Identity to authenticate against the ARM REST API
and restart the active revision so fresh blob data is picked up.

Environment variables:
    AZURE_SUBSCRIPTION_ID  — Azure subscription ID.
    API_RESOURCE_GROUP     — Resource group of the API container app (default: mlmb).
    API_CONTAINER_APP      — Name of the API container app (default: mlmb-api).
"""

import logging
import os

import requests
from azure.identity import ManagedIdentityCredential

logger = logging.getLogger(__name__)

# ARM management endpoint
ARM_BASE = "https://management.azure.com"
API_VERSION = "2024-03-01"


def restart_api() -> bool:
    """
    Restart the MLMB API Container App by retrieving the latest revision
    and issuing a restart via the ARM REST API.

    Returns True on success, False on failure (non-fatal — pipeline still succeeds).
    """
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("API_RESOURCE_GROUP", "mlmb")
    container_app = os.environ.get("API_CONTAINER_APP", "mlmb-api")

    if not subscription_id:
        logger.warning("AZURE_SUBSCRIPTION_ID not set — skipping API restart.")
        return False

    try:
        # Get an ARM token via managed identity
        credential = ManagedIdentityCredential()
        token = credential.get_token("https://management.azure.com/.default")

        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }

        # 1. Get the active revision name
        app_url = (
            f"{ARM_BASE}/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.App/containerApps/{container_app}"
            f"?api-version={API_VERSION}"
        )
        resp = requests.get(app_url, headers=headers, timeout=30)
        resp.raise_for_status()
        revision_name = resp.json()["properties"]["latestRevisionName"]
        logger.info(f"Active revision: {revision_name}")

        # 2. Restart the revision
        restart_url = (
            f"{ARM_BASE}/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.App/containerApps/{container_app}"
            f"/revisions/{revision_name}/restart"
            f"?api-version={API_VERSION}"
        )
        resp = requests.post(restart_url, headers=headers, timeout=30)
        resp.raise_for_status()
        logger.info(f"Restarted {container_app} revision {revision_name}")
        return True

    except Exception as e:
        logger.warning(f"Failed to restart API (non-fatal): {e}")
        return False
