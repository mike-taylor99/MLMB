"""
Tournament service — business logic for tournament endpoints.
"""
from typing import List, Optional

from shared.tournament_store import TournamentStore


def list_tournaments(tournament_store: TournamentStore) -> List[dict]:
    """List all available tournaments."""
    return tournament_store.list_tournaments()


def get_tournament(
    tournament_id: str, tournament_store: TournamentStore
) -> Optional[dict]:
    """Get a full tournament definition by ID."""
    return tournament_store.get_tournament(tournament_id)
