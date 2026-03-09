"""
Service for loading and caching tournament definitions from local JSON files.

Tournament files live in data/tournaments/ and are baked into the Docker image.
Results are updated by editing the JSON and redeploying.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# data/tournaments/ — works in Docker /app/data and local /workspace/data
_TOURNAMENTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "tournaments"
)


class TournamentStore:
    """
    Singleton service for loading tournament definitions.

    Reads JSON files from disk and caches them. Since these are baked
    into the Docker image, they only change on redeploy.
    """

    _instance: Optional["TournamentStore"] = None
    _lock = Lock()

    def __new__(cls) -> "TournamentStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._cache: Dict[str, dict] = {}
        self._cache_lock = Lock()
        self._initialized = True
        logger.info("TournamentStore initialized")

    def _load_all(self) -> Dict[str, dict]:
        """Load all tournament JSON files from disk."""
        if self._cache:
            return self._cache

        with self._cache_lock:
            if self._cache:
                return self._cache

            tournaments = {}
            if not _TOURNAMENTS_DIR.exists():
                logger.warning(f"Tournaments directory not found: {_TOURNAMENTS_DIR}")
                return tournaments

            for path in sorted(_TOURNAMENTS_DIR.glob("*.json")):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    tid = data.get("id", path.stem)
                    tournaments[tid] = data
                    logger.info(f"Loaded tournament: {tid}")
                except Exception as e:
                    logger.error(f"Failed to load tournament {path.name}: {e}")

            self._cache = tournaments
            return tournaments

    def list_tournaments(self) -> List[dict]:
        """Return summary info for all available tournaments."""
        now = datetime.now(timezone.utc)
        result = []
        for tid, t in self._load_all().items():
            lock_date = datetime.fromisoformat(t["lock_date"])
            result.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "year": t["year"],
                    "sport": t["sport"],
                    "lock_date": t["lock_date"],
                    "is_locked": now >= lock_date,
                }
            )
        return result

    def get_tournament(self, tournament_id: str) -> Optional[dict]:
        """Get a full tournament definition by ID."""
        tournaments = self._load_all()
        t = tournaments.get(tournament_id)
        if t is None:
            return None

        now = datetime.now(timezone.utc)
        lock_date = datetime.fromisoformat(t["lock_date"])

        return {
            **t,
            "is_locked": now >= lock_date,
        }

    def is_locked(self, tournament_id: str) -> bool:
        """Check whether a tournament's bracket lock date has passed."""
        t = self.get_tournament(tournament_id)
        if t is None:
            return True  # treat missing tournament as locked
        return t["is_locked"]


# Convenience function
def get_tournament_store() -> TournamentStore:
    """Get the singleton TournamentStore instance."""
    return TournamentStore()
