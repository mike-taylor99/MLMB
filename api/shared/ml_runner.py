"""
ML Runner - low-level machine learning model execution.

Loads sklearn models and runs predictions. This is the core ML engine
that the business logic layer (app/services) calls into.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

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
    home_team = data.get("home_team")
    away_team = data.get("away_team")

    if not home_team or not away_team:
        raise ValueError("home_team and away_team are required")

    span = data.get("span", 3)
    if span not in VALID_SPANS:
        raise ValueError(f"span must be one of: {VALID_SPANS}")

    sport = data.get("sport", "ncaam_basketball")
    if sport not in VALID_SPORTS:
        raise ValueError(f"sport must be one of: {VALID_SPORTS}")

    model = data.get("model", "ensemble")
    if model not in VALID_MODELS:
        raise ValueError(f"model must be one of: {sorted(VALID_MODELS)}")

    neutral = bool(data.get("neutral", False))

    return {
        "home_team": home_team.lower(),
        "away_team": away_team.lower(),
        "span": span,
        "sport": sport,
        "model": model,
        "neutral": neutral,
        "is_womens": sport == "ncaaw_basketball",
    }


# =============================================================================
# Prediction Execution
# =============================================================================


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
    model_versions_cache: Optional[dict] = None,
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
    is_womens = sport == "ncaaw_basketball"
    cache_key = (sport, span, model_type)
    stats_key_home = (home_team, span, is_womens)
    stats_key_away = (away_team, span, is_womens)

    # Get team stats (from cache or load)
    if stats_cache is not None:
        home_stats_data = stats_cache.get(stats_key_home)
        away_stats_data = stats_cache.get(stats_key_away)
    else:
        matchup_stats = blob_service.get_matchup_stats(
            home_team, away_team, span, is_womens
        )
        home_stats_data = matchup_stats["team1"]
        away_stats_data = matchup_stats["team2"]

    if not home_stats_data:
        raise ValueError(f"Stats not found for team: {home_team}")
    if not away_stats_data:
        raise ValueError(f"Stats not found for team: {away_team}")

    home_stats = home_stats_data["stats"]
    away_stats = away_stats_data["stats"]
    home_last_played = home_stats_data["lastPlayed"]
    away_last_played = away_stats_data["lastPlayed"]

    # Build feature dataframe
    input_data = blob_service.build_feature_dataframe(home_stats, away_stats, neutral)

    # Get model and version (from cache or load)
    if models_cache is not None and model_versions_cache is not None:
        model_or_models = models_cache[cache_key]
        model_version = model_versions_cache[cache_key]
    else:
        blob_name = f"{span}span_{MODEL_NAME_MAP[model_type]}"
        blob_path = blob_service.get_model_blob_path(sport, span, model_type)
        model_or_models = blob_service.get_model(
            blob_name, is_womens, blob_path=blob_path
        )
        model_version = blob_service.get_model_version(sport, span, model_type)

    # Run prediction
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
        model_version=model_version,
    )

    feature_values = home_stats + away_stats + [int(neutral)]
    feature_hash = PredictionsStore.generate_feature_hash(feature_values)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    cosmos_record = {
        "id": prediction_id,
        "status": "completed",
        "home_team": home_team,
        "away_team": away_team,
        "home_last_played": home_last_played,
        "away_last_played": away_last_played,
        "span": span,
        "neutral": neutral,
        "sport": sport,
        "model": model_type,
        "model_version": model_version,
        "feature_hash": feature_hash,
        "result": {
            "home_win_probability": round(home_prob, 4),
            "away_win_probability": round(1 - home_prob, 4),
            "predicted_winner": predicted_winner,
        },
        "created_at": now,
        "completed_at": now,
    }

    # Build API response (matches documented format)
    result = {
        "id": prediction_id,
        "type": "prediction",
        "model": model_type,
        "span": span,
        "sport": sport,
        "home_team": home_team,
        "away_team": away_team,
        "home_last_played": home_last_played,
        "away_last_played": away_last_played,
        "neutral": neutral,
        "home_win_probability": round(home_prob, 4),
        "created_at": now,
    }

    return result, cosmos_record


# =============================================================================
# Batch Helpers
# =============================================================================


def preload_models(blob_service: BlobStorageService, model_keys: set) -> dict:
    """Pre-load all required models for batch processing (parallel)."""
    if not model_keys:
        return {}

    from concurrent.futures import ThreadPoolExecutor

    models_cache = {}

    def load_model(key):
        sport, span, model_type = key
        is_womens = sport == "ncaaw_basketball"
        cache_key = (sport, span, model_type)
        blob_name = f"{span}span_{MODEL_NAME_MAP[model_type]}"
        blob_path = blob_service.get_model_blob_path(sport, span, model_type)
        model = blob_service.get_model(blob_name, is_womens, blob_path=blob_path)
        return cache_key, model

    with ThreadPoolExecutor(max_workers=min(len(model_keys), 6)) as executor:
        results = list(executor.map(load_model, model_keys))

    for cache_key, model in results:
        models_cache[cache_key] = model

    return models_cache


def preload_model_versions(blob_service: BlobStorageService, model_keys: set) -> dict:
    """Get model versions for all required models."""
    versions_cache = {}

    for sport, span, model_type in model_keys:
        cache_key = (sport, span, model_type)
        versions_cache[cache_key] = blob_service.get_model_version(
            sport, span, model_type
        )

    return versions_cache


def run_batch_predictions(
    blob_service: BlobStorageService,
    items: list,
    models_cache: dict,
    model_versions_cache: dict,
) -> list:
    """
    Run predictions in vectorized batches, grouped by model.

    Instead of calling predict_proba once per item, this groups items
    that share the same model and calls predict_proba once per group
    with a multi-row DataFrame. This is significantly faster for
    sklearn models.

    Args:
        blob_service: Blob service (for feature names)
        items: List of dicts, each with keys:
            index, home_team, away_team, span, sport, model_type, neutral,
            home_stats, away_stats, home_last_played, away_last_played
        models_cache: Pre-loaded models keyed by (sport, span, model_type)
        model_versions_cache: Pre-loaded versions keyed by (sport, span, model_type)

    Returns:
        List of (index, result_dict, cosmos_record_dict) tuples
    """
    from collections import defaultdict
    import pandas as pd

    groups = defaultdict(list)
    for item in items:
        cache_key = (item["sport"], item["span"], item["model_type"])
        groups[cache_key].append(item)

    feature_names = blob_service.get_feature_names()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    all_results = []

    for cache_key, group_items in groups.items():
        sport, span, model_type = cache_key
        model_or_models = models_cache[cache_key]
        model_version = model_versions_cache[cache_key]

        # Build multi-row feature matrix for the entire group
        rows = []
        for item in group_items:
            feature_values = (
                item["home_stats"] + item["away_stats"] + [int(item["neutral"])]
            )
            rows.append(feature_values)

        input_data = pd.DataFrame(rows, columns=feature_names)

        # Single vectorized predict_proba call for the whole group
        probas = model_or_models.predict_proba(input_data)

        # Build results from the probability matrix
        for i, item in enumerate(group_items):
            home_prob = probas[i][1]
            predicted_winner = (
                item["home_team"] if home_prob >= 0.5 else item["away_team"]
            )

            feature_values = rows[i]

            prediction_id = PredictionsStore.generate_prediction_id(
                home_team=item["home_team"],
                away_team=item["away_team"],
                home_last_played=item["home_last_played"],
                away_last_played=item["away_last_played"],
                span=span,
                neutral=item["neutral"],
                sport=sport,
                model=model_type,
                model_version=model_version,
            )

            feature_hash = PredictionsStore.generate_feature_hash(feature_values)

            cosmos_record = {
                "id": prediction_id,
                "status": "completed",
                "home_team": item["home_team"],
                "away_team": item["away_team"],
                "home_last_played": item["home_last_played"],
                "away_last_played": item["away_last_played"],
                "span": span,
                "neutral": item["neutral"],
                "sport": sport,
                "model": model_type,
                "model_version": model_version,
                "feature_hash": feature_hash,
                "result": {
                    "home_win_probability": round(home_prob, 4),
                    "away_win_probability": round(1 - home_prob, 4),
                    "predicted_winner": predicted_winner,
                },
                "created_at": now,
                "completed_at": now,
            }

            result = {
                "id": prediction_id,
                "type": "prediction",
                "model": model_type,
                "span": span,
                "sport": sport,
                "home_team": item["home_team"],
                "away_team": item["away_team"],
                "home_last_played": item["home_last_played"],
                "away_last_played": item["away_last_played"],
                "neutral": item["neutral"],
                "home_win_probability": round(home_prob, 4),
                "created_at": now,
            }

            all_results.append((item["index"], result, cosmos_record))

    return all_results


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
