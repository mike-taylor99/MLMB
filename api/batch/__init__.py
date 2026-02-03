"""
Batch Predictions API - High-performance batch prediction endpoint.

POST /predictions/batch - Run predictions for multiple matchups in a single request.

Optimizations:
- Models loaded once and reused for all predictions
- Skips Cosmos DB cache reads (computes all predictions)
- Bulk writes only new predictions to Cosmos DB
- Synchronous processing with order preserved
"""
import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service
from shared.predictions_store import get_predictions_store
from shared.prediction_service import (
    VALID_MODELS, VALID_SPORTS, VALID_SPANS,
    validate_prediction_request, run_prediction,
    preload_models, preload_model_versions, preload_stats
)


MAX_BATCH_SIZE = 500


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Handle batch prediction requests."""
    if req.method != 'POST':
        return _error_response("method_not_allowed", "Method not allowed", 405)
    
    return handle_batch(req)


def handle_batch(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process batch predictions.
    
    Request body:
    [
        {"home_team": "duke", "away_team": "connecticut", "span": 3, "neutral": false, "sport": "ncaam_basketball"},
        {"home_team": "duke", "away_team": "connecticut", "span": 3, "neutral": true, "sport": "ncaam_basketball"},
        ...
    ]
    
    Response:
    [
        {"home_team": "duke", "away_team": "connecticut", "home_win_probability": 0.65, "predicted_winner": "duke", ...},
        {"home_team": "duke", "away_team": "connecticut", "home_win_probability": 0.58, "predicted_winner": "duke", ...},
        ...
    ]
    
    Order is preserved - response[i] corresponds to request[i].
    """
    logging.info('POST /predictions/batch')
    
    try:
        body = req.get_json()
        
        # Validate input is an object with input array
        if not isinstance(body, dict) or 'input' not in body:
            return _error_response("invalid_input", "Request body must be an object with 'input' array", 400)
        
        predictions = body['input']
        if not isinstance(predictions, list):
            return _error_response("invalid_input", "'input' must be an array", 400)
        
        # Validate batch size
        if len(predictions) > MAX_BATCH_SIZE:
            return _error_response(
                "batch_too_large", 
                f"Batch size {len(predictions)} exceeds maximum of {MAX_BATCH_SIZE}", 
                400
            )
        
        if len(predictions) == 0:
            return _success_response([])
        
        logging.info(f"Processing batch of {len(predictions)} predictions")
        
        # Validate all predictions
        validated = []
        for i, pred in enumerate(predictions):
            try:
                v = validate_prediction_request(pred)
                v['index'] = i
                validated.append(v)
            except ValueError as e:
                return _error_response("validation_error", f"Prediction {i}: {str(e)}", 400)
        
        # Process predictions
        blob_service = get_blob_service()
        results, records = _process_batch(blob_service, validated)
        
        # Bulk write to Cosmos DB (skip existing, preserve originals)
        if records:
            try:
                predictions_store = get_predictions_store()
                created, skipped = predictions_store.create_predictions_bulk(records)
                logging.info(f"Cosmos DB: {created} created, {skipped} already existed")
            except Exception as e:
                logging.error(f"Bulk write to Cosmos failed (non-fatal): {e}")
        
        logging.info(f"Batch complete: {len(results)} predictions")
        return _success_response(results)
    
    except json.JSONDecodeError:
        return _error_response("invalid_json", "Invalid JSON in request body", 400)
    except Exception as e:
        logging.error(f"Batch prediction error: {e}")
        return _error_response("internal_error", str(e), 500)


def _process_batch(blob_service, predictions: list) -> tuple[list, list]:
    """
    Process all predictions efficiently using pre-loaded models and stats.
    
    Returns:
        Tuple of (results list, cosmos records list)
    """
    # Identify what we need to load
    model_keys = set()  # (sport, span, model_type)
    stats_keys = set()  # (team, span, is_womens)
    
    for pred in predictions:
        model_keys.add((pred['sport'], pred['span'], pred['model']))
        stats_keys.add((pred['home_team'], pred['span'], pred['is_womens']))
        stats_keys.add((pred['away_team'], pred['span'], pred['is_womens']))
    
    logging.info(f"Loading {len(model_keys)} model groups, {len(stats_keys)} team stats")
    
    # Pre-load all models, versions, and stats using shared service
    models_cache = preload_models(blob_service, model_keys)
    model_versions_cache = preload_model_versions(blob_service, model_keys)
    stats_cache = preload_stats(blob_service, stats_keys)
    
    # Run predictions
    results = [None] * len(predictions)
    cosmos_records = []
    
    for pred in predictions:
        try:
            result, record = run_prediction(
                blob_service=blob_service,
                home_team=pred['home_team'],
                away_team=pred['away_team'],
                span=pred['span'],
                sport=pred['sport'],
                model_type=pred['model'],
                neutral=pred['neutral'],
                models_cache=models_cache,
                stats_cache=stats_cache,
                model_versions_cache=model_versions_cache
            )
            results[pred['index']] = result
            if record:
                cosmos_records.append(record)
        except Exception as e:
            logging.error(f"Error predicting {pred['home_team']} vs {pred['away_team']}: {e}")
            results[pred['index']] = {
                'type': 'error',
                'error': {
                    'code': 'validation_error',
                    'message': str(e)
                }
            }
    
    return results, cosmos_records


def _success_response(data: list) -> func.HttpResponse:
    """Return a successful JSON response."""
    return func.HttpResponse(
        json.dumps({"type": "prediction_batch", "output": data}),
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
