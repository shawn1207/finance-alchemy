"""Global configuration management using pydantic-settings."""

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables / .env file."""

    # LLM
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_api_base: str = Field(default="https://api.openai.com/v1", description="OpenAI API Base URL")
    openai_model: str = Field(default="gpt-4o", description="Default LLM model")

    # Data sources
    tushare_token: str = Field(default="", description="TuShare Pro token (optional)")
    eastmoney_api_key: str = Field(default="", description="Eastmoney Smart Select Stock API Key")
    data_cache_ttl_seconds: int = Field(default=300, description="Data cache TTL in seconds")

    # Analysis defaults
    default_kline_limit: int = Field(default=200, description="Default K-line bar count")
    default_market: str = Field(default="all", description="Default market filter")

    # CrewAI
    crewai_verbose: bool = Field(default=True, description="Enable CrewAI verbose logging")
    max_iterations: int = Field(default=5, description="Max agent iterations")

    # Celery
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL for Celery broker")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **values):
        super().__init__(**values)
        from src.infrastructure.security.vault import decrypt_secret
        # Automatically decrypt sensitive fields if they look like ciphertexts ( Fernet tags start with gAAAA )
        if self.openai_api_key.startswith("gAAAA"):
            self.openai_api_key = decrypt_secret(self.openai_api_key)
        if self.eastmoney_api_key.startswith("gAAAA"):
            self.eastmoney_api_key = decrypt_secret(self.eastmoney_api_key)
        if self.tushare_token.startswith("gAAAA"):
            self.tushare_token = decrypt_secret(self.tushare_token)


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton)."""
    return Settings()


def load_yaml_config(file_name: str) -> Dict[str, Any]:
    """Load a YAML configuration file from the project config/ directory."""
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "agents" / file_name
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
