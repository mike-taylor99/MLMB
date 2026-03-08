"""
Cosmos DB service for storing and retrieving user brackets.
"""
import hashlib
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.config import get_settings

logger = logging.getLogger(__name__)


class BracketStore:
    """
    Service for persisting brackets to Cosmos DB.

    Container: brackets (partition key: /user_id)
    Each document represents a single user bracket for a tournament.
    """

    _instance: Optional["BracketStore"] = None
    _lock = Lock()

    DATABASE_NAME = "mlmb"
    CONTAINER_NAME = "brackets"

    def __new__(cls) -> "BracketStore":
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
        logger.info("BracketStore initialized")

    def _ensure_client(self):
        """Ensure the Cosmos client and database are initialized."""
        if self._client is None:
            conn_str = get_settings().cosmos_connection_string
            if not conn_str:
                raise ValueError("COSMOS_CONNECTION_STRING not configured")
            self._client = CosmosClient.from_connection_string(conn_str)
            self._database = self._client.create_database_if_not_exists(
                id=self.DATABASE_NAME
            )

    @property
    def container(self):
        """Get or create the brackets container."""
        if self._container is None:
            self._ensure_client()
            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [{"path": "/*"}],
                "excludedPaths": [
                    {"path": "/picks/*"},
                    {"path": '/"_etag"/?'},
                ],
                "compositeIndexes": [
                    [
                        {"path": "/tournament_id", "order": "ascending"},
                        {"path": "/updated_at", "order": "descending"},
                    ]
                ],
            }
            self._container = self._database.create_container_if_not_exists(
                id=self.CONTAINER_NAME,
                partition_key=PartitionKey(path="/user_id"),
                indexing_policy=indexing_policy,
            )
        return self._container

    # ==================== CRUD ====================

    def create_bracket(
        self,
        user_id: str,
        tournament_id: str,
        name: str,
        picks: Optional[Dict[str, str]] = None,
    ) -> dict:
        """Create a new bracket."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        raw = f"{user_id}:{now}"
        hash_hex = hashlib.sha256(raw.encode()).hexdigest()[:32]
        bracket = {
            "id": f"brk_{hash_hex}",
            "user_id": user_id,
            "tournament_id": tournament_id,
            "name": name,
            "picks": picks or {},
            "created_at": now,
            "updated_at": now,
        }
        self.container.create_item(body=bracket)
        logger.info(f"Created bracket {bracket['id']} for user {user_id}")
        return bracket

    def get_bracket(self, bracket_id: str, user_id: str) -> Optional[dict]:
        """Get a bracket by ID. Returns None if not found."""
        try:
            return self.container.read_item(item=bracket_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return None

    def get_bracket_public(self, bracket_id: str) -> Optional[dict]:
        """Get a bracket by ID without knowing the owner (cross-partition query)."""
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": bracket_id}]
        items = list(
            self.container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else None

    def list_brackets(
        self,
        user_id: str,
        tournament_id: Optional[str] = None,
    ) -> List[dict]:
        """List all brackets for a user, optionally filtered by tournament."""
        if tournament_id:
            query = (
                "SELECT * FROM c WHERE c.user_id = @user_id "
                "AND c.tournament_id = @tournament_id "
                "ORDER BY c.updated_at DESC"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@tournament_id", "value": tournament_id},
            ]
        else:
            query = (
                "SELECT * FROM c WHERE c.user_id = @user_id "
                "ORDER BY c.updated_at DESC"
            )
            params = [{"name": "@user_id", "value": user_id}]

        items = list(
            self.container.query_items(
                query=query,
                parameters=params,
                partition_key=user_id,
            )
        )
        return items

    def update_bracket(
        self,
        bracket_id: str,
        user_id: str,
        name: Optional[str] = None,
        picks: Optional[Dict[str, str]] = None,
    ) -> Optional[dict]:
        """Update a bracket's name and/or picks. Returns None if not found."""
        existing = self.get_bracket(bracket_id, user_id)
        if existing is None:
            return None

        if name is not None:
            existing["name"] = name
        if picks is not None:
            existing["picks"] = picks

        existing["updated_at"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        self.container.replace_item(item=bracket_id, body=existing)
        logger.info(f"Updated bracket {bracket_id}")
        return existing

    def delete_bracket(self, bracket_id: str, user_id: str) -> bool:
        """Delete a bracket. Returns True if deleted, False if not found."""
        try:
            self.container.delete_item(item=bracket_id, partition_key=user_id)
            logger.info(f"Deleted bracket {bracket_id}")
            return True
        except CosmosResourceNotFoundError:
            return False

    def count_user_brackets(self, user_id: str, tournament_id: str) -> int:
        """Count how many brackets a user has for a tournament."""
        query = (
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.user_id = @user_id AND c.tournament_id = @tournament_id"
        )
        params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@tournament_id", "value": tournament_id},
        ]
        results = list(
            self.container.query_items(
                query=query,
                parameters=params,
                partition_key=user_id,
            )
        )
        return results[0] if results else 0


def get_bracket_store() -> BracketStore:
    """Get the singleton BracketStore instance."""
    return BracketStore()
