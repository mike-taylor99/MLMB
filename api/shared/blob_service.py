"""
Singleton service for Azure Blob Storage interactions.
Provides centralized caching and access for all endpoints.
"""
import gzip
import io
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, List, Optional

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
import sklearn.svm  # noqa: F401 — pre-import for parallel deserialization
import xgboost  # noqa: F401 — pre-import for parallel deserialization
import lightgbm  # noqa: F401 — pre-import for parallel deserialization

# Model name mapping (used for preloading)
MODEL_NAME_MAP = {
    "logistic_regression": "logistic_regression_model",
    "knn": "knn_model",
    "random_forest": "random_forest",
    "gradient_boosting": "gradient_boosting",
    "mlp": "multilayer_perceptron",
    "svm": "support_vector_machine_model",
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "ensemble": "ensemble",
}


class BlobStorageService:
    """
    Singleton service for interacting with Azure Blob Storage.

    Provides:
    - Shared BlobServiceClient connection
    - Centralized caching for models, team stats, and top25 data
    - Thread-safe loading operations
    - Parallel model loading for cold starts
    """

    _instance: Optional["BlobStorageService"] = None
    _lock = Lock()

    def __new__(cls) -> "BlobStorageService":
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
            "ncaam_basketball": {},
            "ncaaw_basketball": {},
        }
        self._team_stats_cache: Dict[str, Optional[Dict]] = {
            "ncaam_basketball": None,
            "ncaaw_basketball": None,
        }
        self._top25_cache: Dict[str, Optional[Dict]] = {
            "ncaam_basketball": None,
            "ncaaw_basketball": None,
        }
        self._teams_cache: Optional[tuple] = None  # (teams_list, last_modified)
        self._team_stats_updated: Dict[str, Optional[str]] = {
            "ncaam_basketball": None,
            "ncaaw_basketball": None,
        }

        # Manifest and schema caches
        self._models_manifest_cache: Optional[Dict] = None
        self._feature_schema_cache: Optional[Dict] = None
        self._manifest_lock = Lock()
        self._schema_lock = Lock()

        # Per-resource locks to prevent parallel downloads of the same resource
        self._team_stats_locks: Dict[str, Lock] = {
            "ncaam_basketball": Lock(),
            "ncaaw_basketball": Lock(),
        }
        self._top25_locks: Dict[str, Lock] = {
            "ncaam_basketball": Lock(),
            "ncaaw_basketball": Lock(),
        }
        self._teams_lock = Lock()
        self._model_locks: Dict[str, Lock] = {}  # Dynamic per-model locks
        self._model_locks_lock = Lock()  # Lock for creating model locks

        # Container names
        self.MODELS_CONTAINER = "mlmb-models"
        self.API_CONTAINER = "mlmb-api"

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
        return "ncaaw_basketball" if is_womens else "ncaam_basketball"

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

            blob_name = f"{cache_key}/team-stats"
            logging.info(f"Loading team stats: {blob_name}")

            try:
                blob_client = self.client.get_blob_client(
                    container=self.API_CONTAINER, blob=blob_name
                )
                blob_data = blob_client.download_blob().readall()
                data = json.loads(blob_data.decode())
                self._team_stats_cache[cache_key] = data

                # Cache last_modified from blob properties
                try:
                    props = blob_client.get_blob_properties()
                    self._team_stats_updated[
                        cache_key
                    ] = props.last_modified.isoformat().replace("+00:00", "Z")
                except Exception:
                    pass  # Non-critical — stats still usable without timestamp

                return data
            except Exception as e:
                logging.error(f"Failed to load team stats ({blob_name}): {e}")
                raise

    def get_team_stats_updated_at(self, is_womens: bool = False) -> Optional[str]:
        """
        Return the last-modified ISO timestamp for the team-stats blob.
        Returns None if stats haven't been loaded yet or timestamp is unavailable.
        """
        cache_key = self._get_cache_key(is_womens)
        return self._team_stats_updated.get(cache_key)

    def get_matchup_stats(
        self, team1: str, team2: str, span: int, is_womens: bool = False
    ) -> Dict:
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

        return {"team1": span_stats[team1], "team2": span_stats[team2]}

    # ==================== Models Manifest ====================

    def get_models_manifest(self) -> Dict:
        """
        Load the models manifest with caching.

        The manifest is baked into the container image at build time
        (shared/models_manifest.json), so we read it from disk — no
        network round-trip needed on cold start.

        Returns:
            Dict containing manifest data
        """
        if self._models_manifest_cache is not None:
            return self._models_manifest_cache

        with self._manifest_lock:
            if self._models_manifest_cache is not None:
                return self._models_manifest_cache

            local_path = Path(__file__).parent / "models_manifest.json"
            with open(local_path, "r") as f:
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
        span_key = f"{span}span"

        try:
            return manifest[sport][span_key][model_type]["current"]
        except KeyError:
            logging.warning(
                f"Model not in manifest: {sport}/{span_key}/{model_type}, defaulting to v1"
            )
            return "v1"

    def get_model_blob_path(
        self, sport: str, span: int, model_type: str, version: Optional[str] = None
    ) -> str:
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
        span_key = f"{span}span"

        try:
            model_info = manifest[sport][span_key][model_type]
            if version is None:
                version = model_info["current"]
            return model_info["versions"][version]["blob_path"]
        except KeyError:
            # Fall back to legacy path format
            logging.warning("Model path not in manifest, using legacy format")
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
            if "_meta" not in team_stats:
                raise ValueError("Team stats missing _meta field with feature schema")

            self._feature_schema_cache = team_stats["_meta"]
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
        home_features = schema["features"]  # No prefix for home
        away_prefix = schema.get("away_prefix", "opp_")
        away_features = [f"{away_prefix}{f}" for f in schema["features"]]
        extra_features = schema.get("extra_features", ["Neutral"])

        return home_features + away_features + extra_features

    def build_feature_dataframe(
        self, home_stats: List[float], away_stats: List[float], neutral: bool
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

            blob_name = f"{cache_key}/top25"
            logging.info(f"Loading top 25: {blob_name}")

            try:
                blob_client = self.client.get_blob_client(
                    container=self.API_CONTAINER, blob=blob_name
                )
                # Get blob properties for last_modified
                properties = blob_client.get_blob_properties()
                last_modified = properties.last_modified.isoformat().replace(
                    "+00:00", "Z"
                )

                blob_data = blob_client.download_blob().readall()
                data = json.loads(blob_data.decode())

                # Cache both data and metadata
                self._top25_cache[cache_key] = (data, last_modified)
                return data, last_modified
            except Exception as e:
                logging.error(f"Failed to load top 25 ({blob_name}): {e}")
                raise

    # ==================== Teams ====================

    # Path to data/ directory (works in Docker /app/data and local /workspace/data)
    _DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

    def get_teams(self) -> tuple[list, str]:
        """
        Load teams from local CSV files with caching.
        Reads mens_teams.csv and womens_teams.csv baked into the container image,
        merges them into a unified list, and caches the result.

        Returns:
            Tuple of (teams list, last_modified ISO string)
        """
        # Fast path - already cached
        if self._teams_cache is not None:
            return self._teams_cache

        # Slow path - acquire lock to prevent parallel loads
        with self._teams_lock:
            # Double-check after acquiring lock
            if self._teams_cache is not None:
                return self._teams_cache

            logging.info("Loading teams from local CSV files")

            try:
                mens_csv = self._DATA_DIR / "mens_teams.csv"
                womens_csv = self._DATA_DIR / "womens_teams.csv"

                mens_df = pd.read_csv(mens_csv)
                womens_df = pd.read_csv(womens_csv)

                mens_keys = set(mens_df["SR key"])
                womens_keys = set(womens_df["SR key"])

                # Start with men's teams, mark programs
                merged_df = mens_df.copy()
                merged_df["has_mens_program"] = True
                merged_df["has_womens_program"] = merged_df["SR key"].isin(womens_keys)

                # Add women-only teams
                womens_only = womens_df[~womens_df["SR key"].isin(mens_keys)].copy()
                womens_only["has_mens_program"] = False
                womens_only["has_womens_program"] = True
                merged_df = pd.concat([merged_df, womens_only], ignore_index=True)

                # Transform to API format
                teams_list = []
                for _, row in merged_df.iterrows():
                    teams_list.append(
                        {
                            "key": row["SR key"] if pd.notna(row["SR key"]) else None,
                            "school": row["School"]
                            if pd.notna(row["School"])
                            else None,
                            "name": row["NCAA Name"]
                            if pd.notna(row.get("NCAA Name"))
                            else None,
                            "location": row["City, State"]
                            if pd.notna(row["City, State"])
                            else None,
                            "ncaa_key": row["NCAA key"]
                            if pd.notna(row.get("NCAA key"))
                            else None,
                            "color": row["background-color"]
                            if pd.notna(row.get("background-color"))
                            else None,
                            "has_mens_program": bool(
                                row.get("has_mens_program", False)
                            ),
                            "has_womens_program": bool(
                                row.get("has_womens_program", False)
                            ),
                        }
                    )

                # Filter out teams without a key and sort
                teams_list = sorted(
                    [t for t in teams_list if t["key"]], key=lambda x: x["key"]
                )

                # Use the latest file mtime as last_modified
                mtime = max(mens_csv.stat().st_mtime, womens_csv.stat().st_mtime)
                last_modified = (
                    datetime.fromtimestamp(mtime, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )

                self._teams_cache = (teams_list, last_modified)
                logging.info(f"Loaded {len(teams_list)} teams from CSV")
                return teams_list, last_modified
            except Exception as e:
                logging.error(f"Failed to load teams from CSV: {e}")
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

    def _resolve_blob_path(self, model_name: str, cache_key: str) -> Optional[str]:
        """
        Resolve the blob path for a model from the manifest.

        Parses model_name (e.g. '3span_logistic_regression_model') into span + model_type,
        then looks up the current version's blob_path in the manifest.

        Returns:
            The manifest blob_path string, or None if not resolvable.
        """
        try:
            parts = model_name.split("span_", 1)
            if len(parts) != 2:
                return None
            span = int(parts[0])
            blob_suffix = parts[1]

            # Reverse lookup: blob file name -> model type key
            model_type = None
            for mt, bn in MODEL_NAME_MAP.items():
                if bn == blob_suffix:
                    model_type = mt
                    break
            if model_type is None:
                return None

            return self.get_model_blob_path(cache_key, span, model_type)
        except Exception:
            return None

    def get_model(
        self, model_name: str, is_womens: bool = False, blob_path: str = None
    ) -> Any:
        """
        Load a single model from Blob Storage with caching.
        Thread-safe: uses per-model locks to prevent parallel downloads of the same model.

        Blob path resolution order:
        1. Explicit blob_path parameter (if provided by caller)
        2. Auto-resolve from manifest using model_name parsing
        3. Legacy flat path fallback: {sport}/{model_name}.pkl

        Args:
            model_name: Name of the model (without .pkl extension)
            is_womens: Whether to load women's model
            blob_path: Optional manifest-resolved blob path (e.g.
                'ncaam_basketball/2026-03-02/3span_logistic_regression_model.pkl').
                When provided, overrides manifest and flat path resolution.

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

            # Resolve blob path: explicit > manifest > flat legacy
            if blob_path is None:
                blob_path = self._resolve_blob_path(model_name, cache_key)

            if blob_path:
                # Versioned path (from manifest or caller)
                blob_path_gz = blob_path.replace(".pkl", ".pkl.gz")
                blob_path_raw = blob_path
            else:
                # Legacy flat path: {sport}/{model_name}.pkl
                blob_path_gz = f"{cache_key}/{model_name}.pkl.gz"
                blob_path_raw = f"{cache_key}/{model_name}.pkl"

            try:
                try:
                    blob_client = self.client.get_blob_client(
                        container=self.MODELS_CONTAINER, blob=blob_path_gz
                    )
                    compressed = blob_client.download_blob().readall()
                    model_bytes = gzip.decompress(compressed)
                except Exception:
                    # Fall back to uncompressed
                    blob_client = self.client.get_blob_client(
                        container=self.MODELS_CONTAINER, blob=blob_path_raw
                    )
                    model_bytes = blob_client.download_blob().readall()

                model = joblib.load(io.BytesIO(model_bytes))
                self._models_cache[cache_key][model_name] = model
                logging.info(f"Loaded model: {model_name}")
                return model
            except Exception as e:
                logging.error(f"Failed to load model {model_name}: {e}")
                raise

    def get_models_parallel(
        self, model_names: List[str], is_womens: bool = False
    ) -> Dict[str, Any]:
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
        models_to_load = [
            name for name in model_names if name not in self._models_cache[cache_key]
        ]

        if models_to_load:
            logging.info(
                f"Cold start: loading {len(models_to_load)} models in parallel"
            )

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
                raise RuntimeError(
                    f"Failed to load {len(errors)} model(s): {failed_names}"
                )

        # Verify all requested models are now in cache
        missing = [
            name for name in model_names if name not in self._models_cache[cache_key]
        ]
        if missing:
            raise RuntimeError(f"Models missing from cache after loading: {missing}")

        # Return models in sorted order for deterministic iteration
        return {
            name: self._models_cache[cache_key][name] for name in sorted(model_names)
        }

    # ==================== Eager Loading ====================

    def start_preload(self) -> None:
        """
        Kick off background preloading of all blob data.

        Returns immediately after loading local data (manifest, teams CSV).
        Blob downloads (team stats, top25, models) run in background threads.
        Endpoints that need data still loading will block on their per-resource
        lock until that specific resource is ready — not all resources.
        """
        # ── Local data (instant, no network) ──
        self.get_models_manifest()
        self.get_teams()
        logging.info("Local data ready (manifest + teams CSV) — accepting requests")

        # ── Blob data in background threads ──
        start = time.time()

        def _task(label: str, fn, *args):
            t0 = time.time()
            try:
                fn(*args)
                logging.info(f"Preloaded {label} in {time.time() - t0:.2f}s")
            except Exception as e:
                logging.error(f"Preload failed for {label}: {e}")

        pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="preload")

        futures = []

        # API data from blob storage
        futures.append(
            pool.submit(_task, "team_stats[men]", self.get_team_stats, False)
        )
        futures.append(
            pool.submit(_task, "team_stats[women]", self.get_team_stats, True)
        )
        futures.append(pool.submit(_task, "top25[men]", self.get_top25, False))
        futures.append(pool.submit(_task, "top25[women]", self.get_top25, True))
        futures.append(
            pool.submit(_task, "feature_schema", self.get_feature_schema, False)
        )

        # Ensemble models (2 sports × 3 spans = 6 downloads)
        ensemble_blob = MODEL_NAME_MAP["ensemble"]
        for span in [3, 5, 7]:
            name = f"{span}span_{ensemble_blob}"
            futures.append(
                pool.submit(_task, f"model[men/{name}]", self.get_model, name, False)
            )
            futures.append(
                pool.submit(_task, f"model[women/{name}]", self.get_model, name, True)
            )

        pool.shutdown(wait=False)

        # Track overall completion in a daemon thread
        def _on_complete():
            for f in futures:
                try:
                    f.result()
                except Exception:
                    pass
            logging.info(
                f"Background preload complete in {time.time() - start:.2f}s "
                f"— cache: {self.get_cache_stats()}"
            )

        Thread(target=_on_complete, daemon=True, name="preload-done").start()

    # ==================== Cache Management ====================

    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cached data.

        Args:
            cache_type: 'models', 'stats', 'top25', 'teams', 'manifest', 'schema', or None for all
        """
        if cache_type is None or cache_type == "models":
            self._models_cache = {"ncaam_basketball": {}, "ncaaw_basketball": {}}
            logging.info("Cleared models cache")

        if cache_type is None or cache_type == "stats":
            self._team_stats_cache = {
                "ncaam_basketball": None,
                "ncaaw_basketball": None,
            }
            logging.info("Cleared team stats cache")

        if cache_type is None or cache_type == "top25":
            self._top25_cache = {"ncaam_basketball": None, "ncaaw_basketball": None}
            logging.info("Cleared top 25 cache")

        if cache_type is None or cache_type == "teams":
            self._teams_cache = None
            logging.info("Cleared teams cache")

        if cache_type is None or cache_type == "manifest":
            self._models_manifest_cache = None
            logging.info("Cleared models manifest cache")

        if cache_type is None or cache_type == "schema":
            self._feature_schema_cache = None
            logging.info("Cleared feature schema cache")

    def get_cache_stats(self) -> Dict:
        """Get current cache statistics."""
        return {
            "models": {
                "ncaam_basketball": len(self._models_cache["ncaam_basketball"]),
                "ncaaw_basketball": len(self._models_cache["ncaaw_basketball"]),
            },
            "team_stats": {
                "ncaam_basketball": self._team_stats_cache["ncaam_basketball"]
                is not None,
                "ncaaw_basketball": self._team_stats_cache["ncaaw_basketball"]
                is not None,
            },
            "top25": {
                "ncaam_basketball": self._top25_cache["ncaam_basketball"] is not None,
                "ncaaw_basketball": self._top25_cache["ncaaw_basketball"] is not None,
            },
            "teams": self._teams_cache is not None,
        }


# Convenience function to get the singleton instance
def get_blob_service() -> BlobStorageService:
    """Get the singleton BlobStorageService instance."""
    return BlobStorageService()
