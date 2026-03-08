"""Pydantic models for API request/response validation.

All models use strict typing with Literal types for enum-like fields.
"""

from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.constants import (
    VALID_SPORTS,
    VALID_MODELS,
    VALID_SPANS,
    SportType,
    ModelTypeStr,
    SpanType,
)


# =============================================================================
# Common Models
# =============================================================================


class ErrorDetail(BaseModel):
    """Error detail with code and message."""

    code: str = Field(..., description="Error code (e.g., 'validation_error')")
    message: str = Field(..., description="Human-readable error message")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    type: Literal["error"] = Field(default="error", description="Response type")
    error: ErrorDetail


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(
        default="healthy", description="Service health status"
    )


# =============================================================================
# Prediction Models
# =============================================================================


class PredictionRequest(BaseModel):
    """Request body for creating a prediction."""

    home_team: str = Field(
        ..., min_length=1, description="Home team key (e.g., 'duke')"
    )
    away_team: str = Field(
        ..., min_length=1, description="Away team key (e.g., 'connecticut')"
    )
    span: SpanType = Field(default=3, description="Moving average span: 3, 5, or 7")
    neutral: bool = Field(default=False, description="Whether game is at neutral site")
    sport: SportType = Field(default="ncaam_basketball", description="Sport code")
    model: ModelTypeStr = Field(default="ensemble", description="Model type")

    @field_validator("home_team", "away_team", "sport")
    @classmethod
    def lowercase_strings(cls, v: str) -> str:
        return v.strip().lower()


class PredictionResponse(BaseModel):
    """Response for a single prediction."""

    id: str = Field(..., description="Prediction ID")
    type: Literal["prediction"] = Field(
        default="prediction", description="Response type"
    )
    model: str = Field(..., description="Model used for prediction")
    span: int = Field(..., description="Moving average span used")
    sport: str = Field(..., description="Sport code")
    home_team: str = Field(..., description="Home team key")
    away_team: str = Field(..., description="Away team key")
    home_last_played: Optional[str] = Field(
        None, description="Home team's last game date (YYYY-MM-DD)"
    )
    away_last_played: Optional[str] = Field(
        None, description="Away team's last game date (YYYY-MM-DD)"
    )
    neutral: bool = Field(..., description="Whether neutral site")
    home_win_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probability home team wins (0-1)"
    )
    created_at: Optional[str] = Field(None, description="ISO timestamp when created")

    @classmethod
    def from_cosmos_record(cls, record: dict) -> "PredictionResponse":
        """Create a PredictionResponse from a Cosmos DB record."""
        result = record.get("result", {})
        return cls(
            id=record["id"],
            model=record["model"],
            span=record["span"],
            sport=record["sport"],
            home_team=record["home_team"],
            away_team=record["away_team"],
            home_last_played=record.get("home_last_played"),
            away_last_played=record.get("away_last_played"),
            neutral=record["neutral"],
            home_win_probability=result.get("home_win_probability", 0.0),
            created_at=record.get("created_at"),
        )

    @classmethod
    def from_prediction_result(cls, result: dict) -> "PredictionResponse":
        """Create a PredictionResponse from a run_prediction result."""
        return cls(
            id=result["id"],
            model=result["model"],
            span=result["span"],
            sport=result["sport"],
            home_team=result["home_team"],
            away_team=result["away_team"],
            home_last_played=result.get("home_last_played"),
            away_last_played=result.get("away_last_played"),
            neutral=result["neutral"],
            home_win_probability=result["home_win_probability"],
            created_at=result.get("created_at"),
        )


class PredictionListResponse(BaseModel):
    """Response for prediction history queries."""

    data: List[PredictionResponse] = Field(..., description="List of predictions")
    first_id: Optional[str] = Field(None, description="ID of first item")
    last_id: Optional[str] = Field(None, description="ID of last item")
    has_more: bool = Field(..., description="Whether more items exist")


class BatchRequest(BaseModel):
    """Request body for batch predictions."""

    input: List[PredictionRequest] = Field(
        ..., min_length=1, description="List of prediction requests"
    )


class BatchResponse(BaseModel):
    """Response for batch predictions."""

    type: Literal["prediction_batch"] = Field(
        default="prediction_batch", description="Response type"
    )
    output: List[Union[PredictionResponse, ErrorResponse]] = Field(
        ..., description="List of prediction results (or errors)"
    )


# =============================================================================
# Team Models
# =============================================================================


class TeamMeta(BaseModel):
    """Sport-agnostic metadata for a team."""

    school: str = Field(..., description="School short name (e.g., 'Duke')")
    name: str = Field(..., description="Full school name")
    location: str = Field(..., description="City, State")
    ncaa_key: Optional[str] = Field(None, description="NCAA identifier")
    color: Optional[str] = Field(None, description="Primary color hex code")


