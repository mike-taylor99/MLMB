"""
Bracket service — business logic for bracket CRUD.
"""
import logging
from typing import Dict, List, Optional

from app.exceptions import (
    BracketLockedError,
    BracketLimitError,
    TournamentNotFoundError,
)
from shared.bracket_store import BracketStore
from shared.tournament_store import TournamentStore

logger = logging.getLogger(__name__)

MAX_BRACKETS_PER_TOURNAMENT = 10


def create_bracket(
    user_id: str,
    tournament_id: str,
    name: str,
    picks: Dict[str, str],
    bracket_store: BracketStore,
    tournament_store: TournamentStore,
) -> dict:
    """
    Create a new bracket for a user.

    Validates:
    - Tournament exists
    - Tournament is not locked
    - User hasn't exceeded bracket limit
    """
    tournament = tournament_store.get_tournament(tournament_id)
    if tournament is None:
        raise TournamentNotFoundError(tournament_id)

    if tournament["is_locked"]:
        raise BracketLockedError()

    count = bracket_store.count_user_brackets(user_id, tournament_id)
    if count >= MAX_BRACKETS_PER_TOURNAMENT:
        raise BracketLimitError(MAX_BRACKETS_PER_TOURNAMENT)

    return bracket_store.create_bracket(
        user_id=user_id,
        tournament_id=tournament_id,
        name=name,
        picks=picks,
    )


def get_bracket(
    bracket_id: str,
    user_id: str,
    bracket_store: BracketStore,
) -> Optional[dict]:
    """Get a single bracket by ID for a user."""
    return bracket_store.get_bracket(bracket_id, user_id)


def get_bracket_public(
    bracket_id: str,
    bracket_store: BracketStore,
) -> Optional[dict]:
    """Get a bracket by ID regardless of owner (read-only sharing)."""
    return bracket_store.get_bracket_public(bracket_id)


def list_brackets(
    user_id: str,
    bracket_store: BracketStore,
    tournament_id: Optional[str] = None,
) -> List[dict]:
    """List all brackets for a user, optionally filtered by tournament."""
    return bracket_store.list_brackets(user_id, tournament_id)


def update_bracket(
    bracket_id: str,
    user_id: str,
    bracket_store: BracketStore,
    tournament_store: TournamentStore,
    name: Optional[str] = None,
    picks: Optional[Dict[str, str]] = None,
) -> Optional[dict]:
    """
    Update a bracket's name and/or picks.

    Validates:
    - Bracket exists and belongs to user
    - If updating picks, tournament must not be locked
    """
    existing = bracket_store.get_bracket(bracket_id, user_id)
    if existing is None:
        return None

    # Only enforce lock when picks are being changed
    if picks is not None:
        tournament = tournament_store.get_tournament(existing["tournament_id"])
        if tournament and tournament["is_locked"]:
            raise BracketLockedError()

    return bracket_store.update_bracket(
        bracket_id=bracket_id,
        user_id=user_id,
        name=name,
        picks=picks,
    )


def delete_bracket(
    bracket_id: str,
    user_id: str,
    bracket_store: BracketStore,
) -> bool:
    """Delete a bracket. Returns True if deleted."""
    return bracket_store.delete_bracket(bracket_id, user_id)
