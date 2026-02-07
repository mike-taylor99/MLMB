"""
Team service - business logic for teams.

Handles team retrieval and filtering.
"""

import logging
from typing import Optional

from app.schemas import TeamResponse, TeamsListResponse
from shared.blob_service import BlobStorageService


def get_team_by_id(team_id: str, blob_service: BlobStorageService) -> Optional[TeamResponse]:
    """
    Get a single team by ID.

    Args:
        team_id: The team key
        blob_service: Blob storage service

    Returns:
        TeamResponse or None if not found
    """
    teams_data, _ = blob_service.get_teams()
    record = next((t for t in teams_data if t["key"] == team_id), None)

    if not record:
        return None

    return TeamResponse.from_record(record)


def list_teams(
    blob_service: BlobStorageService,
    sport: Optional[str] = None,
    limit: int = 100,
    after_id: Optional[str] = None,
    before_id: Optional[str] = None,
) -> TeamsListResponse:
    """
    List teams with cursor-based pagination.

    Args:
        blob_service: Blob storage service
        sport: Optional sport filter
        limit: Maximum number of results
        after_id: Get teams after this ID
        before_id: Get teams before this ID

    Returns:
        TeamsListResponse with paginated results
    """
    logging.info(f"Listing teams (sport={sport}, limit={limit})")

    teams_data, _ = blob_service.get_teams()

    # Apply sport filter
    if sport == "ncaam_basketball":
        filtered = [t for t in teams_data if t.get("has_mens_program")]
    elif sport == "ncaaw_basketball":
        filtered = [t for t in teams_data if t.get("has_womens_program")]
    else:
        filtered = teams_data

    # Apply cursor pagination
    start_index = 0
    end_index = len(filtered)

    if after_id:
        for i, team in enumerate(filtered):
            if team["key"] == after_id:
                start_index = i + 1
                break

    if before_id:
        for i, team in enumerate(filtered):
            if team["key"] == before_id:
                end_index = i
                break

    cursor_filtered = filtered[start_index:end_index]

    # Apply limit
    if before_id and not after_id:
        paginated = cursor_filtered[-limit:] if len(cursor_filtered) > limit else cursor_filtered
    else:
        paginated = cursor_filtered[:limit]

    has_more = len(cursor_filtered) > limit

    # Convert to response models
    teams = [TeamResponse.from_record(t) for t in paginated]

    return TeamsListResponse(
        data=teams,
        first_id=teams[0].id if teams else None,
        last_id=teams[-1].id if teams else None,
        has_more=has_more,
    )