class TeamResponse(BaseModel):
    """Response for a single team."""

    id: str = Field(..., description="Team key (e.g., 'duke')")
    type: Literal["team"] = Field(default="team", description="Response type")
    sports: List[str] = Field(
        ..., description="List of sports this team has programs for"
    )
    meta: TeamMeta = Field(..., description="Team metadata")

    @classmethod
    def from_record(cls, record: dict) -> "TeamResponse":
        """Create a TeamResponse from a data record."""
        sports = []
        if record.get("has_mens_program"):
            sports.append("ncaam_basketball")
        if record.get("has_womens_program"):
            sports.append("ncaaw_basketball")

        return cls(
            id=record["key"],
            sports=sports,
            meta=TeamMeta(
                school=record["school"],
                name=record.get("name") or record["school"],
                location=record["location"],
                ncaa_key=record.get("ncaa_key"),
                color=record.get("color"),
            ),
        )


class TeamsListResponse(BaseModel):
    """Response for teams list endpoint."""

    data: List[TeamResponse] = Field(..., description="List of teams")
    first_id: Optional[str] = Field(None, description="ID of first team in response")
    last_id: Optional[str] = Field(None, description="ID of last team in response")
    has_more: bool = Field(..., description="Whether more teams exist")


# =============================================================================
# Ranking Models
# =============================================================================


class RankingEntry(BaseModel):
    """A single team's ranking entry."""

    rank: int = Field(..., ge=1, description="Rank position (1-25)")
    team: str = Field(..., description="Team key")
    rating: float = Field(..., description="Rating score")


class RankingsResponse(BaseModel):
    """Response for rankings endpoint."""

    sport: str = Field(..., description="Sport code")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    rankings: List[RankingEntry] = Field(..., description="Ordered list of rankings")


# =============================================================================
# Tournament Models
# =============================================================================


class PlayInGame(BaseModel):
    """A play-in game in the tournament."""

    slot: str = Field(..., description="Slot ID (e.g., 'pi_1')")
    region: str = Field(..., description="Region this play-in feeds into")
    seed: int = Field(..., description="Seed position (11 or 16)")
    teams: List[str] = Field(..., description="Two team keys (empty if TBD)")
    result: Optional[str] = Field(None, description="Winning team key or null")


class RegionDef(BaseModel):
    """A region's seed assignments."""

    name: str = Field(..., description="Display name (e.g., 'South')")
    seeds: dict = Field(..., description="Seed number → team key or pi_* ref")


class FinalFourDef(BaseModel):
    """Final Four matchup configuration."""

    semifinal_1: List[str] = Field(..., description="Two region keys")
    semifinal_2: List[str] = Field(..., description="Two region keys")


class TournamentSummary(BaseModel):
    """Summary info for tournament listing."""

    id: str = Field(..., description="Tournament ID")
    name: str = Field(..., description="Display name")
    year: int = Field(..., description="Tournament year")
    sport: str = Field(..., description="Sport code")
    lock_date: str = Field(..., description="ISO timestamp after which picks are locked")
    is_locked: bool = Field(..., description="Whether bracket edits are locked")


class TournamentListResponse(BaseModel):
    """Response for tournament listing."""

    data: List[TournamentSummary] = Field(..., description="Available tournaments")


class TournamentResponse(BaseModel):
    """Full tournament definition with structure and results."""

    id: str = Field(..., description="Tournament ID")
    type: Literal["tournament"] = Field(default="tournament")
    name: str = Field(..., description="Display name")
    year: int = Field(..., description="Tournament year")
    sport: str = Field(..., description="Sport code")
    lock_date: str = Field(..., description="ISO lock timestamp")
    is_locked: bool = Field(..., description="Whether picks are locked")
    play_in: List[PlayInGame] = Field(..., description="Play-in games")
    regions: dict = Field(..., description="Region definitions")
    final_four: FinalFourDef = Field(..., description="Final Four config")
    results: dict = Field(default_factory=dict, description="Slot → winning team")


# =============================================================================
# Bracket Models
# =============================================================================


class CreateBracketRequest(BaseModel):
    """Request body for creating a bracket."""

    tournament_id: str = Field(..., min_length=1, description="Tournament ID")
    name: str = Field(..., min_length=1, max_length=50, description="Bracket name")
    picks: dict = Field(default_factory=dict, description="Slot → team key picks")


class UpdateBracketRequest(BaseModel):
    """Request body for updating a bracket."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    picks: Optional[dict] = None


class BracketResponse(BaseModel):
    """Response for a single bracket."""

    id: str = Field(..., description="Bracket ID")
    type: Literal["bracket"] = Field(default="bracket")
    tournament_id: str = Field(..., description="Tournament ID")
    name: str = Field(..., description="User-chosen bracket name")
    picks: dict = Field(..., description="Slot → team key picks")
    created_at: str = Field(..., description="ISO creation timestamp")
    updated_at: str = Field(..., description="ISO last-update timestamp")

    @classmethod
    def from_cosmos_record(cls, record: dict) -> "BracketResponse":
        """Create a BracketResponse from a Cosmos DB record."""
        return cls(
            id=record["id"],
            tournament_id=record["tournament_id"],
            name=record["name"],
            picks=record.get("picks", {}),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )


class BracketListResponse(BaseModel):
    """Response for bracket listing."""

    data: List[BracketResponse] = Field(..., description="User's brackets")
