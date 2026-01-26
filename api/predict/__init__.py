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
        Tuple of (home_win_probability, away_win_probability).
    """
    if not models:
        raise ValueError("No models provided for ensemble prediction")
    
    # Accumulate probabilities: [0] = away wins, [1] = home wins
    predict_proba = [0.0, 0.0]
    model_names = []
    
    # Models dict should already be in sorted order from get_models_parallel
    for name, model in models.items():
        proba = model.predict_proba(input_data)
        predict_proba[0] += proba[0][0]  # P(away wins)
        predict_proba[1] += proba[0][1]  # P(home wins)
        model_names.append(name)
    
    num_models = len(models)
    logging.info(f"Ensemble prediction used {num_models} models: {model_names}")
    
    # Return (home_prob, away_prob)
    return predict_proba[1] / num_models, predict_proba[0] / num_models

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle prediction requests.
    
    POST /predictions
    
    Request body:
    {
        "home_team": "duke",
        "away_team": "connecticut",
        "span": 3,              # Optional, default: 3
        "neutral": false,       # Optional, default: false
        "gender": "men",        # Optional, default: "men"
        "model": "ensemble"     # Optional, default: "ensemble"
    }
    
    Response:
    {
        "home_team": "duke",
        "away_team": "connecticut",
        "home_win_probability": 0.5218,
        "home_last_played": "2026-01-17",
        "away_last_played": "2026-01-17",
        "predicted_winner": "duke",
        "neutral": false,
        "span": 3,
        "gender": "men",
        "model": "ensemble"
    }
    """
    logging.info('Prediction function triggered')
    
    try:
        blob_service = get_blob_service()
        data = req.get_json()
        
        # Extract and validate request fields
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        span = data.get('span', 3)
        neutral = data.get('neutral', False)
        gender = data.get('gender', 'men')
        model_type = data.get('model', 'ensemble')
        
        # Validate required fields
        if not home_team or not away_team:
            return func.HttpResponse(
                json.dumps({"error": {"code": "missing_teams", "message": "home_team and away_team are required"}}),
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
        # Note: In training data, first position = home team stats, second position = away team stats
        matchup_stats = blob_service.get_matchup_stats(home_team, away_team, span, is_womens)
        home_stats = matchup_stats['team1']['stats']  # team1 in blob = first requested team = home
        away_stats = matchup_stats['team2']['stats']  # team2 in blob = second requested team = away
        home_last_played = matchup_stats['team1']['lastPlayed']
        away_last_played = matchup_stats['team2']['lastPlayed']
        
        # Prepare input: [home_stats + away_stats + neutral]
        # Model trained with home team first, away team second
        input_data = np.array([home_stats + away_stats + [int(neutral)]])
        
        if model_type == 'ensemble':
            # Load all models for this span in parallel and get them in sorted order
            model_names_to_load = [f'{span}span_{blob_name}' for blob_name in MODEL_NAME_MAP.values()]
            
            # Returns models dict in sorted order for deterministic results
            ensemble_models = blob_service.get_models_parallel(model_names_to_load, is_womens)
            
            # ensemble_predict returns (home_prob, away_prob)
            home_prob, away_prob = ensemble_predict(input_data, ensemble_models)
        else:
            # Single model prediction
            blob_model_name = f'{span}span_{MODEL_NAME_MAP[model_type]}'
            model = blob_service.get_model(blob_model_name, is_womens)
            proba = model.predict_proba(input_data)
            # proba[0][0] = P(away wins), proba[0][1] = P(home wins)
            home_prob, away_prob = proba[0][1], proba[0][0]
        
        # Determine predicted winner (actual team name)
        predicted_winner = home_team if home_prob >= away_prob else away_team
        
        # Build response
        response = {
            'home_team': home_team,
            'away_team': away_team,
            'home_win_probability': round(home_prob, 4),
            'home_last_played': home_last_played,
            'away_last_played': away_last_played,
            'predicted_winner': predicted_winner,
            'neutral': neutral,
            'span': span,
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
