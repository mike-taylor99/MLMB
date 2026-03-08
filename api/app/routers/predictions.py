"""
Predictions router - thin route handlers.

All business logic lives in app.services.predictions.
Endpoints:
- POST /predictions - Create a new prediction
- GET /predictions - Query prediction history
- GET /predictions/{id} - Get a single prediction by ID
- POST /predictions/batch - Batch predictions
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query

from app.constants import VALID_SPORTS
from app.dependencies import (
    BlobServiceDep,
    PredictionsStoreDep,
    RequireAuthDep,
    SettingsDep,
    get_user_id,
)
from app.exceptions import (
    InvalidSportError,
    PredictionNotFoundError,
    BatchTooLargeError,
    ValidationError,
)
from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionListResponse,
    BatchRequest,
    BatchResponse,
)
from app.services import (
    create_prediction,
    create_batch_predictions,
    get_prediction_by_id,
    list_predictions,
)
from app.tasks import (
    write_prediction,
    write_predictions_bulk,
    link_user_prediction,
    link_user_predictions_bulk,
)


router = APIRouter(prefix="/predictions")


# =============================================================================
# POST /predictions - Create a new prediction
# =============================================================================


@router.post("", response_model=PredictionResponse)
async def create_prediction_endpoint(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    blob_service: BlobServiceDep,
    predictions_store: PredictionsStoreDep,
    auth: RequireAuthDep,
) -> PredictionResponse:
    """
    Create a new prediction for a matchup.

    Predictions are cached based on content hash. Identical requests return
    the same ID instantly from cache.
    """
    try:
        response, cosmos_record = create_prediction(
            request=request,
            blob_service=blob_service,
            predictions_store=predictions_store,
        )

        # Queue background write (only if new)
        if cosmos_record:
            background_tasks.add_task(
                write_prediction, predictions_store, cosmos_record
            )

        # Link prediction to user for scoped history
        user_id = get_user_id(auth)
        if user_id:
            background_tasks.add_task(
                link_user_prediction,
                predictions_store,
                user_id,
                response.id,
                request.sport,
            )

        return response

    except ValueError as e:
        raise ValidationError(str(e))


# =============================================================================
# GET /predictions/{id} - Get a single prediction
# =============================================================================


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_endpoint(
    prediction_id: str,
    predictions_store: PredictionsStoreDep,
    _auth: RequireAuthDep,
    sport: str = Query(..., description="Sport code (required)"),
) -> PredictionResponse:
    """Retrieve a prediction by ID."""
    if sport not in VALID_SPORTS:
        raise InvalidSportError(sport)

    prediction = get_prediction_by_id(prediction_id, sport, predictions_store)
    if not prediction:
        raise PredictionNotFoundError(prediction_id)

    return prediction


# =============================================================================
# GET /predictions - List predictions with pagination
# =============================================================================


@router.get("", response_model=PredictionListResponse)
async def list_predictions_endpoint(
    predictions_store: PredictionsStoreDep,
    settings: SettingsDep,
    auth: RequireAuthDep,
    sport: str = Query(..., description="Sport code (required)"),
    limit: Optional[int] = Query(None, ge=1),
    before_id: Optional[str] = Query(None),
    after_id: Optional[str] = Query(None),
) -> PredictionListResponse:
    """Query prediction history scoped to the current user."""
    # Apply defaults from settings
    if limit is None:
        limit = settings.default_page_limit
    limit = min(limit, settings.max_page_limit)

    if sport not in VALID_SPORTS:
        raise InvalidSportError(sport)

    user_id = get_user_id(auth)

    return list_predictions(
        predictions_store=predictions_store,
        sport=sport,
        limit=limit,
        user_id=user_id,
        before_id=before_id,
        after_id=after_id,
    )


# =============================================================================
# POST /predictions/batch - Batch predictions
# =============================================================================


@router.post("/batch", response_model=BatchResponse)
async def batch_predictions_endpoint(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
    blob_service: BlobServiceDep,
    predictions_store: PredictionsStoreDep,
    settings: SettingsDep,
    auth: RequireAuthDep,
) -> BatchResponse:
    """
    Process multiple predictions in a single request.

    Models are loaded once and reused. Results are cached to Cosmos DB
    in the background. Order is preserved - response[i] matches request[i].
    """
    if len(request.input) > settings.max_batch_size:
        raise BatchTooLargeError(len(request.input), settings.max_batch_size)

    if len(request.input) == 0:
        return BatchResponse(output=[])

    results, cosmos_records = create_batch_predictions(
        requests=request.input,
        blob_service=blob_service,
    )

    # Queue background bulk write
    if cosmos_records:
        background_tasks.add_task(
            write_predictions_bulk, predictions_store, cosmos_records
        )

    # Link predictions to user for scoped history
    user_id = get_user_id(auth)
    if user_id:
        # Group successful prediction IDs by sport (batch may span sports)
        ids_by_sport: dict[str, list[str]] = {}
        for req_item, result in zip(request.input, results):
            if hasattr(result, "id") and getattr(result, "type", None) == "prediction":
                ids_by_sport.setdefault(req_item.sport, []).append(result.id)

        for sport, prediction_ids in ids_by_sport.items():
            background_tasks.add_task(
                link_user_predictions_bulk,
                predictions_store,
                user_id,
                prediction_ids,
                sport,
            )

    return BatchResponse(output=results)
