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
import pandas as pd

from shared.blob_service import get_blob_service
from shared.pagination import build_list_response, parse_pagination_params
from shared.predictions_store import get_predictions_store, PredictionsStore


# Valid model types
VALID_MODELS = {
    'ensemble', 'logistic_regression', 'knn', 'random_forest',
    'gradient_boosting', 'mlp', 'svm'
}

# Model name mapping (short name -> blob storage name)
MODEL_NAME_MAP = {
    'logistic_regression': 'logistic_regression_model',
    'knn': 'knn_model',
    'random_forest': 'random_forest',
    'gradient_boosting': 'gradient_boosting',
    'mlp': 'multilayer_perceptron',
    'svm': 'support_vector_machine_model'
}

VALID_SPORTS = ['ncaam_basketball', 'ncaaw_basketball']


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
    
    return func.HttpResponse(
        json.dumps({"error": {"code": "method_not_allowed", "message": "Method not allowed"}}),
        mimetype="application/json",
        status_code=405
    )


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
        
        # Extract and validate request fields
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        span = data.get('span', 3)
        neutral = data.get('neutral', False)
        sport = data.get('sport', 'ncaam_basketball')
        model_type = data.get('model', 'ensemble')
        
        # Validate required fields
        if not home_team or not away_team:
            return _error_response("missing_teams", "home_team and away_team are required", 400)
        
        # Normalize team names
        home_team = home_team.lower()
        away_team = away_team.lower()
        
        # Validate span
        if span not in [3, 5, 7]:
            return _error_response("invalid_span", "span must be 3, 5, or 7", 400)
        
        # Validate sport
        if sport not in VALID_SPORTS:
            return _error_response("invalid_sport", f"sport must be one of: {', '.join(VALID_SPORTS)}", 400)
        
        # Validate model
        if model_type not in VALID_MODELS:
            return _error_response("invalid_model", f"model must be one of: {', '.join(sorted(VALID_MODELS))}", 400)
        
        is_womens = sport == 'ncaaw_basketball'
        
        # Look up team stats from Blob Storage
        matchup_stats = blob_service.get_matchup_stats(home_team, away_team, span, is_womens)
        home_stats = matchup_stats['team1']['stats']
        away_stats = matchup_stats['team2']['stats']
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
        
        # Build named DataFrame for prediction
        input_data = blob_service.build_feature_dataframe(home_stats, away_stats, neutral)
        
        # Generate feature hash for traceability
        feature_values = home_stats + away_stats + [int(neutral)]
        feature_hash = PredictionsStore.generate_feature_hash(feature_values)
        
        if model_type == 'ensemble':
            model_names_to_load = [f'{span}span_{blob_name}' for blob_name in MODEL_NAME_MAP.values()]
            ensemble_models = blob_service.get_models_parallel(model_names_to_load, is_womens)
            home_prob, away_prob = _ensemble_predict(input_data, ensemble_models)
        else:
            blob_model_name = f'{span}span_{MODEL_NAME_MAP[model_type]}'
            model = blob_service.get_model(blob_model_name, is_womens)
            proba = model.predict_proba(input_data)
            home_prob, away_prob = proba[0][1], proba[0][0]
        
        predicted_winner = home_team if home_prob >= away_prob else away_team
        
        # Build and store prediction record
        prediction_record = predictions_store.build_prediction_record(
            prediction_id=prediction_id,
            home_team=home_team,
            away_team=away_team,
            home_last_played=home_last_played,
            away_last_played=away_last_played,
            span=span,
            neutral=neutral,
            sport=sport,
            model=model_type,
            model_version=model_version,
            feature_hash=feature_hash,
            home_win_probability=home_prob,
            predicted_winner=predicted_winner
        )
        
        stored = predictions_store.create_prediction(prediction_record)
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

def _ensemble_predict(input_data: pd.DataFrame, models: dict) -> tuple[float, float]:
    """Run ensemble prediction using provided models."""
    if not models:
        raise ValueError("No models provided for ensemble prediction")
    
    predict_proba = [0.0, 0.0]
    model_names = []
    
    for name, model in models.items():
        proba = model.predict_proba(input_data)
        predict_proba[0] += proba[0][0]
        predict_proba[1] += proba[0][1]
        model_names.append(name)
    
    num_models = len(models)
    logging.info(f"Ensemble prediction used {num_models} models: {model_names}")
    
    return predict_proba[1] / num_models, predict_proba[0] / num_models


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
        json.dumps({"error": {"code": code, "message": message}}),
        mimetype="application/json",
        status_code=status_code
    )
