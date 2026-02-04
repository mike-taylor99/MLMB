"""Pydantic models for API request/response validation.

All models use strict typing with Literal types for enum-like fields.
"""

from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.constants import VALID_SPORTS, VALID_MODELS, VALID_SPANS, SportType, ModelTypeStr, SpanType


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
    status: Literal["healthy", "unhealthy"] = Field(default="healthy", description="Service health status")


# =============================================================================
# Prediction Models
# =============================================================================

class PredictionRequest(BaseModel):
    """Request body for creating a prediction."""
    home_team: str = Field(..., min_length=1, description="Home team key (e.g., 'duke')")
    away_team: str = Field(..., min_length=1, description="Away team key (e.g., 'connecticut')")
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
    type: Literal["prediction"] = Field(default="prediction", description="Response type")
    model: str = Field(..., description="Model used for prediction")
    span: int = Field(..., description="Moving average span used")
    sport: str = Field(..., description="Sport code")
    home_team: str = Field(..., description="Home team key")
    away_team: str = Field(..., description="Away team key")
    home_last_played: Optional[str] = Field(None, description="Home team's last game date (YYYY-MM-DD)")
    away_last_played: Optional[str] = Field(None, description="Away team's last game date (YYYY-MM-DD)")
    neutral: bool = Field(..., description="Whether neutral site")
    home_win_probability: float = Field(..., ge=0.0, le=1.0, description="Probability home team wins (0-1)")
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
    input: List[PredictionRequest] = Field(..., min_length=1, description="List of prediction requests")


class BatchResponse(BaseModel):
    """Response for batch predictions."""
    type: Literal["prediction_batch"] = Field(default="prediction_batch", description="Response type")
    output: List[Union[PredictionResponse, ErrorResponse]] = Field(
        ..., description="List of prediction results (or errors)"
    )


# =============================================================================
# Team Models
# =============================================================================

class TeamResponse(BaseModel):
    """Response for a single team."""
    id: str = Field(..., description="Team key (e.g., 'duke')")
    type: Literal["team"] = Field(default="team", description="Response type")
    school: str = Field(..., description="School short name (e.g., 'Duke')")
    name: str = Field(..., description="Full school name")
    location: str = Field(..., description="City, State")
    ncaa_key: Optional[str] = Field(None, description="NCAA identifier")
    color: Optional[str] = Field(None, description="Primary color hex code")
    sports: List[str] = Field(..., description="List of sports this team has programs for")

    @classmethod
    def from_blob_record(cls, record: dict) -> "TeamResponse":
        """Create a TeamResponse from a blob storage record."""
        sports = []
        if record.get("has_mens_program"):
            sports.append("ncaam_basketball")
        if record.get("has_womens_program"):
            sports.append("ncaaw_basketball")

        return cls(
            id=record["key"],
            school=record["school"],
            name=record["name"],
            location=record["location"],
            ncaa_key=record.get("ncaa_key"),
            color=record.get("color"),
            sports=sports,
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
