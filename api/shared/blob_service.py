"""
Singleton service for Azure Blob Storage interactions.
Provides centralized caching and access for all endpoints.
"""
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
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
        
        # Caches - keyed by sport code
        self._models_cache: Dict[str, Dict[str, Any]] = {
            'ncaam_basketball': {},
            'ncaaw_basketball': {}
        }
        self._team_stats_cache: Dict[str, Optional[Dict]] = {
            'ncaam_basketball': None,
            'ncaaw_basketball': None
        }
        self._top25_cache: Dict[str, Optional[Dict]] = {
            'ncaam_basketball': None,
            'ncaaw_basketball': None
        }
        self._teams_cache: Optional[tuple] = None  # (teams_list, last_modified)
        
        # Manifest and schema caches
        self._models_manifest_cache: Optional[Dict] = None
        self._feature_schema_cache: Optional[Dict] = None
        self._manifest_lock = Lock()
        self._schema_lock = Lock()
        
        # Per-resource locks to prevent parallel downloads of the same resource
        self._team_stats_locks: Dict[str, Lock] = {'ncaam_basketball': Lock(), 'ncaaw_basketball': Lock()}
        self._top25_locks: Dict[str, Lock] = {'ncaam_basketball': Lock(), 'ncaaw_basketball': Lock()}
        self._teams_lock = Lock()
        self._model_locks: Dict[str, Lock] = {}  # Dynamic per-model locks
        self._model_locks_lock = Lock()  # Lock for creating model locks
        
        # Container names
        self.MODELS_CONTAINER = 'mlmb-models'
        self.API_CONTAINER = 'mlmb-api'
        
        self._initialized = True
        logging.info("BlobStorageService initialized")
    
    @property
    def client(self) -> BlobServiceClient:
        """Get or create the BlobServiceClient."""
        if self._client is None:
            from app.config import get_settings
            conn_str = get_settings().azure_storage_connection_string
            if not conn_str:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING not configured")
            self._client = BlobServiceClient.from_connection_string(conn_str)
        return self._client
    
    def _get_cache_key(self, is_womens: bool) -> str:
        """Get cache key from is_womens flag."""
        return 'ncaaw_basketball' if is_womens else 'ncaam_basketball'
    
    # ==================== Team Stats ====================
    
    def get_team_stats(self, is_womens: bool = False) -> Dict:
        """
        Load team stats from Blob Storage with caching.
        Thread-safe: uses double-checked locking to prevent parallel downloads.
        
        Args:
            is_womens: Whether to load women's stats
            
        Returns:
            Dict of team stats keyed by span
        """
        cache_key = self._get_cache_key(is_womens)
        
        # Fast path - already cached
        if self._team_stats_cache[cache_key] is not None:
            return self._team_stats_cache[cache_key]
        
        # Slow path - acquire lock to prevent parallel downloads
        with self._team_stats_locks[cache_key]:
            # Double-check after acquiring lock
            if self._team_stats_cache[cache_key] is not None:
                return self._team_stats_cache[cache_key]
            
            blob_name = f'{cache_key}/team-stats'
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
    
    # ==================== Models Manifest ====================
    
    def get_models_manifest(self) -> Dict:
        """
        Load the models manifest from Blob Storage with caching.
        The manifest tracks model versions, paths, and metadata.
        
        Returns:
            Dict containing manifest data
        """
        if self._models_manifest_cache is not None:
            return self._models_manifest_cache
        
        with self._manifest_lock:
            if self._models_manifest_cache is not None:
                return self._models_manifest_cache
            
            # Try loading from blob storage first, fall back to local file
            try:
                blob_client = self.client.get_blob_client(
                    container=self.MODELS_CONTAINER,
                    blob='models_manifest.json'
                )
                blob_data = blob_client.download_blob().readall()
                self._models_manifest_cache = json.loads(blob_data.decode())
                logging.info("Loaded models manifest from blob storage")
            except Exception as e:
                logging.warning(f"Failed to load manifest from blob, using local: {e}")
                # Fall back to local file
                local_path = Path(__file__).parent / 'models_manifest.json'
                with open(local_path, 'r') as f:
                    self._models_manifest_cache = json.load(f)
                logging.info("Loaded models manifest from local file")
            
            return self._models_manifest_cache
    
    def get_model_version(self, sport: str, span: int, model_type: str) -> str:
        """
        Get the current model version for a specific model.
        
        Args:
            sport: Sport code (e.g., 'ncaam_basketball', 'ncaaw_basketball')
            span: 3, 5, or 7
            model_type: Model type key (e.g., 'logistic_regression', 'knn')
            
        Returns:
            Current version string (e.g., 'v1')
        """
        manifest = self.get_models_manifest()
        span_key = f'{span}span'
        
        try:
            return manifest[sport][span_key][model_type]['current']
        except KeyError:
            logging.warning(f"Model not in manifest: {sport}/{span_key}/{model_type}, defaulting to v1")
            return 'v1'
    
    def get_model_blob_path(self, sport: str, span: int, model_type: str, version: Optional[str] = None) -> str:
        """
        Get the blob path for a specific model version.
        
        Args:
            sport: Sport code (e.g., 'ncaam_basketball', 'ncaaw_basketball')
            span: 3, 5, or 7
            model_type: Model type key
            version: Specific version or None for current
            
        Returns:
            Blob path string
        """
        manifest = self.get_models_manifest()
        span_key = f'{span}span'
        
        try:
            model_info = manifest[sport][span_key][model_type]
            if version is None:
                version = model_info['current']
            return model_info['versions'][version]['blob_path']
        except KeyError:
            # Fall back to legacy path format
            logging.warning(f"Model path not in manifest, using legacy format")
            from predict import MODEL_NAME_MAP
            blob_name = MODEL_NAME_MAP.get(model_type, model_type)
            return f"{sport}/{span}span_{blob_name}.pkl"
    
    # ==================== Feature Schema ====================
    
    def get_feature_schema(self, is_womens: bool = False) -> Dict:
        """
        Load the feature schema from team stats' _meta field with caching.
        The schema defines feature names for DataFrame construction.
        
        Args:
            is_womens: Whether to load women's schema (both should be identical)
            
        Returns:
            Dict containing schema data with 'features', 'away_prefix', 'extra_features'
        """
        if self._feature_schema_cache is not None:
            return self._feature_schema_cache
        
        with self._schema_lock:
            if self._feature_schema_cache is not None:
                return self._feature_schema_cache
            
            # Get feature schema from team stats _meta field
            team_stats = self.get_team_stats(is_womens)
            if '_meta' not in team_stats:
                raise ValueError("Team stats missing _meta field with feature schema")
            
            self._feature_schema_cache = team_stats['_meta']
            logging.info("Loaded feature schema from team stats _meta")
            return self._feature_schema_cache
    
    def get_feature_names(self) -> List[str]:
        """
        Get the full ordered list of feature names for model input.
        
        Returns:
            List of feature names in order: [home_features, away_features, extra_features]
        """
        schema = self.get_feature_schema()
        
        # Build full feature list: home + away (with prefix) + extras
        home_features = schema['features']  # No prefix for home
        away_prefix = schema.get('away_prefix', 'opp_')
        away_features = [f"{away_prefix}{f}" for f in schema['features']]
        extra_features = schema.get('extra_features', ['Neutral'])
        
        return home_features + away_features + extra_features
    
    def build_feature_dataframe(
        self, 
        home_stats: List[float], 
        away_stats: List[float], 
        neutral: bool
    ) -> pd.DataFrame:
        """
        Build a named DataFrame for model prediction.
        
        This ensures feature names match what the model was trained with,
        eliminating sklearn warnings about unnamed features.
        
        Args:
            home_stats: List of home team statistics
            away_stats: List of away team statistics  
            neutral: Whether game is at neutral site
            
        Returns:
            Single-row DataFrame with named columns
        """
        feature_names = self.get_feature_names()
        feature_values = home_stats + away_stats + [int(neutral)]
        
        if len(feature_values) != len(feature_names):
            raise ValueError(
                f"Feature count mismatch: got {len(feature_values)} values, "
                f"expected {len(feature_names)} features"
            )
        
        return pd.DataFrame([dict(zip(feature_names, feature_values))])
    
    # ==================== Top 25 ====================
    
    def get_top25(self, is_womens: bool = False) -> tuple[Dict, str]:
        """
        Load top 25 rankings from Blob Storage with caching.
        Thread-safe: uses double-checked locking to prevent parallel downloads.
        
        Args:
            is_womens: Whether to load women's rankings
            
        Returns:
            Tuple of (data dict, last_modified ISO string)
        """
        cache_key = self._get_cache_key(is_womens)
        
        # Fast path - already cached
        if self._top25_cache[cache_key] is not None:
            return self._top25_cache[cache_key]
        
        # Slow path - acquire lock to prevent parallel downloads
        with self._top25_locks[cache_key]:
            # Double-check after acquiring lock
            if self._top25_cache[cache_key] is not None:
                return self._top25_cache[cache_key]
            
            blob_name = f'{cache_key}/top25'
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
    
    # ==================== Teams ====================
    
    def get_teams(self) -> tuple[list, str]:
        """
        Load teams data from Blob Storage with caching.
        Thread-safe: uses double-checked locking to prevent parallel downloads.
        
        Returns:
            Tuple of (teams list, last_modified ISO string)
        """
        # Fast path - already cached
        if self._teams_cache is not None:
            return self._teams_cache
        
        # Slow path - acquire lock to prevent parallel downloads
        with self._teams_lock:
            # Double-check after acquiring lock
            if self._teams_cache is not None:
                return self._teams_cache
            
            blob_name = 'teams'
            logging.info(f"Loading teams: {blob_name}")
            
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
                self._teams_cache = (data, last_modified)
                return data, last_modified
            except Exception as e:
                logging.error(f"Failed to load teams ({blob_name}): {e}")
                raise
    
    # ==================== Models ====================
    
    def _get_model_lock(self, model_name: str, is_womens: bool) -> Lock:
        """
        Get or create a lock for a specific model.
        Thread-safe creation of per-model locks.
        """
        lock_key = f"{self._get_cache_key(is_womens)}_{model_name}"
        if lock_key not in self._model_locks:
            with self._model_locks_lock:
                # Double-check after acquiring lock
                if lock_key not in self._model_locks:
                    self._model_locks[lock_key] = Lock()
        return self._model_locks[lock_key]
    
    def get_model(self, model_name: str, is_womens: bool = False) -> Any:
        """
        Load a single model from Blob Storage with caching.
        Thread-safe: uses per-model locks to prevent parallel downloads of the same model.
        
        Args:
            model_name: Name of the model (without .pkl extension)
            is_womens: Whether to load women's model
            
        Returns:
            Loaded sklearn model
        """
        cache_key = self._get_cache_key(is_womens)
        
        # Fast path - already cached
        if model_name in self._models_cache[cache_key]:
            return self._models_cache[cache_key][model_name]
        
        # Slow path - acquire per-model lock to prevent parallel downloads
        with self._get_model_lock(model_name, is_womens):
            # Double-check after acquiring lock
            if model_name in self._models_cache[cache_key]:
                return self._models_cache[cache_key][model_name]
            
            # Use sport code as path prefix (ncaam_basketball/ or ncaaw_basketball/)
            blob_path = f"{cache_key}/{model_name}.pkl"
            
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
            cache_type: 'models', 'stats', 'top25', 'manifest', 'schema', or None for all
        """
        if cache_type is None or cache_type == 'models':
            self._models_cache = {'ncaam_basketball': {}, 'ncaaw_basketball': {}}
            logging.info("Cleared models cache")
            
        if cache_type is None or cache_type == 'stats':
            self._team_stats_cache = {'ncaam_basketball': None, 'ncaaw_basketball': None}
            logging.info("Cleared team stats cache")
            
        if cache_type is None or cache_type == 'top25':
            self._top25_cache = {'ncaam_basketball': None, 'ncaaw_basketball': None}
            logging.info("Cleared top 25 cache")
        
        if cache_type is None or cache_type == 'manifest':
            self._models_manifest_cache = None
            logging.info("Cleared models manifest cache")
        
        if cache_type is None or cache_type == 'schema':
            self._feature_schema_cache = None
            logging.info("Cleared feature schema cache")
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics."""
        return {
            'models': {
                'ncaam_basketball': len(self._models_cache['ncaam_basketball']),
                'ncaaw_basketball': len(self._models_cache['ncaaw_basketball'])
            },
            'team_stats': {
                'ncaam_basketball': self._team_stats_cache['ncaam_basketball'] is not None,
                'ncaaw_basketball': self._team_stats_cache['ncaaw_basketball'] is not None
            },
            'top25': {
                'ncaam_basketball': self._top25_cache['ncaam_basketball'] is not None,
                'ncaaw_basketball': self._top25_cache['ncaaw_basketball'] is not None
            }
        }


# Convenience function to get the singleton instance
def get_blob_service() -> BlobStorageService:
    """Get the singleton BlobStorageService instance."""
    return BlobStorageService()
