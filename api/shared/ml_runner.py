"""
ML Runner - low-level machine learning model execution.

Loads sklearn models and runs predictions. This is the core ML engine
that the business logic layer (app/services) calls into.
"""
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.constants import VALID_SPORTS, VALID_SPANS, VALID_MODELS
from shared.blob_service import BlobStorageService, MODEL_NAME_MAP
from shared.predictions_store import PredictionsStore


# =============================================================================
# Validation
# =============================================================================

def validate_prediction_request(data: dict) -> dict:
    """
    Validate and normalize a prediction request.
    
    Args:
        data: Raw request data
        
    Returns:
        Normalized request dict
        
    Raises:
        ValueError: If validation fails
    """
    home_team = data.get('home_team')
    away_team = data.get('away_team')
    
    if not home_team or not away_team:
        raise ValueError("home_team and away_team are required")
    
    span = data.get('span', 3)
    if span not in VALID_SPANS:
        raise ValueError(f"span must be one of: {VALID_SPANS}")
    
    sport = data.get('sport', 'ncaam_basketball')
    if sport not in VALID_SPORTS:
        raise ValueError(f"sport must be one of: {VALID_SPORTS}")
    
    model = data.get('model', 'ensemble')
    if model not in VALID_MODELS:
        raise ValueError(f"model must be one of: {sorted(VALID_MODELS)}")
    
    neutral = bool(data.get('neutral', False))
    
    return {
        'home_team': home_team.lower(),
        'away_team': away_team.lower(),
        'span': span,
        'sport': sport,
        'model': model,
        'neutral': neutral,
        'is_womens': sport == 'ncaaw_basketball'
    }


# =============================================================================
# Prediction Execution
# =============================================================================

def ensemble_predict(input_data: pd.DataFrame, models: dict) -> float:
    """
    Run ensemble prediction and return home win probability.
    
    Args:
        input_data: Feature DataFrame for prediction
        models: Dict of model_name -> model
        
    Returns:
        Home win probability (0-1)
    """
    if not models:
        raise ValueError("No models provided for ensemble prediction")
    
    total_prob = 0.0
    for model in models.values():
        proba = model.predict_proba(input_data)
        total_prob += proba[0][1]  # home win probability
    
    return total_prob / len(models)


