"""
Predictions API - Consolidated handler for all prediction operations.

Routes:
- POST /predictions - Create a new prediction
- GET /predictions - Query prediction history
- GET /predictions/{id} - Get a single prediction by ID
"""
import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service
from shared.pagination import build_list_response, parse_pagination_params
from shared.predictions_store import get_predictions_store, PredictionsStore
from shared.prediction_service import (
    VALID_MODELS, VALID_SPORTS, MODEL_NAME_MAP,
    validate_prediction_request, run_prediction
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Route requests to appropriate handler based on method and path."""
    prediction_id = req.route_params.get('prediction_id')
    
    if req.method == 'POST':
        return handle_create(req)
    elif req.method == 'GET':
        if prediction_id:
            return handle_get_one(req, prediction_id)
        else:
            return handle_list(req)
    
    return _error_response("method_not_allowed", "Method not allowed", 405)


# =============================================================================
# POST /predictions - Create a new prediction
# =============================================================================

def handle_create(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new prediction.
    
    Request body:
    {
        "home_team": "duke",
        "away_team": "connecticut",
        "span": 3,                          # Optional, default: 3
        "neutral": false,                   # Optional, default: false
        "sport": "ncaam_basketball",        # Optional, default: "ncaam_basketball"
        "model": "ensemble"                 # Optional, default: "ensemble"
    }
    """
    logging.info('POST /predictions')
    
    try:
        blob_service = get_blob_service()
        predictions_store = get_predictions_store()
        data = req.get_json()
        
        # Validate request
        try:
            validated = validate_prediction_request(data)
        except ValueError as e:
            return _error_response("validation_error", str(e), 400)
        
        home_team = validated['home_team']
        away_team = validated['away_team']
        span = validated['span']
        sport = validated['sport']
        model_type = validated['model']
        neutral = validated['neutral']
        is_womens = validated['is_womens']
        
        # Get team stats to generate prediction ID for cache check
        matchup_stats = blob_service.get_matchup_stats(home_team, away_team, span, is_womens)
        home_last_played = matchup_stats['team1']['lastPlayed']
        away_last_played = matchup_stats['team2']['lastPlayed']
        
        # Get model version(s) for prediction ID
        if model_type == 'ensemble':
            model_versions = []
            for mt in sorted(MODEL_NAME_MAP.keys()):
                v = blob_service.get_model_version(sport, span, mt)
                model_versions.append(f"{mt}:{v}")
            model_version = '|'.join(model_versions)
        else:
            model_version = blob_service.get_model_version(sport, span, model_type)
        
        # Generate prediction ID (content-hash based)
        prediction_id = PredictionsStore.generate_prediction_id(
            home_team=home_team,
            away_team=away_team,
            home_last_played=home_last_played,
            away_last_played=away_last_played,
            span=span,
            neutral=neutral,
            sport=sport,
            model=model_type,
            model_version=model_version
        )
        
        # Check cache (point read)
        cached = predictions_store.get_prediction(prediction_id, sport)
        if cached:
            logging.info(f"Cache hit for prediction: {prediction_id}")
            return _success_response(_format_prediction(cached))
        
        logging.info(f"Cache miss for prediction: {prediction_id}")
        
        # Run prediction using shared service
        result, cosmos_record = run_prediction(
            blob_service=blob_service,
            home_team=home_team,
            away_team=away_team,
            span=span,
            sport=sport,
            model_type=model_type,
            neutral=neutral
        )
        
        # Store and return
        stored = predictions_store.create_prediction(cosmos_record)
        return _success_response(_format_prediction(stored))
    
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return _error_response("validation_error", str(e), 400)
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return _error_response("internal_error", "Internal server error", 500)


# =============================================================================
# GET /predictions/{id} - Get a single prediction
# =============================================================================

def handle_get_one(req: func.HttpRequest, prediction_id: str) -> func.HttpResponse:
    """
    Retrieve a prediction by ID.
    
    GET /predictions/{prediction_id}?sport=ncaam_basketball
    """
    logging.info(f'GET /predictions/{prediction_id}')
    
    try:
        sport = req.params.get('sport')
        
        if not sport or sport not in VALID_SPORTS:
            return _error_response(
                "missing_sport", 
                f"sport query parameter is required (one of: {', '.join(VALID_SPORTS)})", 
                400
            )
        
        predictions_store = get_predictions_store()
        prediction = predictions_store.get_prediction(prediction_id, sport)
        
        if not prediction:
            return _error_response("not_found", "Prediction not found", 404)
        
        return _success_response(_format_prediction(prediction))
    
    except Exception as e:
        logging.error(f"Error retrieving prediction: {e}")
        return _error_response("internal_error", "Internal server error", 500)


# =============================================================================
# GET /predictions - List predictions with pagination
# =============================================================================

def handle_list(req: func.HttpRequest) -> func.HttpResponse:
    """
    Query prediction history with optional filters.
    
    GET /predictions?sport=ncaam_basketball&home_team=duke&limit=50
    """
    logging.info('GET /predictions')
    
    try:
        sport = req.params.get('sport')
        
        if not sport or sport not in VALID_SPORTS:
            return _error_response(
                "missing_sport", 
                f"sport query parameter is required (one of: {', '.join(VALID_SPORTS)})", 
                400
            )
        
        home_team = req.params.get('home_team')
        away_team = req.params.get('away_team')
        model_version = req.params.get('model_version')
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')
        
        pagination = parse_pagination_params(req.params)
        
        predictions_store = get_predictions_store()
        predictions = predictions_store.query_predictions(
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
            limit=pagination['limit'] + 1,
            before_id=pagination['before_id'],
            after_id=pagination['after_id']
        )
        
        formatted = [_format_prediction(p) for p in predictions]
        response = build_list_response(formatted, pagination['limit'])
        
        return _success_response(response)
    
    except Exception as e:
        logging.error(f"Error querying predictions: {e}")
        return _error_response("internal_error", "Internal server error", 500)


# =============================================================================
# Helpers
# =============================================================================

def _format_prediction(prediction: dict) -> dict:
    """Format a prediction record for API response."""
    result = prediction.get('result', {})
    
    return {
        'id': prediction['id'],
        'type': 'prediction',
        'model': prediction['model'],
        'span': prediction['span'],
        'sport': prediction['sport'],
        'home_team': prediction['home_team'],
        'away_team': prediction['away_team'],
        'home_last_played': prediction.get('home_last_played'),
        'away_last_played': prediction.get('away_last_played'),
        'neutral': prediction['neutral'],
        'home_win_probability': result.get('home_win_probability'),
        'created_at': prediction.get('created_at')
    }


def _success_response(data: dict) -> func.HttpResponse:
    """Return a successful JSON response."""
    return func.HttpResponse(
        json.dumps(data),
        mimetype="application/json",
        status_code=200
    )


def _error_response(code: str, message: str, status_code: int) -> func.HttpResponse:
    """Return an error JSON response."""
    return func.HttpResponse(
        json.dumps({"type": "error", "error": {"code": code, "message": message}}),
        mimetype="application/json",
        status_code=status_code
    )
