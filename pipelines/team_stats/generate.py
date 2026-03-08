"""
Team Stats Pipeline — Container Apps Job entrypoint.

Generates latest team statistics for all NCAA basketball teams
and uploads to Azure Blob Storage.

Usage:
    python -m team_stats.generate

Environment variables:
    AZURE_STORAGE_CONNECTION_STRING  — Required for blob upload.
"""

import logging
import os
import sys

# Ensure shared modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.season import current_season_year, is_in_season
from shared.stats import generate_and_upload_team_stats
from shared.restart import restart_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [team-stats] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Off-season guard
    if not is_in_season():
        logger.info("Off-season — skipping team stats generation.")
        return

    season = current_season_year()
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        logger.warning(
            "AZURE_STORAGE_CONNECTION_STRING not set — results will only be written locally."
        )

    logger.info(f"Starting team stats pipeline for season {season}")
    success = generate_and_upload_team_stats(
        season, connection_string=connection_string
    )
    logger.info("Team stats pipeline complete.")

    if success and connection_string:
        restart_api()

    if not success:
        logger.error("One or more sports failed to generate stats.")
        sys.exit(1)


if __name__ == "__main__":
    main()
