import json
import logging
import os
import re
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import azure.functions as func
import numpy as np
import joblib
from azure.storage.blob import BlobServiceClient

# Cache for loaded models and team stats
_models_cache = {
    'mens': {},
    'womens': {}
}

_team_stats_cache = {
    'mens': None,
    'womens': None
}

def get_blob_service_client():
    """Get Azure Blob Storage client."""
    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    return BlobServiceClient.from_connection_string(conn_str)

def load_team_stats(is_womens: bool = False) -> dict:
    """Load team stats from Blob Storage with caching."""
    cache_key = 'womens' if is_womens else 'mens'
    
    if _team_stats_cache[cache_key] is not None:
        return _team_stats_cache[cache_key]
    
    try:
        blob_service = get_blob_service_client()
        container_name = 'mlmb-api'
        blob_name = 'womens-team-stats' if is_womens else 'team-stats'
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        blob_data = blob_client.download_blob().readall()
        
        data = json.loads(blob_data.decode())
        _team_stats_cache[cache_key] = data
        
        return data
    except Exception as e:
        logging.error(f"Failed to load team stats: {e}")
        raise

def get_matchup_stats(team1: str, team2: str, span: int, is_womens: bool = False) -> dict:
    """Get stats for both teams in a matchup."""
    stats = load_team_stats(is_womens)
    span_key = str(span)
    
    if span_key not in stats:
        raise ValueError(f"Invalid span: {span}")
    
    span_stats = stats[span_key]
    
    if team1 not in span_stats:
        raise ValueError(f"Team not found: {team1}")
    if team2 not in span_stats:
        raise ValueError(f"Team not found: {team2}")
    
    return {
        'team1': span_stats[team1],
        'team2': span_stats[team2]
    }

def load_model(model_name: str, is_womens: bool = False):
    """Load model from Blob Storage with caching."""
    cache_key = 'womens' if is_womens else 'mens'
    
    if model_name in _models_cache[cache_key]:
        return _models_cache[cache_key][model_name]
    
    try:
        blob_service = get_blob_service_client()
        container_name = 'mlmb-models'
        blob_path = f"{'womens' if is_womens else 'mens'}/{model_name}.pkl"
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
        model_bytes = blob_client.download_blob().readall()
        
        model = joblib.load(io.BytesIO(model_bytes))
        _models_cache[cache_key][model_name] = model
        
        return model
    except Exception as e:
        logging.error(f"Failed to load model {model_name}: {e}")
        raise

def load_models_parallel(model_names: list, is_womens: bool = False):
    """Load multiple models in parallel."""
    cache_key = 'womens' if is_womens else 'mens'
    
    # Filter to only models not already cached
    models_to_load = [name for name in model_names if name not in _models_cache[cache_key]]
    
    if not models_to_load:
        return  # All models already cached
    
    def load_single(model_name):
        try:
            return model_name, load_model(model_name, is_womens)
        except Exception as e:
            logging.warning(f"Failed to load model {model_name}: {e}")
            return model_name, None
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(load_single, name): name for name in models_to_load}
        for future in as_completed(futures):
            model_name, model = future.result()
            if model is not None:
                logging.info(f"Loaded model: {model_name}")

def get_span_number(model_name: str) -> int:
    """Extract span number from model name (e.g., '3span_ensemble' -> 3)."""
    match = re.search(r"(\d+)span", model_name)
    return int(match.group(1)) if match else None

def ensemble_predict(input_data: np.ndarray, models: dict, span: int) -> dict:
    """Run ensemble prediction across all models for a given span."""
    counter = 0
    predict_proba = [0.0, 0.0]
    
    for key, model in models.items():
        if f'{span}span_' in key:
            proba = model.predict_proba(input_data)
            predict_proba[0] += proba[0][0]
            predict_proba[1] += proba[0][1]
            counter += 1
    
    if counter == 0:
        raise ValueError(f"No models found for span {span}")
    
    return {
        'predict': [round(predict_proba[1] / counter)],
        'predictProba': [predict_proba[0] / counter, predict_proba[1] / counter]
    }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle prediction requests.
    
    Expected request body:
    [
        {
            "model": "3span_ensemble",
            "isNeutral": true,
            "isWomens": false,
            "team1": "connecticut",   # Team name (string)
            "team2": "duke"           # Team name (string)
        }
    ]
    
    Response:
    [
        {
            "model": "3span_ensemble",
            "isNeutral": true,
            "isWomens": false,
            "team1": "connecticut",
            "team2": "duke",
            "predict": [1],
            "predictProba": [0.35, 0.65],
            "team1LastPlayed": "2026-01-15",
            "team2LastPlayed": "2026-01-14"
        }
    ]
    """
    logging.info('Prediction function triggered')
    
    try:
        matchups = req.get_json()
        
        if not isinstance(matchups, list):
            matchups = [matchups]
        
        results = []
        
        for matchup in matchups:
            model_name = matchup['model']
            is_womens = matchup.get('isWomens', False)
            is_neutral = matchup.get('isNeutral', False)
            team1_name = matchup['team1']  # Team name string
            team2_name = matchup['team2']  # Team name string
            
            # Get span from model name
            span = get_span_number(model_name)
            if span is None:
                raise ValueError(f"Could not determine span from model name: {model_name}")
            
            # Look up team stats from Blob Storage
            matchup_stats = get_matchup_stats(team1_name, team2_name, span, is_womens)
            team1_stats = matchup_stats['team1']['stats']
            team2_stats = matchup_stats['team2']['stats']
            team1_last_played = matchup_stats['team1']['lastPlayed']
            team2_last_played = matchup_stats['team2']['lastPlayed']
            
            # Prepare input: [team2_stats + team1_stats + is_neutral]
            input_data = np.array([team2_stats + team1_stats + [int(is_neutral)]])
            
            cache_key = 'womens' if is_womens else 'mens'
            
            if 'ensemble' in model_name:
                # Load all models for this span in parallel
                model_types = ['logistic_regression_model', 'knn_model', 'random_forest', 
                              'gradient_boosting', 'multilayer_perceptron', 'support_vector_machine_model']
                model_names_to_load = [f'{span}span_{model_type}' for model_type in model_types]
                
                # Parallel loading - much faster on cold start
                load_models_parallel(model_names_to_load, is_womens)
                
                result = ensemble_predict(input_data, _models_cache[cache_key], span)
            else:
                model = load_model(model_name, is_womens)
                predict = model.predict(input_data)
                predict_proba = model.predict_proba(input_data)
                result = {
                    'predict': predict.tolist(),
                    'predictProba': predict_proba.tolist()[0]
                }
            
            # Build response matching MatchupOutput interface
            response_matchup = {
                'model': model_name,
                'isNeutral': is_neutral,
                'isWomens': is_womens,
                'team1': team1_name,
                'team2': team2_name,
                'predict': result['predict'],
                'predictProba': result['predictProba'],
                'team1LastPlayed': team1_last_played,
                'team2LastPlayed': team2_last_played
            }
            results.append(response_matchup)
        
        return func.HttpResponse(
            json.dumps(results),
            mimetype="application/json",
            status_code=200
        )
    
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )
