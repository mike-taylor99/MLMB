"""
Analysis service — generates AI-powered matchup analyses.

Orchestrates predictions, stats extraction, caching, and the Foundry
agent call behind a single ``run_analysis()`` entry-point.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.schemas import (
    AnalysisPredictionSummary,
    AnalysisResponse,
    PredictionRequest,
    PredictionResponse,
)
from app.services.predictions import create_prediction
from app.services.teams import _CURATED_STATS_MAP, _DEFAULT_SPAN
from shared.agent_service import AgentService
from shared.blob_service import BlobStorageService
from shared.predictions_store import PredictionsStore


logger = logging.getLogger(__name__)

# All spans the analysis should cover
_ANALYSIS_SPANS = [3, 5, 7]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _generate_analysis_id(prediction_ids: List[str]) -> str:
    """
    Deterministic analysis ID derived from the sorted prediction IDs.

    Because each prediction ID already encodes team keys, lastPlayed,
    span, neutral, sport, model, and model version, the analysis ID
    automatically changes whenever any underlying input changes.
    """
    canonical = "|".join(sorted(prediction_ids))
    hash_value = hashlib.sha256(canonical.encode()).hexdigest()[:32]
    return f"analysis_{hash_value}"


def _extract_curated_stats(
    team_key: str,
    sport: str,
    blob_service: BlobStorageService,
) -> Tuple[Dict[str, float], str]:
    """
    Extract curated stats and lastPlayed for a team.

    Returns:
        (stats_dict, last_played_date)

    Raises:
        ValueError: If team stats are unavailable.
    """
    is_womens = sport == "ncaaw_basketball"
    all_stats = blob_service.get_team_stats(is_womens)

    span_data = all_stats.get(_DEFAULT_SPAN, {})
    team_data = span_data.get(team_key)
    if not team_data:
        raise ValueError(f"Stats unavailable for team '{team_key}' in {sport}")

    features = all_stats.get("_meta", {}).get("features", [])
    raw_stats = team_data.get("stats", [])

    if not features or len(features) != len(raw_stats):
        raise ValueError(f"Feature/stats length mismatch for '{team_key}'")

    stats: Dict[str, float] = {}
    for i, feat_name in enumerate(features):
        if feat_name in _CURATED_STATS_MAP:
            stats[_CURATED_STATS_MAP[feat_name]] = round(raw_stats[i], 4)

    last_played = team_data.get("lastPlayed", "")
    return stats, last_played


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def run_analysis(
    home_team: str,
    away_team: str,
    sport: str,
    neutral: bool,
    blob_service: BlobStorageService,
    predictions_store: PredictionsStore,
    agent_service: AgentService,
) -> Tuple[AnalysisResponse, List[dict], Optional[dict], List[str]]:
    """
    Run a full matchup analysis.

    1.  Generate predictions (6 for neutral, 3 for home/away).
    2.  Derive a deterministic analysis ID from the prediction IDs.
    3.  Check Cosmos cache — return immediately on hit.
    4.  On miss: extract curated stats, call the Foundry agent,
        persist the analysis record, and return.

    Args:
        home_team: Home team key.
        away_team: Away team key.
        sport: Sport code.
        neutral: Neutral-site analysis flag.
        blob_service: Blob storage service.
        predictions_store: Cosmos predictions store.
        agent_service: Foundry agent service.

    Returns:
        Tuple of (AnalysisResponse, list of new Cosmos prediction records,
        analysis Cosmos record or None if cache hit, list of all prediction IDs).

    Raises:
        ValueError: If a team is not found or stats are unavailable.
    """
    logger.info(
        f"Running analysis: {home_team} vs {away_team} "
        f"(sport={sport}, neutral={neutral})"
    )

    # ------------------------------------------------------------------
    # 1. Generate predictions
    # ------------------------------------------------------------------
    prediction_responses: List[PredictionResponse] = []
    cosmos_records: List[dict] = []

    orientations = (
        [(home_team, away_team), (away_team, home_team)]
        if neutral
        else [(home_team, away_team)]
    )

    for h, a in orientations:
        for span in _ANALYSIS_SPANS:
            req = PredictionRequest(
                home_team=h,
                away_team=a,
                span=span,
                neutral=neutral,
                sport=sport,
                model="ensemble",
            )
            resp, record = create_prediction(req, blob_service, predictions_store)
            prediction_responses.append(resp)
            if record:
                cosmos_records.append(record)

    prediction_ids = [p.id for p in prediction_responses]

    # ------------------------------------------------------------------
    # 2. Derive analysis ID & check cache
    # ------------------------------------------------------------------
    analysis_id = _generate_analysis_id(prediction_ids)

    cached = predictions_store.get_analysis(analysis_id, sport)
    if cached:
        logger.info(f"Analysis cache hit: {analysis_id}")
        return (
            _analysis_from_cosmos(cached),
            cosmos_records,
            None,
            prediction_ids,
        )

    logger.info(f"Analysis cache miss: {analysis_id}")

    # ------------------------------------------------------------------
    # 3. Extract curated stats
    # ------------------------------------------------------------------
    home_stats, home_last_played = _extract_curated_stats(
        home_team, sport, blob_service
    )
    away_stats, away_last_played = _extract_curated_stats(
        away_team, sport, blob_service
    )

    # ------------------------------------------------------------------
    # 4. Build prediction summaries for agent prompt & response
    # ------------------------------------------------------------------
    pred_summaries = [
        AnalysisPredictionSummary(
            span=p.span,
            home_team=p.home_team,
            away_team=p.away_team,
            home_win_probability=p.home_win_probability,
            neutral=p.neutral,
        )
        for p in prediction_responses
    ]

    pred_dicts = [s.model_dump() for s in pred_summaries]

    # ------------------------------------------------------------------
    # 5. Call Foundry agent
    # ------------------------------------------------------------------
    analysis_text = agent_service.analyze_matchup(
        home_team=home_team,
        away_team=away_team,
        sport=sport,
        neutral=neutral,
        predictions=pred_dicts,
        home_stats=home_stats,
        away_stats=away_stats,
        home_last_played=home_last_played,
        away_last_played=away_last_played,
    )

    now = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 6. Build response
    # ------------------------------------------------------------------
    response = AnalysisResponse(
        id=analysis_id,
        home_team=home_team,
        away_team=away_team,
        sport=sport,
        neutral=neutral,
        predictions=pred_summaries,
        home_stats=home_stats,
        away_stats=away_stats,
        home_last_played=home_last_played,
        away_last_played=away_last_played,
        analysis=analysis_text,
        created_at=now,
    )

    # ------------------------------------------------------------------
    # 7. Build Cosmos record for cache persistence
    # ------------------------------------------------------------------
    analysis_record = {
        "id": analysis_id,
        "type": "analysis",
        "sport": sport,
        "home_team": home_team,
        "away_team": away_team,
        "neutral": neutral,
        "prediction_ids": prediction_ids,
        "home_last_played": home_last_played,
        "away_last_played": away_last_played,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "predictions": pred_dicts,
        "analysis": analysis_text,
        "created_at": now,
    }

    return response, cosmos_records, analysis_record, prediction_ids


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def get_analysis_by_id(
    analysis_id: str,
    sport: str,
    predictions_store: PredictionsStore,
) -> Optional[AnalysisResponse]:
    """
    Get a cached analysis by ID.

    Args:
        analysis_id: The analysis content-hash ID.
        sport: Sport code (partition key).
        predictions_store: Cosmos DB store.

    Returns:
        AnalysisResponse or None if not found.
    """
    logger.info(f"Getting analysis: {analysis_id}")
    record = predictions_store.get_analysis(analysis_id, sport)
    if not record:
        return None
    return _analysis_from_cosmos(record)


def _analysis_from_cosmos(record: dict) -> AnalysisResponse:
    """Reconstruct an AnalysisResponse from a cached Cosmos record."""
    return AnalysisResponse(
        id=record["id"],
        home_team=record["home_team"],
        away_team=record["away_team"],
        sport=record["sport"],
        neutral=record["neutral"],
        predictions=[
            AnalysisPredictionSummary(**p) for p in record["predictions"]
        ],
        home_stats=record["home_stats"],
        away_stats=record["away_stats"],
        home_last_played=record["home_last_played"],
        away_last_played=record["away_last_played"],
        analysis=record["analysis"],
        created_at=record["created_at"],
    )
