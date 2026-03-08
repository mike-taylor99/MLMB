"""
Brackets router — authenticated CRUD for user brackets.

Endpoints:
- POST   /brackets              — Create a new bracket
- GET    /brackets               — List user's brackets
- GET    /brackets/{bracket_id}  — Get a single bracket
- PUT    /brackets/{bracket_id}  — Update a bracket
- DELETE /brackets/{bracket_id}  — Delete a bracket
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.dependencies import (
    BracketStoreDep,
    RequireAuthDep,
    TournamentStoreDep,
    get_user_id,
)
from app.exceptions import (
    AuthenticationError,
    BracketNotFoundError,
)
from app.schemas import (
    BracketListResponse,
    BracketResponse,
    CreateBracketRequest,
    UpdateBracketRequest,
)
from app.services import (
    create_bracket,
    get_bracket,
    list_brackets,
    update_bracket,
    delete_bracket,
)

router = APIRouter(prefix="/brackets")


def _require_user_id(principal: dict) -> str:
    """Extract user_id from principal; raise if not a real user."""
    user_id = get_user_id(principal)
    if user_id is None:
        raise AuthenticationError("User identity required for bracket operations")
    return user_id


# =============================================================================
# POST /brackets — Create a new bracket
# =============================================================================


@router.post("", response_model=BracketResponse, status_code=201)
async def create_bracket_endpoint(
    request: CreateBracketRequest,
    auth: RequireAuthDep,
    bracket_store: BracketStoreDep,
    tournament_store: TournamentStoreDep,
) -> BracketResponse:
    """Create a new bracket for the authenticated user."""
    user_id = _require_user_id(auth)
    record = create_bracket(
        user_id=user_id,
        tournament_id=request.tournament_id,
        name=request.name,
        picks=request.picks,
        bracket_store=bracket_store,
        tournament_store=tournament_store,
    )
    return BracketResponse.from_cosmos_record(record)


# =============================================================================
# GET /brackets — List user's brackets
# =============================================================================


@router.get("", response_model=BracketListResponse)
async def list_brackets_endpoint(
    auth: RequireAuthDep,
    bracket_store: BracketStoreDep,
    tournament_id: Optional[str] = Query(None, description="Filter by tournament"),
) -> BracketListResponse:
    """List all brackets for the authenticated user."""
    user_id = _require_user_id(auth)
    records = list_brackets(user_id, bracket_store, tournament_id)
    return BracketListResponse(
        data=[BracketResponse.from_cosmos_record(r) for r in records],
    )


# =============================================================================
# GET /brackets/{bracket_id} — Get a single bracket
# =============================================================================


@router.get("/{bracket_id}", response_model=BracketResponse)
async def get_bracket_endpoint(
    bracket_id: str,
    auth: RequireAuthDep,
    bracket_store: BracketStoreDep,
) -> BracketResponse:
    """Get a single bracket by ID for the authenticated user."""
    user_id = _require_user_id(auth)
    record = get_bracket(bracket_id, user_id, bracket_store)
    if record is None:
        raise BracketNotFoundError(bracket_id)
    return BracketResponse.from_cosmos_record(record)


# =============================================================================
# PUT /brackets/{bracket_id} — Update a bracket
# =============================================================================


@router.put("/{bracket_id}", response_model=BracketResponse)
async def update_bracket_endpoint(
    bracket_id: str,
    request: UpdateBracketRequest,
    auth: RequireAuthDep,
    bracket_store: BracketStoreDep,
    tournament_store: TournamentStoreDep,
) -> BracketResponse:
    """Update a bracket's name and/or picks."""
    user_id = _require_user_id(auth)
    record = update_bracket(
        bracket_id=bracket_id,
        user_id=user_id,
        bracket_store=bracket_store,
        tournament_store=tournament_store,
        name=request.name,
        picks=request.picks,
    )
    if record is None:
        raise BracketNotFoundError(bracket_id)
    return BracketResponse.from_cosmos_record(record)


# =============================================================================
# DELETE /brackets/{bracket_id} — Delete a bracket
# =============================================================================


@router.delete("/{bracket_id}", status_code=204)
async def delete_bracket_endpoint(
    bracket_id: str,
    auth: RequireAuthDep,
    bracket_store: BracketStoreDep,
) -> None:
    """Delete a bracket."""
    user_id = _require_user_id(auth)
    deleted = delete_bracket(bracket_id, user_id, bracket_store)
    if not deleted:
        raise BracketNotFoundError(bracket_id)
