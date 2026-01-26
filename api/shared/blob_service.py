"""
Singleton service for Azure Blob Storage interactions.
Provides centralized caching and access for all endpoints.
"""
import io
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any, Dict, List, Optional

import joblib
from azure.storage.blob import BlobServiceClient

# Pre-import sklearn to avoid circular import errors during parallel model loading
# This ensures all sklearn modules are fully initialized before ThreadPoolExecutor starts
import sklearn.base
import sklearn.ensemble
import sklearn.linear_model
import sklearn.neighbors
import sklearn.neural_network
import sklearn.svm


class BlobStorageService:
    """
    Singleton service for interacting with Azure Blob Storage.
    
    Provides:
    - Shared BlobServiceClient connection
    - Centralized caching for models, team stats, and top25 data
    - Thread-safe loading operations
    - Parallel model loading for cold starts
    """
    
    _instance: Optional['BlobStorageService'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'BlobStorageService':
        if cls._instance is None:
            with cls._lock:
                # Double-check pattern for thread safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._client: Optional[BlobServiceClient] = None
        
        # Caches
        self._models_cache: Dict[str, Dict[str, Any]] = {
            'mens': {},
            'womens': {}
        }
        self._team_stats_cache: Dict[str, Optional[Dict]] = {
            'mens': None,
            'womens': None
        }
        self._top25_cache: Dict[str, Optional[Dict]] = {
            'mens': None,
            'womens': None
        }
        
        # Container names
        self.MODELS_CONTAINER = 'mlmb-models'
        self.API_CONTAINER = 'mlmb-api'
        
        self._initialized = True
        logging.info("BlobStorageService initialized")
    
    @property
    def client(self) -> BlobServiceClient:
        """Get or create the BlobServiceClient."""
        if self._client is None:
            conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            if not conn_str:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
            self._client = BlobServiceClient.from_connection_string(conn_str)
        return self._client
    
    def _get_cache_key(self, is_womens: bool) -> str:
        return 'womens' if is_womens else 'mens'
    
    # ==================== Team Stats ====================
    
    def get_team_stats(self, is_womens: bool = False) -> Dict:
        """
        Load team stats from Blob Storage with caching.
        
        Args:
            is_womens: Whether to load women's stats
            
        Returns:
            Dict of team stats keyed by span
        """
        cache_key = self._get_cache_key(is_womens)
        
        if self._team_stats_cache[cache_key] is not None:
            return self._team_stats_cache[cache_key]
        
        blob_name = 'womens-team-stats' if is_womens else 'team-stats'
        logging.info(f"Loading team stats: {blob_name}")
        
        try:
            blob_client = self.client.get_blob_client(
                container=self.API_CONTAINER, 
                blob=blob_name
            )
            blob_data = blob_client.download_blob().readall()
            data = json.loads(blob_data.decode())
            self._team_stats_cache[cache_key] = data
            return data
        except Exception as e:
            logging.error(f"Failed to load team stats ({blob_name}): {e}")
            raise
    
    def get_matchup_stats(self, team1: str, team2: str, span: int, is_womens: bool = False) -> Dict:
        """
        Get stats for both teams in a matchup.
        
        Args:
            team1: First team name
            team2: Second team name
            span: Span value (3, 5, or 7)
            is_womens: Whether this is women's data
            
        Returns:
            Dict with 'team1' and 'team2' keys containing stats
        """
        stats = self.get_team_stats(is_womens)
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
    
    # ==================== Top 25 ====================
    
    def get_top25(self, is_womens: bool = False) -> tuple[Dict, str]:
        """
        Load top 25 rankings from Blob Storage with caching.
        
        Args:
            is_womens: Whether to load women's rankings
            
        Returns:
            Tuple of (data dict, last_modified ISO string)
        """
        cache_key = self._get_cache_key(is_womens)
        
        if self._top25_cache[cache_key] is not None:
            return self._top25_cache[cache_key]
        
        blob_name = 'womens-top25' if is_womens else 'top25'
        logging.info(f"Loading top 25: {blob_name}")
        
        try:
            blob_client = self.client.get_blob_client(
                container=self.API_CONTAINER,
                blob=blob_name
            )
            # Get blob properties for last_modified
            properties = blob_client.get_blob_properties()
            last_modified = properties.last_modified.isoformat().replace('+00:00', 'Z')
            
            blob_data = blob_client.download_blob().readall()
            data = json.loads(blob_data.decode())
            
            # Cache both data and metadata
            self._top25_cache[cache_key] = (data, last_modified)
            return data, last_modified
        except Exception as e:
            logging.error(f"Failed to load top 25 ({blob_name}): {e}")
            raise
    
    # ==================== Models ====================
    
    def get_model(self, model_name: str, is_womens: bool = False) -> Any:
        """
        Load a single model from Blob Storage with caching.
        
        Args:
            model_name: Name of the model (without .pkl extension)
            is_womens: Whether to load women's model
            
        Returns:
            Loaded sklearn model
        """
        cache_key = self._get_cache_key(is_womens)
        
        if model_name in self._models_cache[cache_key]:
            return self._models_cache[cache_key][model_name]
        
        gender_path = 'womens' if is_womens else 'mens'
        blob_path = f"{gender_path}/{model_name}.pkl"
        
        try:
            blob_client = self.client.get_blob_client(
                container=self.MODELS_CONTAINER,
                blob=blob_path
            )
            model_bytes = blob_client.download_blob().readall()
            model = joblib.load(io.BytesIO(model_bytes))
            self._models_cache[cache_key][model_name] = model
            logging.info(f"Loaded model: {model_name}")
            return model
        except Exception as e:
            logging.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def get_models_parallel(self, model_names: List[str], is_womens: bool = False) -> Dict[str, Any]:
        """
        Load multiple models in parallel, returning them in sorted order.
        
        This is optimized for cold starts where multiple models need to be loaded.
        Models are returned in sorted order for deterministic ensemble predictions.
        
        Args:
            model_names: List of model names to load
            is_womens: Whether to load women's models
            
        Returns:
            Dict of models keyed by name in sorted order
            
        Raises:
            RuntimeError: If any model fails to load
        """
        cache_key = self._get_cache_key(is_womens)
        
        # Check which models need to be loaded
        models_to_load = [name for name in model_names if name not in self._models_cache[cache_key]]
        
        if models_to_load:
            logging.info(f"Cold start: loading {len(models_to_load)} models in parallel")
            
            errors = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = {
                    executor.submit(self.get_model, name, is_womens): name 
                    for name in models_to_load
                }
                for future in as_completed(futures):
                    model_name = futures[future]
                    try:
                        future.result()  # Model is cached by get_model
                    except Exception as e:
                        logging.error(f"Failed to load model {model_name}: {e}")
                        errors.append((model_name, str(e)))
            
            if errors:
                failed_names = [name for name, _ in errors]
                raise RuntimeError(f"Failed to load {len(errors)} model(s): {failed_names}")
        
        # Verify all requested models are now in cache
        missing = [name for name in model_names if name not in self._models_cache[cache_key]]
        if missing:
            raise RuntimeError(f"Models missing from cache after loading: {missing}")
        
        # Return models in sorted order for deterministic iteration
        return {name: self._models_cache[cache_key][name] for name in sorted(model_names)}
    
    # ==================== Cache Management ====================
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cached data.
        
        Args:
            cache_type: 'models', 'stats', 'top25', or None for all
        """
        if cache_type is None or cache_type == 'models':
            self._models_cache = {'mens': {}, 'womens': {}}
            logging.info("Cleared models cache")
            
        if cache_type is None or cache_type == 'stats':
            self._team_stats_cache = {'mens': None, 'womens': None}
            logging.info("Cleared team stats cache")
            
        if cache_type is None or cache_type == 'top25':
            self._top25_cache = {'mens': None, 'womens': None}
            logging.info("Cleared top 25 cache")
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics."""
        return {
            'models': {
                'mens': len(self._models_cache['mens']),
                'womens': len(self._models_cache['womens'])
            },
            'team_stats': {
                'mens': self._team_stats_cache['mens'] is not None,
                'womens': self._team_stats_cache['womens'] is not None
            },
            'top25': {
                'mens': self._top25_cache['mens'] is not None,
                'womens': self._top25_cache['womens'] is not None
            }
        }


# Convenience function to get the singleton instance
def get_blob_service() -> BlobStorageService:
    """Get the singleton BlobStorageService instance."""
    return BlobStorageService()
