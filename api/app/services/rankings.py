"""
Rankings service - business logic for rankings.

Handles ranking retrieval and formatting.
"""

import logging

from app.schemas import RankingsResponse, RankingEntry
from shared.blob_service import BlobStorageService


def get_rankings(sport: str, blob_service: BlobStorageService) -> RankingsResponse:
    """
    Get top 25 rankings for a sport.

    Args:
        sport: The sport code
        blob_service: Blob storage service

    Returns:
        RankingsResponse with ordered rankings
    """
    logging.info(f"Getting rankings for {sport}")

    is_womens = sport == "ncaaw_basketball"
    data, last_modified = blob_service.get_top25(is_womens)

    # Transform { team: rating } dict to ranked array
    sorted_teams = sorted(data.items(), key=lambda x: x[1], reverse=True)
    rankings = [
        RankingEntry(rank=i + 1, team=team, rating=round(rating, 2))
        for i, (team, rating) in enumerate(sorted_teams)
    ]

    return RankingsResponse(
        sport=sport,
        updated_at=last_modified,
        rankings=rankings,
    )
