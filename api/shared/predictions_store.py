"""
Cosmos DB service for storing and retrieving predictions.
Provides prediction history, caching via content-hash IDs, and query capabilities.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosResourceNotFoundError


class PredictionsStore:
    """
    Service for persisting predictions to Cosmos DB.
    
    Features:
    - Content-hash based prediction IDs for automatic deduplication
    - Point reads for fast cache lookups
    - Query support for prediction history
    - Conditional inserts to handle race conditions (first write wins)
    """
    
    _instance: Optional['PredictionsStore'] = None
    _lock = Lock()
    
    # Cosmos DB configuration
    DATABASE_NAME = 'mlmb'
    CONTAINER_NAME = 'predictions'
    
    def __new__(cls) -> 'PredictionsStore':
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
        self._initialized = True
        logging.info("PredictionsStore initialized")
    
    @property
    def container(self):
        """Get or create the Cosmos DB container."""
        if self._container is None:
            conn_str = os.getenv('COSMOS_CONNECTION_STRING')
            if not conn_str:
                raise ValueError("COSMOS_CONNECTION_STRING environment variable not set")
            
            self._client = CosmosClient.from_connection_string(conn_str)
            self._database = self._client.create_database_if_not_exists(id=self.DATABASE_NAME)
            self._container = self._database.create_container_if_not_exists(
                id=self.CONTAINER_NAME,
                partition_key=PartitionKey(path='/sport'),
                offer_throughput=400  # Minimum RU/s for serverless
            )
        return self._container
    
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
        model_version: str
    ) -> str:
        """
        Generate a deterministic prediction ID based on input parameters.
        
        Identical inputs produce identical IDs, enabling automatic deduplication.
        
        Returns:
            String in format 'pred_{hash}'
        """
        # Create canonical string for hashing
        canonical = '|'.join([
            home_team.lower(),
            away_team.lower(),
            home_last_played,
            away_last_played,
            str(span),
            str(neutral).lower(),
            sport.lower(),
            model.lower(),
            model_version.lower()
        ])
        
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
        canonical = '|'.join([f"{v:.6f}" for v in feature_values])
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
            logging.info(f"Prediction already exists (race condition): {prediction['id']}")
            return self.get_prediction(prediction['id'], prediction['sport'])
        except Exception as e:
            logging.error(f"Error creating prediction: {e}")
            raise
    
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
        after_id: Optional[str] = None
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
                cursor_timestamp = cursor_item.get('created_at')
                if before_id:
                    # Get items newer than cursor (created_at > cursor)
                    conditions.append("c.created_at > @cursor_timestamp")
                else:  # after_id
                    # Get items older than cursor (created_at < cursor)
                    conditions.append("c.created_at < @cursor_timestamp")
                parameters.append({"name": "@cursor_timestamp", "value": cursor_timestamp})
        
        query = f"""
            SELECT * FROM c 
            WHERE {' AND '.join(conditions)}
            ORDER BY c.created_at DESC
            OFFSET 0 LIMIT {limit}
        """
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=False  # Partition key required
            ))
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
        predicted_winner: str
    ) -> Dict:
        """
        Build a complete prediction record.
        
        Args:
            All prediction inputs and outputs
            
        Returns:
            Dict ready for Cosmos DB insertion
        """
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        return {
            'id': prediction_id,
            'status': 'completed',
            'home_team': home_team.lower(),
            'away_team': away_team.lower(),
            'home_last_played': home_last_played,
            'away_last_played': away_last_played,
            'span': span,
            'neutral': neutral,
            'sport': sport,
            'model': model,
            'model_version': model_version,
            'feature_hash': feature_hash,
            'result': {
                'home_win_probability': round(home_win_probability, 4),
                'away_win_probability': round(1 - home_win_probability, 4),
                'predicted_winner': predicted_winner
            },
            'created_at': now,
            'completed_at': now
        }


# Convenience function to get the singleton instance
def get_predictions_store() -> PredictionsStore:
    """Get the singleton PredictionsStore instance."""
    return PredictionsStore()
