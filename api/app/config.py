"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure Storage
    azure_storage_connection_string: str = ""

    # Cosmos DB
    cosmos_connection_string: str = ""

    # API Settings
    max_batch_size: int = 500
    default_page_limit: int = 20
    max_page_limit: int = 100
    teams_default_limit: int = 100
    teams_max_limit: int = 500

    # Auth — server-to-server API key (used by jobs/pipelines)
    api_key: str = ""

    # Azure AI Foundry — agent-based matchup analysis
    foundry_project_endpoint: str = ""
    foundry_agent_name: str = "mlmb-matchup-analysis"

    # Set LOCAL_DEV=true to bypass auth during local development
    local_dev: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
