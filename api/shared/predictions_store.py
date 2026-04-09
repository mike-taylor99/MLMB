"""
Cosmos DB service for storing and retrieving predictions.
Provides prediction history, caching via content-hash IDs, and query capabilities.
"""
import hashlib
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import (
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential

from app.config import get_settings


class PredictionsStore:
    """
    Service for persisting predictions to Cosmos DB.

    Features:
    - Content-hash based prediction IDs for automatic deduplication
    - Point reads for fast cache lookups
    - Query support for prediction history
    - Conditional inserts to handle race conditions (first write wins)
    """

    _instance: Optional["PredictionsStore"] = None
    _lock = Lock()

    # Cosmos DB configuration
    DATABASE_NAME = "mlmb"
    CONTAINER_NAME = "predictions"
    USER_PREDICTIONS_CONTAINER_NAME = "user_predictions"

    def __new__(cls) -> "PredictionsStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._client: Optional[CosmosClient] = None
        self._database = None
        self._container = None
        self._user_predictions_container = None
        self._initialized = True
        logging.info("PredictionsStore initialized")

    def _ensure_client(self):
        """Ensure the Cosmos client and database are initialized using managed identity."""
        if self._client is None:
            endpoint = get_settings().cosmos_endpoint
            if not endpoint:
                raise ValueError("COSMOS_ENDPOINT not configured")
            self._client = CosmosClient(endpoint, credential=DefaultAzureCredential())
            self._database = self._client.create_database_if_not_exists(
                id=self.DATABASE_NAME
            )

    @property
    def container(self):
        """Get or create the Cosmos DB predictions container."""
        if self._container is None:
            self._ensure_client()
            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [{"path": "/*"}],
                "excludedPaths": [
                    {"path": "/result/*"},
                    {"path": "/feature_hash/?"},
                    {"path": '/"_etag"/?'},
                ],
                "compositeIndexes": [
                    [
                        {"path": "/sport", "order": "ascending"},
                        {"path": "/created_at", "order": "descending"},
                    ],
                    [
                        {"path": "/sport", "order": "ascending"},
                        {"path": "/status", "order": "ascending"},
                        {"path": "/created_at", "order": "descending"},
                    ],
                ],
            }
            self._container = self._database.create_container_if_not_exists(
                id=self.CONTAINER_NAME,
                partition_key=PartitionKey(path="/sport"),
                indexing_policy=indexing_policy,
            )
        return self._container

    @property
    def user_predictions_container(self):
        """Get or create the Cosmos DB user_predictions container."""
        if self._user_predictions_container is None:
            self._ensure_client()
            # Indexing policy optimised for the primary query pattern:
            #   WHERE c.user_id = <pk> AND c.sport = @sport
            #   ORDER BY c.created_at DESC
            indexing_policy = {
                "includedPaths": [{"path": "/*"}],
                "excludedPaths": [{"path": '/"_etag"/?'}],
                "compositeIndexes": [
                    [
                        {"path": "/sport", "order": "ascending"},
                        {"path": "/created_at", "order": "descending"},
                    ]
                ],
            }
            self._user_predictions_container = (
                self._database.create_container_if_not_exists(
                    id=self.USER_PREDICTIONS_CONTAINER_NAME,
                    partition_key=PartitionKey(path="/user_id"),
                    indexing_policy=indexing_policy,
                )
            )
        return self._user_predictions_container

    @staticmethod
    def generate_prediction_id(
        home_team: str,
        away_team: str,
        home_last_played: str,
        away_last_played: str,
        span: int,
        neutral: bool,
        sport: str,
        model: str,
        model_version: str,
    ) -> str:
        """
        Generate a deterministic prediction ID based on input parameters.

        Identical inputs produce identical IDs, enabling automatic deduplication.

        Returns:
            String in format 'pred_{hash}'
        """
        # Create canonical string for hashing
        canonical = "|".join(
            [
                home_team.lower(),
                away_team.lower(),
                home_last_played,
                away_last_played,
                str(span),
                str(neutral).lower(),
                sport.lower(),
                model.lower(),
                model_version.lower(),
            ]
        )

        # Generate SHA256 hash (first 32 chars for reasonable length)
        hash_value = hashlib.sha256(canonical.encode()).hexdigest()[:32]
        return f"pred_{hash_value}"

    @staticmethod
    def generate_feature_hash(feature_values: List[float]) -> str:
        """
        Generate a hash of the feature vector for reproducibility verification.

        Args:
            feature_values: List of feature values in order

        Returns:
            SHA256 hash of the feature vector (first 16 chars)
        """
        # Convert to string with consistent precision
        canonical = "|".join([f"{v:.6f}" for v in feature_values])
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def get_prediction(self, prediction_id: str, sport: str) -> Optional[Dict]:
        """
        Retrieve a prediction by ID (point read).

        This is O(1) and very fast (~5-15ms).

        Args:
            prediction_id: The prediction ID
            sport: Sport partition key (e.g., 'ncaam_basketball', 'ncaaw_basketball')

        Returns:
            Prediction record or None if not found
        """
        try:
            item = self.container.read_item(item=prediction_id, partition_key=sport)
            return item
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logging.error(f"Error reading prediction {prediction_id}: {e}")
            raise

    def create_prediction(self, prediction: Dict) -> Dict:
        """
        Create a new prediction record.

        Uses conditional insert (first write wins) to handle race conditions.
        If a prediction with the same ID already exists, returns the existing one.

        Args:
            prediction: Prediction record to create

        Returns:
            Created or existing prediction record
        """
        try:
            # Attempt to create (will fail if exists)
            created = self.container.create_item(body=prediction)
            logging.info(f"Created prediction: {prediction['id']}")
            return created
        except CosmosResourceExistsError:
            # Race condition: another request created it first
            # Return the existing record
            logging.info(
                f"Prediction already exists (race condition): {prediction['id']}"
            )
            return self.get_prediction(prediction["id"], prediction["sport"])
        except Exception as e:
            logging.error(f"Error creating prediction: {e}")
            raise

    def create_predictions_bulk(self, predictions: List[Dict]) -> tuple[int, int]:
        """
        Create multiple predictions, skipping any that already exist.

        Strategy:
        1. Query for existing IDs (one query per partition)
        2. Filter to only new predictions
        3. Batch create only new ones

        This preserves original records while maintaining batch efficiency.

        Args:
            predictions: List of prediction records to create

        Returns:
            Tuple of (created_count, skipped_count)
        """
        if not predictions:
            return 0, 0

        # Group by partition key (sport)
        by_sport: Dict[str, List[Dict]] = {}
        for pred in predictions:
            sport = pred["sport"]
            if sport not in by_sport:
                by_sport[sport] = []
            by_sport[sport].append(pred)

        total_created = 0
        total_skipped = 0

        for sport, sport_predictions in by_sport.items():
            # Get all IDs we want to create
            all_ids = [p["id"] for p in sport_predictions]

            # Query for which IDs already exist
            existing_ids = self._get_existing_ids(sport, all_ids)

            # Filter to only new predictions
            new_predictions = [
                p for p in sport_predictions if p["id"] not in existing_ids
            ]
            skipped = len(sport_predictions) - len(new_predictions)
            total_skipped += skipped

            if not new_predictions:
                continue

            # Batch create new predictions (100 per batch)
            batch_size = 100
            for i in range(0, len(new_predictions), batch_size):
                batch = new_predictions[i : i + batch_size]
                operations = [("create", (pred,), {}) for pred in batch]

                try:
                    self.container.execute_item_batch(
                        batch_operations=operations, partition_key=sport
                    )
                    total_created += len(batch)
                except Exception as e:
                    logging.error(f"Batch create error for {sport}: {e}")
                    # Fall back to individual creates
                    for pred in batch:
                        try:
                            self.container.create_item(body=pred)
                            total_created += 1
                        except CosmosResourceExistsError:
                            total_skipped += 1
                        except Exception as inner_e:
                            logging.error(
                                f"Create failed for {pred.get('id')}: {inner_e}"
                            )

        logging.info(
            f"Bulk write: {total_created} created, {total_skipped} skipped (already existed)"
        )
        return total_created, total_skipped

    def _get_existing_ids(self, sport: str, ids: List[str]) -> set:
        """
        Query for which prediction IDs already exist in a partition.

        Uses batched IN queries (max 256 items per query) for efficiency.
        """
        existing = set()
        batch_size = 256  # Cosmos IN clause limit

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            placeholders = ", ".join([f"@id{j}" for j in range(len(batch_ids))])
            parameters = [
                {"name": f"@id{j}", "value": id_val}
                for j, id_val in enumerate(batch_ids)
            ]

            query = f"SELECT c.id FROM c WHERE c.sport = @sport AND c.id IN ({placeholders})"
            parameters.append({"name": "@sport", "value": sport})

            try:
                results = self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False,
                )
                for item in results:
                    existing.add(item["id"])
            except Exception as e:
                logging.warning(f"Error checking existing IDs: {e}")

        return existing

    def query_predictions(
        self,
        sport: str,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        model_version: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query predictions with optional filters (cursor-based pagination).

        Args:
            sport: Required partition key (e.g., 'ncaam_basketball', 'ncaaw_basketball')
            home_team: Optional home team filter
            away_team: Optional away team filter
            model_version: Optional model version filter
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
            limit: Max results to return (default 20)
            before_id: Get items created before this prediction ID
            after_id: Get items created after this prediction ID

        Returns:
            List of matching predictions
        """
        # Build query dynamically
        conditions = ["c.sport = @sport", "c.status = 'completed'"]
        parameters = [{"name": "@sport", "value": sport}]

        if home_team:
            conditions.append("c.home_team = @home_team")
            parameters.append({"name": "@home_team", "value": home_team.lower()})

        if away_team:
            conditions.append("c.away_team = @away_team")
            parameters.append({"name": "@away_team", "value": away_team.lower()})

        if model_version:
            conditions.append("c.model_version = @model_version")
            parameters.append({"name": "@model_version", "value": model_version})

        if start_date:
            conditions.append("c.created_at >= @start_date")
            parameters.append({"name": "@start_date", "value": start_date})

        if end_date:
            conditions.append("c.created_at <= @end_date")
            parameters.append({"name": "@end_date", "value": end_date})

        # Handle cursor-based pagination
        # We need to get the created_at of the cursor item for comparison
        if before_id or after_id:
            cursor_id = before_id or after_id
            cursor_item = self.get_prediction(cursor_id, sport)
            if cursor_item:
                cursor_timestamp = cursor_item.get("created_at")
                if before_id:
                    # Get items newer than cursor (created_at > cursor)
                    conditions.append("c.created_at > @cursor_timestamp")
                else:  # after_id
                    # Get items older than cursor (created_at < cursor)
                    conditions.append("c.created_at < @cursor_timestamp")
                parameters.append(
                    {"name": "@cursor_timestamp", "value": cursor_timestamp}
                )

        query = f"""
            SELECT * FROM c 
            WHERE {' AND '.join(conditions)}
            ORDER BY c.created_at DESC
            OFFSET 0 LIMIT {limit}
        """

        try:
            items = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False,  # Partition key required
                )
            )
            return items
        except Exception as e:
            logging.error(f"Error querying predictions: {e}")
            raise

    def build_prediction_record(
        self,
        prediction_id: str,
        home_team: str,
        away_team: str,
        home_last_played: str,
        away_last_played: str,
        span: int,
        neutral: bool,
        sport: str,
        model: str,
        model_version: str,
        feature_hash: str,
        home_win_probability: float,
        predicted_winner: str,
    ) -> Dict:
        """
        Build a complete prediction record.

        Args:
            All prediction inputs and outputs

        Returns:
            Dict ready for Cosmos DB insertion
        """
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return {
            "id": prediction_id,
            "status": "completed",
            "home_team": home_team.lower(),
            "away_team": away_team.lower(),
            "home_last_played": home_last_played,
            "away_last_played": away_last_played,
            "span": span,
            "neutral": neutral,
            "sport": sport,
            "model": model,
            "model_version": model_version,
            "feature_hash": feature_hash,
            "result": {
                "home_win_probability": round(home_win_probability, 4),
                "away_win_probability": round(1 - home_win_probability, 4),
                "predicted_winner": predicted_winner,
            },
            "created_at": now,
            "completed_at": now,
        }

    # ==================== User Predictions ====================

    def link_user_prediction(
        self,
        user_id: str,
        prediction_id: str,
        sport: str,
    ) -> None:
        """
        Link a prediction to a user for scoped history.

        Uses a composite ID (user_id + prediction_id) so the same user
        making the same prediction is idempotent.

        Args:
            user_id: SWA userId (stable, opaque hash per provider)
            prediction_id: The prediction content-hash ID
            sport: Sport code
        """
        doc_id = f"{user_id}_{prediction_id}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        record = {
            "id": doc_id,
            "user_id": user_id,
            "prediction_id": prediction_id,
            "sport": sport,
            "created_at": now,
        }

        try:
            self.user_predictions_container.create_item(body=record)
            logging.info(f"Linked prediction {prediction_id} to user {user_id}")
        except CosmosResourceExistsError:
            # Already linked — idempotent
            pass
        except Exception as e:
            logging.error(f"Error linking prediction to user: {e}")

    def link_user_predictions_bulk(
        self,
        user_id: str,
        prediction_ids: List[str],
        sport: str,
    ) -> None:
        """
        Link multiple predictions to a user in bulk.

        Args:
            user_id: SWA userId
            prediction_ids: List of prediction IDs
            sport: Sport code
        """
        if not prediction_ids:
            return

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        records = []
        for pid in prediction_ids:
            records.append(
                {
                    "id": f"{user_id}_{pid}",
                    "user_id": user_id,
                    "prediction_id": pid,
                    "sport": sport,
                    "created_at": now,
                }
            )

        # Batch create (100 per batch, single partition)
        batch_size = 100
        created = 0
        skipped = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            operations = [("create", (rec,), {}) for rec in batch]
            try:
                self.user_predictions_container.execute_item_batch(
                    batch_operations=operations,
                    partition_key=user_id,
                )
                created += len(batch)
            except Exception:
                # Fall back to individual creates
                for rec in batch:
                    try:
                        self.user_predictions_container.create_item(body=rec)
                        created += 1
                    except CosmosResourceExistsError:
                        skipped += 1
                    except Exception as e:
                        logging.error(f"Error linking prediction: {e}")

        logging.info(f"Bulk user link: {created} created, {skipped} skipped")

    def query_user_predictions(
        self,
        user_id: str,
        sport: str,
        limit: int = 20,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query a user's prediction history, returning full prediction records.

        Fetches user_prediction links first, then hydrates with prediction data.

        Args:
            user_id: SWA userId (partition key)
            sport: Sport filter
            limit: Max results
            before_id: Cursor — get predictions newer than this
            after_id: Cursor — get predictions older than this

        Returns:
            List of prediction records (from the predictions container)
        """
        # Build query for user_predictions container
        conditions = ["c.user_id = @user_id", "c.sport = @sport"]
        parameters: List[Dict[str, Any]] = [
            {"name": "@user_id", "value": user_id},
            {"name": "@sport", "value": sport},
        ]

        # Cursor-based pagination
        if before_id or after_id:
            cursor_doc_id = f"{user_id}_{before_id or after_id}"
            try:
                cursor_item = self.user_predictions_container.read_item(
                    item=cursor_doc_id, partition_key=user_id
                )
                cursor_ts = cursor_item.get("created_at")
                if before_id:
                    conditions.append("c.created_at > @cursor_ts")
                else:
                    conditions.append("c.created_at < @cursor_ts")
                parameters.append({"name": "@cursor_ts", "value": cursor_ts})
            except CosmosResourceNotFoundError:
                pass  # Invalid cursor — ignore

        query = f"""
            SELECT c.prediction_id FROM c
            WHERE {' AND '.join(conditions)}
            ORDER BY c.created_at DESC
            OFFSET 0 LIMIT {limit}
        """

        try:
            links = list(
                self.user_predictions_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False,
                )
            )
        except Exception as e:
            logging.error(f"Error querying user predictions: {e}")
            raise

        if not links:
            return []

        # Hydrate — fetch full prediction records
        prediction_ids = [link["prediction_id"] for link in links]
        records = []
        for pid in prediction_ids:
            record = self.get_prediction(pid, sport)
            if record:
                records.append(record)

        return records

    # ------------------------------------------------------------------
    # Analysis cache (stored in the same predictions container)
    # ------------------------------------------------------------------

    ANALYSIS_CONTAINER_NAME = "analyses"

    @property
    def analysis_container(self):
        """Get or create the Cosmos DB analyses container."""
        if not hasattr(self, "_analysis_container") or self._analysis_container is None:
            self._ensure_client()
            self._analysis_container = self._database.create_container_if_not_exists(
                id=self.ANALYSIS_CONTAINER_NAME,
                partition_key=PartitionKey(path="/sport"),
            )
        return self._analysis_container

    def get_analysis(self, analysis_id: str, sport: str) -> Optional[Dict]:
        """
        Retrieve a cached analysis by ID (point read).

        Args:
            analysis_id: The analysis content-hash ID.
            sport: Sport partition key.

        Returns:
            Analysis record or None if not found.
        """
        try:
            item = self.analysis_container.read_item(
                item=analysis_id, partition_key=sport
            )
            return item
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logging.error(f"Error reading analysis {analysis_id}: {e}")
            raise

    def create_analysis(self, record: Dict) -> Dict:
        """
        Persist an analysis record.  First-write-wins on conflict.

        Args:
            record: Analysis record to store.

        Returns:
            Created or existing record.
        """
        try:
            created = self.analysis_container.create_item(body=record)
            logging.info(f"Created analysis: {record['id']}")
            return created
        except CosmosResourceExistsError:
            logging.info(f"Analysis already exists (race): {record['id']}")
            return self.get_analysis(record["id"], record["sport"])
        except Exception as e:
            logging.error(f"Error creating analysis: {e}")
            raise


# Convenience function to get the singleton instance
def get_predictions_store() -> PredictionsStore:
    """Get the singleton PredictionsStore instance."""
    return PredictionsStore()
