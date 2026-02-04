"""
Prediction service - business logic for predictions.

Handles prediction creation, caching, and batch processing.
Returns Pydantic models, not raw dicts.
"""

import logging
from typing import Optional, Union

from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionListResponse,
    ErrorResponse,
    ErrorDetail,
)
from shared.blob_service import BlobStorageService
from shared.predictions_store import PredictionsStore
from shared.ml_runner import (
    MODEL_NAME_MAP,
    run_prediction as _run_prediction,
    preload_models,
    preload_model_versions,
    preload_stats,
)


def _get_model_version_string(
    blob_service: BlobStorageService,
    sport: str,
    span: int,
    model_type: str,
) -> str:
    """Get the model version string for ID generation."""
    if model_type == "ensemble":
        versions = []
        for mt in sorted(MODEL_NAME_MAP.keys()):
            v = blob_service.get_model_version(sport, span, mt)
            versions.append(f"{mt}:{v}")
        return "|".join(versions)
    return blob_service.get_model_version(sport, span, model_type)


def create_prediction(
    request: PredictionRequest,
    blob_service: BlobStorageService,
    predictions_store: PredictionsStore,
) -> tuple[PredictionResponse, Optional[dict]]:
    """
    Create a prediction, checking cache first.

    Args:
        request: The prediction request
        blob_service: Blob storage service for models/stats
        predictions_store: Cosmos DB store for caching

    Returns:
        Tuple of (PredictionResponse, cosmos_record or None if cached)

    Raises:
        ValueError: If team not found or other validation error
    """
    logging.info(f"Creating prediction: {request.home_team} vs {request.away_team}")
    is_womens = request.sport == "ncaaw_basketball"

    # Get team stats for cache key generation
    matchup_stats = blob_service.get_matchup_stats(
        request.home_team, request.away_team, request.span, is_womens
    )
    home_last_played = matchup_stats["team1"]["lastPlayed"]
    away_last_played = matchup_stats["team2"]["lastPlayed"]

    # Get model version for prediction ID
    model_version = _get_model_version_string(
        blob_service, request.sport, request.span, request.model
    )

    # Generate prediction ID (content-hash based)
    prediction_id = PredictionsStore.generate_prediction_id(
        home_team=request.home_team,
        away_team=request.away_team,
        home_last_played=home_last_played,
        away_last_played=away_last_played,
        span=request.span,
        neutral=request.neutral,
        sport=request.sport,
        model=request.model,
        model_version=model_version,
    )

    # Check cache (point read)
    cached = predictions_store.get_prediction(prediction_id, request.sport)
    if cached:
        logging.info(f"Cache hit: {prediction_id}")
        return PredictionResponse.from_cosmos_record(cached), None

    logging.info(f"Cache miss: {prediction_id}")

    # Run prediction
    result, cosmos_record = _run_prediction(
        blob_service=blob_service,
        home_team=request.home_team,
        away_team=request.away_team,
        span=request.span,
        sport=request.sport,
        model_type=request.model,
        neutral=request.neutral,
    )

    return PredictionResponse.from_prediction_result(result), cosmos_record


def get_prediction_by_id(
    prediction_id: str,
    sport: str,
    predictions_store: PredictionsStore,
) -> Optional[PredictionResponse]:
    """
    Get a prediction by ID.

    Args:
        prediction_id: The prediction ID
        sport: Sport code (used as partition key)
        predictions_store: Cosmos DB store

    Returns:
        PredictionResponse or None if not found
    """
    logging.info(f"Getting prediction: {prediction_id}")
    record = predictions_store.get_prediction(prediction_id, sport)
    if not record:
        return None
    return PredictionResponse.from_cosmos_record(record)


def create_batch_predictions(
    requests: list[PredictionRequest],
    blob_service: BlobStorageService,
) -> tuple[list[Union[PredictionResponse, ErrorResponse]], list[dict]]:
    """
    Create multiple predictions in a batch.

    Models are loaded once and reused for efficiency.

    Args:
        requests: List of prediction requests
        blob_service: Blob storage service for models/stats

    Returns:
        Tuple of (results list matching input order, cosmos_records to write)
    """
    if not requests:
        return [], []

    # Build cache keys
    indexed_requests = [
        {"index": i, "request": req, "is_womens": req.sport == "ncaaw_basketball"}
        for i, req in enumerate(requests)
    ]

    # Pre-load models and stats
    model_keys = {
        (item["request"].sport, item["request"].span, item["request"].model)
        for item in indexed_requests
    }
    stats_keys = set()
    for item in indexed_requests:
        req = item["request"]
        stats_keys.add((req.home_team, req.span, item["is_womens"]))
        stats_keys.add((req.away_team, req.span, item["is_womens"]))

    logging.info(f"Loading {len(model_keys)} model groups, {len(stats_keys)} team stats")

    models_cache = preload_models(blob_service, model_keys)
    model_versions_cache = preload_model_versions(blob_service, model_keys)
    stats_cache = preload_stats(blob_service, stats_keys)

    # Run predictions
    results: list[Union[PredictionResponse, ErrorResponse]] = [None] * len(indexed_requests)  # type: ignore
    cosmos_records: list[dict] = []

    for item in indexed_requests:
        req = item["request"]
        try:
            result, record = _run_prediction(
                blob_service=blob_service,
                home_team=req.home_team,
                away_team=req.away_team,
                span=req.span,
                sport=req.sport,
                model_type=req.model,
                neutral=req.neutral,
                models_cache=models_cache,
                stats_cache=stats_cache,
                model_versions_cache=model_versions_cache,
            )
            results[item["index"]] = PredictionResponse.from_prediction_result(result)
            if record:
                cosmos_records.append(record)
        except Exception as e:
            logging.error(f"Error predicting {req.home_team} vs {req.away_team}: {e}")
            results[item["index"]] = ErrorResponse(
                error=ErrorDetail(code="prediction_error", message=str(e))
            )

    return results, cosmos_records


def list_predictions(
    predictions_store: PredictionsStore,
    sport: str,
    limit: int,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None,
) -> PredictionListResponse:
    """
    Query prediction history with pagination.

    Args:
        predictions_store: Cosmos DB store
        sport: Sport code (required)
        limit: Maximum results to return
        home_team: Optional filter
        away_team: Optional filter
        start_date: Optional filter (YYYY-MM-DD)
        end_date: Optional filter (YYYY-MM-DD)
        before_id: Cursor for backward pagination
        after_id: Cursor for forward pagination

    Returns:
        PredictionListResponse with paginated results
    """
    logging.info(f"Querying predictions (sport={sport}, limit={limit})")

    # Query one extra to determine has_more
    records = predictions_store.query_predictions(
        sport=sport,
        home_team=home_team,
        away_team=away_team,
        start_date=start_date,
        end_date=end_date,
        limit=limit + 1,
        before_id=before_id,
        after_id=after_id,
    )

    has_more = len(records) > limit
    if has_more:
        records = records[:limit]

    predictions = [PredictionResponse.from_cosmos_record(r) for r in records]

    return PredictionListResponse(
        data=predictions,
        first_id=predictions[0].id if predictions else None,
        last_id=predictions[-1].id if predictions else None,
        has_more=has_more,
    )
