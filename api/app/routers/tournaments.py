"""
Tournaments router — public endpoints for tournament definitions.

Endpoints:
- GET /tournaments                              — List all available tournaments
- GET /tournaments/{id}                         — Get a full tournament definition
- GET /tournaments/{id}/brackets/{bracket_id}   — View any bracket (public, read-only)
"""

from fastapi import APIRouter

from app.dependencies import BracketStoreDep, TournamentStoreDep
from app.exceptions import BracketNotFoundError, TournamentNotFoundError
from app.schemas import (
    BracketResponse,
    TournamentListResponse,
    TournamentResponse,
    TournamentSummary,
)
from app.services import list_tournaments, get_tournament, get_bracket_public

router = APIRouter(prefix="/tournaments")


# =============================================================================
# GET /tournaments — List all tournaments
# =============================================================================


@router.get("", response_model=TournamentListResponse)
async def list_tournaments_endpoint(
    tournament_store: TournamentStoreDep,
) -> TournamentListResponse:
    """List all available tournaments with summary info."""
    items = list_tournaments(tournament_store)
    return TournamentListResponse(
        data=[TournamentSummary(**t) for t in items],
    )


# =============================================================================
# GET /tournaments/{tournament_id} — Get full tournament definition
# =============================================================================


@router.get("/{tournament_id}", response_model=TournamentResponse)
async def get_tournament_endpoint(
    tournament_id: str,
    tournament_store: TournamentStoreDep,
) -> TournamentResponse:
    """Get a full tournament definition including structure and results."""
    tournament = get_tournament(tournament_id, tournament_store)
    if tournament is None:
        raise TournamentNotFoundError(tournament_id)
    return TournamentResponse(**tournament)


# =============================================================================
# GET /tournaments/{tournament_id}/brackets/{bracket_id} — Public bracket view
# =============================================================================


@router.get(
    "/{tournament_id}/brackets/{bracket_id}",
    response_model=BracketResponse,
)
async def get_public_bracket_endpoint(
    tournament_id: str,
    bracket_id: str,
    tournament_store: TournamentStoreDep,
    bracket_store: BracketStoreDep,
) -> BracketResponse:
    """View any bracket by ID (public, read-only). No authentication required."""
    # Verify the tournament exists
    tournament = get_tournament(tournament_id, tournament_store)
    if tournament is None:
        raise TournamentNotFoundError(tournament_id)

    record = get_bracket_public(bracket_id, bracket_store)
    if record is None or record["tournament_id"] != tournament_id:
        raise BracketNotFoundError(bracket_id)

    return BracketResponse.from_cosmos_record(record)
