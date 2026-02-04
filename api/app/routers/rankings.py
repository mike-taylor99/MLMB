"""
Rankings router - thin route handlers.

All business logic lives in app.services.rankings.
Endpoints:
- GET /rankings/{sport} - Get top 25 rankings for a sport
"""

from fastapi import APIRouter

from app.constants import VALID_SPORTS
from app.dependencies import BlobServiceDep
from app.exceptions import InvalidSportError
from app.schemas import RankingsResponse
from app.services import get_rankings as get_rankings_service


router = APIRouter(prefix="/rankings")


@router.get("/{sport}", response_model=RankingsResponse)
async def get_rankings(sport: str, blob_service: BlobServiceDep):
    """
    Get top 25 rankings for a sport.

    Rankings are pre-computed from all pairwise predictions and stored in blob storage.
    """
    sport = sport.strip().lower()

    if sport not in VALID_SPORTS:
        raise InvalidSportError(sport)

    return get_rankings_service(sport, blob_service)
