"""
Teams router - thin route handlers.

All business logic lives in app.services.teams.
Endpoints:
- GET /teams - List teams with pagination
- GET /teams/{id} - Get a single team by ID
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.constants import VALID_SPORTS
from app.dependencies import BlobServiceDep, SettingsDep
from app.exceptions import InvalidSportError, TeamNotFoundError
from app.schemas import TeamResponse, TeamsListResponse
from app.services import get_team_by_id, list_teams as list_teams_service


router = APIRouter(prefix="/teams")


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: str, blob_service: BlobServiceDep):
    """Get a single team by ID."""
    team = get_team_by_id(team_id, blob_service)
    if not team:
        raise TeamNotFoundError(team_id)

    return team


@router.get("", response_model=TeamsListResponse)
async def list_teams(
    blob_service: BlobServiceDep,
    settings: SettingsDep,
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: Optional[int] = Query(None, ge=1),
    after_id: Optional[str] = Query(None, description="Get teams after this ID"),
    before_id: Optional[str] = Query(None, description="Get teams before this ID"),
):
    """List teams with cursor-based pagination."""
    # Apply defaults from settings
    if limit is None:
        limit = settings.teams_default_limit
    limit = min(limit, settings.teams_max_limit)

    if sport and sport not in VALID_SPORTS:
        raise InvalidSportError(sport)

    return list_teams_service(
        blob_service=blob_service,
        sport=sport,
        limit=limit,
        after_id=after_id,
        before_id=before_id,
    )