def run_prediction(
    blob_service: BlobStorageService,
    home_team: str,
    away_team: str,
    span: int,
    sport: str,
    model_type: str,
    neutral: bool,
    models_cache: Optional[dict] = None,
    stats_cache: Optional[dict] = None,
    model_versions_cache: Optional[dict] = None
) -> Tuple[dict, dict]:
    """
    Run a single prediction and build result + Cosmos record.
    
    Can use pre-loaded caches (for batch) or load on-demand (for single).
    
    Args:
        blob_service: Blob service instance
        home_team: Home team key
        away_team: Away team key
        span: Span value (3, 5, or 7)
        sport: Sport key
        model_type: Model type (ensemble, logistic_regression, etc.)
        neutral: Whether neutral site
        models_cache: Optional pre-loaded models
        stats_cache: Optional pre-loaded stats
        model_versions_cache: Optional pre-loaded model versions
        
    Returns:
        Tuple of (API response dict, Cosmos DB record dict)
    """
    is_womens = sport == 'ncaaw_basketball'
    cache_key = (sport, span, model_type)
    stats_key_home = (home_team, span, is_womens)
    stats_key_away = (away_team, span, is_womens)
    
    # Get team stats (from cache or load)
    if stats_cache is not None:
        home_stats_data = stats_cache.get(stats_key_home)
        away_stats_data = stats_cache.get(stats_key_away)
    else:
        matchup_stats = blob_service.get_matchup_stats(home_team, away_team, span, is_womens)
        home_stats_data = matchup_stats['team1']
        away_stats_data = matchup_stats['team2']
    
    if not home_stats_data:
        raise ValueError(f"Stats not found for team: {home_team}")
    if not away_stats_data:
        raise ValueError(f"Stats not found for team: {away_team}")
    
    home_stats = home_stats_data['stats']
    away_stats = away_stats_data['stats']
    home_last_played = home_stats_data['lastPlayed']
    away_last_played = away_stats_data['lastPlayed']
    
    # Build feature dataframe
    input_data = blob_service.build_feature_dataframe(home_stats, away_stats, neutral)
    
    # Get model and version (from cache or load)
    if models_cache is not None and model_versions_cache is not None:
        model_or_models = models_cache[cache_key]
        model_version = model_versions_cache[cache_key]
    else:
        if model_type == 'ensemble':
            model_names = [f'{span}span_{blob_name}' for blob_name in MODEL_NAME_MAP.values()]
            model_or_models = blob_service.get_models_parallel(model_names, is_womens)
            model_versions = []
            for mt in sorted(MODEL_NAME_MAP.keys()):
                v = blob_service.get_model_version(sport, span, mt)
                model_versions.append(f"{mt}:{v}")
            model_version = '|'.join(model_versions)
        else:
            blob_name = f'{span}span_{MODEL_NAME_MAP[model_type]}'
            model_or_models = blob_service.get_model(blob_name, is_womens)
            model_version = blob_service.get_model_version(sport, span, model_type)
    
    # Run prediction
    if model_type == 'ensemble':
        home_prob = ensemble_predict(input_data, model_or_models)
    else:
        proba = model_or_models.predict_proba(input_data)
        home_prob = proba[0][1]
    
    predicted_winner = home_team if home_prob >= 0.5 else away_team
    
    # Build Cosmos DB record first (we need the ID for the API response)
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
    
    feature_values = home_stats + away_stats + [int(neutral)]
    feature_hash = PredictionsStore.generate_feature_hash(feature_values)
    
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    cosmos_record = {
        'id': prediction_id,
        'status': 'completed',
        'home_team': home_team,
        'away_team': away_team,
        'home_last_played': home_last_played,
        'away_last_played': away_last_played,
        'span': span,
        'neutral': neutral,
        'sport': sport,
        'model': model_type,
        'model_version': model_version,
        'feature_hash': feature_hash,
        'result': {
            'home_win_probability': round(home_prob, 4),
            'away_win_probability': round(1 - home_prob, 4),
            'predicted_winner': predicted_winner
        },
        'created_at': now,
        'completed_at': now
    }
    
    # Build API response (matches documented format)
    result = {
        'id': prediction_id,
        'type': 'prediction',
        'model': model_type,
        'span': span,
        'sport': sport,
        'home_team': home_team,
        'away_team': away_team,
        'home_last_played': home_last_played,
        'away_last_played': away_last_played,
        'neutral': neutral,
        'home_win_probability': round(home_prob, 4),
        'created_at': now
    }
    
    return result, cosmos_record


# =============================================================================
# Batch Helpers
# =============================================================================

def preload_models(blob_service: BlobStorageService, model_keys: set) -> dict:
    """Pre-load all required models for batch processing."""
    models_cache = {}
    
    for sport, span, model_type in model_keys:
        is_womens = sport == 'ncaaw_basketball'
        cache_key = (sport, span, model_type)
        
        if model_type == 'ensemble':
            model_names = [f'{span}span_{blob_name}' for blob_name in MODEL_NAME_MAP.values()]
            models_cache[cache_key] = blob_service.get_models_parallel(model_names, is_womens)
        else:
            blob_name = f'{span}span_{MODEL_NAME_MAP[model_type]}'
            models_cache[cache_key] = blob_service.get_model(blob_name, is_womens)
    
    return models_cache


def preload_model_versions(blob_service: BlobStorageService, model_keys: set) -> dict:
    """Get model versions for all required models."""
    versions_cache = {}
    
    for sport, span, model_type in model_keys:
        cache_key = (sport, span, model_type)
        
        if model_type == 'ensemble':
            model_versions = []
            for mt in sorted(MODEL_NAME_MAP.keys()):
                v = blob_service.get_model_version(sport, span, mt)
                model_versions.append(f"{mt}:{v}")
            versions_cache[cache_key] = '|'.join(model_versions)
        else:
            versions_cache[cache_key] = blob_service.get_model_version(sport, span, model_type)
    
    return versions_cache


def preload_stats(blob_service: BlobStorageService, stats_keys: set) -> dict:
    """Pre-load all required team stats for batch processing."""
    from concurrent.futures import ThreadPoolExecutor
    
    stats_cache = {}
    
    def load_stats(key):
        team, span, is_womens = key
        try:
            all_stats = blob_service.get_team_stats(is_womens)
            span_stats = all_stats.get(str(span), {})
            team_data = span_stats.get(team)
            return key, team_data
        except Exception as e:
            logging.warning(f"Failed to load stats for {team}: {e}")
            return key, None
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(load_stats, stats_keys))
    
    for key, data in results:
        stats_cache[key] = data
    
    return stats_cache
