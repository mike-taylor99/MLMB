"""Background tasks for async operations.

These tasks run after the response is sent to the client.
Used for non-critical operations like caching to Cosmos DB.

Defined as regular functions (not async) so FastAPI runs them in a
thread pool, since the underlying Cosmos SDK calls are synchronous.
"""

import logging

from shared.predictions_store import PredictionsStore


def write_prediction(predictions_store: PredictionsStore, record: dict) -> None:
    """Write a single prediction to Cosmos DB."""
    try:
        predictions_store.create_prediction(record)
        logging.info(f"Background write completed: {record['id']}")
    except Exception as e:
        logging.error(f"Background write failed for {record['id']}: {e}")


def write_predictions_bulk(
    predictions_store: PredictionsStore, records: list[dict]
) -> None:
    """Write multiple predictions to Cosmos DB."""
    try:
        created, skipped = predictions_store.create_predictions_bulk(records)
        logging.info(f"Background bulk write: {created} created, {skipped} skipped")
    except Exception as e:
        logging.error(f"Background bulk write failed: {e}")


def link_user_prediction(
    predictions_store: PredictionsStore,
    user_id: str,
    prediction_id: str,
    sport: str,
) -> None:
    """Link a single prediction to a user for scoped history."""
    try:
        predictions_store.link_user_prediction(user_id, prediction_id, sport)
    except Exception as e:
        logging.error(f"Background user link failed for {prediction_id}: {e}")


def link_user_predictions_bulk(
    predictions_store: PredictionsStore,
    user_id: str,
    prediction_ids: list[str],
    sport: str,
) -> None:
    """Link multiple predictions to a user for scoped history."""
    try:
        predictions_store.link_user_predictions_bulk(user_id, prediction_ids, sport)
    except Exception as e:
        logging.error(f"Background bulk user link failed: {e}")
