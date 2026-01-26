import json
import logging
import azure.functions as func
import numpy as np

from shared.blob_service import get_blob_service

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


def ensemble_predict(input_data: np.ndarray, models: dict) -> tuple[float, float]:
    """
    Run ensemble prediction using provided models.
    
    Args:
        input_data: Feature array for prediction.
        models: Dict of models to use (should already be filtered and sorted).
    
    Returns:
        Tuple of (team1_probability, team2_probability).
    """
    if not models:
        raise ValueError("No models provided for ensemble prediction")
    
    predict_proba = [0.0, 0.0]
    model_names = []
    
    # Models dict should already be in sorted order from get_models_parallel
    for name, model in models.items():
        proba = model.predict_proba(input_data)
        predict_proba[0] += proba[0][0]
        predict_proba[1] += proba[0][1]
        model_names.append(name)
    
    num_models = len(models)
    logging.info(f"Ensemble prediction used {num_models} models: {model_names}")
    
    return predict_proba[0] / num_models, predict_proba[1] / num_models

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle prediction requests.
    
    POST /predictions
    
    Request body:
    {
        "team1": "duke",
        "team2": "connecticut",
        "span": 3,              # Optional, default: 3
        "neutral": false,       # Optional, default: false
        "gender": "men",        # Optional, default: "men"
        "model": "ensemble"     # Optional, default: "ensemble"
    }
    
    Response:
    {
        "team1": "duke",
        "team1_probability": 0.5218,
        "team1_last_played": "2026-01-17",
        "team2": "connecticut",
        "team2_probability": 0.4782,
        "team2_last_played": "2026-01-17",
        "winner": "team1",
        "confidence": 0.5218,
        "span": 3,
        "neutral": false,
        "gender": "men",
        "model": "ensemble"
    }
    """
    logging.info('Prediction function triggered')
    
    try:
        blob_service = get_blob_service()
        data = req.get_json()
        
        # Extract and validate request fields
        team1_name = data.get('team1')
        team2_name = data.get('team2')
        span = data.get('span', 3)
        neutral = data.get('neutral', False)
        gender = data.get('gender', 'men')
        model_type = data.get('model', 'ensemble')
        
        # Validate required fields
        if not team1_name or not team2_name:
            return func.HttpResponse(
                json.dumps({"error": {"code": "missing_teams", "message": "team1 and team2 are required"}}),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate span
        if span not in [3, 5, 7]:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_span", "message": "span must be 3, 5, or 7"}}),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate gender
        if gender not in ['men', 'women']:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_gender", "message": "gender must be 'men' or 'women'"}}),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate model
        if model_type not in VALID_MODELS:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_model", "message": f"model must be one of: {', '.join(sorted(VALID_MODELS))}"}}),
                mimetype="application/json",
                status_code=400
            )
        
        is_womens = gender == 'women'
        
        # Look up team stats from Blob Storage
        matchup_stats = blob_service.get_matchup_stats(team1_name, team2_name, span, is_womens)
        team1_stats = matchup_stats['team1']['stats']
        team2_stats = matchup_stats['team2']['stats']
        team1_last_played = matchup_stats['team1']['lastPlayed']
        team2_last_played = matchup_stats['team2']['lastPlayed']
        
        # Prepare input: [team2_stats + team1_stats + neutral]
        input_data = np.array([team2_stats + team1_stats + [int(neutral)]])
        
        if model_type == 'ensemble':
            # Load all models for this span in parallel and get them in sorted order
            model_names_to_load = [f'{span}span_{blob_name}' for blob_name in MODEL_NAME_MAP.values()]
            
            # Returns models dict in sorted order for deterministic results
            ensemble_models = blob_service.get_models_parallel(model_names_to_load, is_womens)
            
            team1_prob, team2_prob = ensemble_predict(input_data, ensemble_models)
        else:
            # Single model prediction
            blob_model_name = f'{span}span_{MODEL_NAME_MAP[model_type]}'
            model = blob_service.get_model(blob_model_name, is_womens)
            proba = model.predict_proba(input_data)
            team1_prob, team2_prob = proba[0][0], proba[0][1]
        
        # Determine winner and confidence
        if team1_prob >= team2_prob:
            winner = 'team1'
            confidence = team1_prob
        else:
            winner = 'team2'
            confidence = team2_prob
        
        # Build response
        response = {
            'team1': team1_name,
            'team1_probability': round(team1_prob, 4),
            'team1_last_played': team1_last_played,
            'team2': team2_name,
            'team2_probability': round(team2_prob, 4),
            'team2_last_played': team2_last_played,
            'winner': winner,
            'confidence': round(confidence, 4),
            'span': span,
            'neutral': neutral,
            'gender': gender,
            'model': model_type
        }
        
        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"code": "validation_error", "message": str(e)}}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"code": "internal_error", "message": "Internal server error"}}),
            mimetype="application/json",
            status_code=500
        )
