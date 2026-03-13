"""
Team service - business logic for teams.

Handles team retrieval and filtering.
"""

import logging
from typing import Dict, Optional

from app.schemas import (
    TeamDetailResponse,
    TeamLatestStats,
    TeamResponse,
    TeamsListResponse,
)
from shared.blob_service import BlobStorageService

# Feature name → API key mapping for curated stats.
# Covers efficiency, four factors, shooting, and their defensive mirrors.
_CURATED_STATS_MAP: Dict[str, str] = {
    # Efficiency
    "ORtg_SMA": "ortg",
    "DRtg_SMA": "drtg",
    "Pace_SMA": "pace",
    # Four Factors – offense
    "eFG%_SMA": "efg_pct",
    "TOV%_SMA": "tov_pct",
    "ORB%_SMA": "orb_pct",
    "FT/FGA_SMA": "fta_rate",
    # Four Factors – defense
    "def_eFG%_SMA": "def_efg_pct",
    "def_TOV%_SMA": "def_tov_pct",
    "def_ORB%_SMA": "def_orb_pct",
    "def_FT/FGA_SMA": "def_fta_rate",
    # Shooting – offense
    "FG%_SMA": "fg_pct",
    "3P%_SMA": "three_pct",
    "2P%_SMA": "two_pct",
    "FT%_SMA": "ft_pct",
    "TS%_SMA": "ts_pct",
    # Shooting – defense
    "def_FG%_SMA": "def_fg_pct",
    "def_3P%_SMA": "def_three_pct",
    "def_2P%_SMA": "def_two_pct",
    "def_FT%_SMA": "def_ft_pct",
    # Miscellaneous
    "STL%_SMA": "stl_pct",
    "BLK%_SMA": "blk_pct",
    "3PAr_SMA": "three_pa_rate",
}

_DEFAULT_SPAN = "5"


def _extract_latest_stats(
    team_key: str,
    sport: str,
    blob_service: BlobStorageService,
) -> Optional[TeamLatestStats]:
    """Extract curated latest stats for a team in a specific sport."""
    is_womens = sport == "ncaaw_basketball"

    try:
        all_stats = blob_service.get_team_stats(is_womens)
    except Exception:
        logging.debug(f"Team stats unavailable for {sport}")
        return None

    span_data = all_stats.get(_DEFAULT_SPAN, {})
    team_data = span_data.get(team_key)
    if not team_data:
        return None

    features = all_stats.get("_meta", {}).get("features", [])
    raw_stats = team_data.get("stats", [])

    if not features or len(features) != len(raw_stats):
        return None

    # Build curated stats dict from feature vector
    stats: Dict[str, float] = {}
    for i, feat_name in enumerate(features):
        if feat_name in _CURATED_STATS_MAP:
            stats[_CURATED_STATS_MAP[feat_name]] = round(raw_stats[i], 4)

    return TeamLatestStats(
        sport=sport,
        last_played=team_data.get("lastPlayed", ""),
        stats=stats,
    )


def get_team_by_id(
    team_id: str, blob_service: BlobStorageService
) -> Optional[TeamResponse]:
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


def get_team_detail(
    team_id: str, blob_service: BlobStorageService
) -> Optional[TeamDetailResponse]:
    """
    Get a single team by ID with latest stats included.

    Args:
        team_id: The team key
        blob_service: Blob storage service

    Returns:
        TeamDetailResponse or None if not found
    """
    team = get_team_by_id(team_id, blob_service)
    if not team:
        return None

    # Collect latest stats for each sport the team participates in
    latest = []
    for sport in team.sports:
        sport_stats = _extract_latest_stats(team_id, sport, blob_service)
        if sport_stats:
            latest.append(sport_stats)

    return TeamDetailResponse(
        **team.model_dump(),
        latest=latest if latest else None,
    )


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
        paginated = (
            cursor_filtered[-limit:]
            if len(cursor_filtered) > limit
            else cursor_filtered
        )
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
