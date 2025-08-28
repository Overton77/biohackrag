from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATHS = [BACKEND_DIR / ".env", Path(".env")]


class AppSettings(BaseSettings):
    """
    Centralized application settings using Pydantic Settings (v2).

    - Loads from environment variables and a local .env file.
    - Provides strongly-typed accessors for keys and configuration values.
    - Exposes a canonical set of HTTP headers for webpage fetching.
    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=ENV_PATHS,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- API Keys / External Services ---
    firecrawl_api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "firecrawl_api_key"),
        description="API key for Firecrawl service.",
    ) 

    groq_api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"),
        description="API key for Groq service.",
    )

    langsmith_api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "langsmith_api_key"),
        description="API key for LangSmith tracing/observability.",
    )

    google_free_api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_FREE_API_KEY", "google_free_api_key"),
        description="API key for Google (free) endpoints.",
    )

    # --- MongoDB ---
    # Accept a broad set of legacy and common env var names to avoid breaking
    # existing setups (e.g., previously used MONGO_CONNECTION, MONGODB_URI, etc.)
    mongo_db_uri: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            # Preferred
         
            "MONGO_CONNECTION",
            
            "MONGODB_URI",
          
        ),
        description="MongoDB connection string URI.",
    )
    mongo_db_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            # Preferred
            "MONGO_DB_NAME",
            "mongo_db_name",
            # Legacy/common variants
            "MONGO_DATABASE",
            "MONGO_DB",
            "MONGODB_NAME",
            "DB_NAME",
        ),
        description="MongoDB database name.",
    )

    # --- Google Cloud (GCP) ---
    # Support both concise .env keys (region/account/project) and namespaced ones.
    gcp_region: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GCP_REGION", "region"),
        description="GCP region (e.g. us-central1).",
    )
    gcp_account: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GCP_ACCOUNT", "account"),
        description="GCP account/email or service account identifier.",
    )
    gcp_project: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GCP_PROJECT", "project"),
        description="GCP project ID.",
    )

  

    fastapi_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("FASTAPI_PORT", "PORT", "fastapi_port"),
        description="Port for running the FastAPI server.",
    )

    # --- Web Fetch Headers (defaults) ---
    web_fetch_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        validation_alias=AliasChoices("WEB_FETCH_USER_AGENT", "web_fetch_user_agent"),
        description="Default User-Agent for webpage fetching.",
    )
    web_fetch_referer: str = Field(
        default="https://daveasprey.com/",
        validation_alias=AliasChoices("WEB_FETCH_REFERER", "web_fetch_referer"),
        description="Default Referer header for webpage fetching.",
    )
    web_fetch_accept_language: str = Field(
        default="en-US,en;q=0.9",
        validation_alias=AliasChoices("WEB_FETCH_ACCEPT_LANGUAGE", "web_fetch_accept_language"),
        description="Default Accept-Language header for webpage fetching.",
    )

    @property
    def web_fetch_headers(self) -> Dict[str, str]:
        """Canonical headers to use for webpage fetching/scraping."""
        return {
            "User-Agent": self.web_fetch_user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self.web_fetch_accept_language,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": self.web_fetch_referer,
        }

    def google_credentials_path_exists(self) -> bool:
        """Convenience check for the configured Google credentials path."""
        return self.google_oauth_client_credentials_path.exists()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached settings instance for application-wide use."""
    return AppSettings()


