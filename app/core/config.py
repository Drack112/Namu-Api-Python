import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_app_env = os.environ.get("APP_ENV", "development")


class Settings(BaseSettings):
    # Environment
    app_env: Literal["development", "production"] = "development"
    log_level: str = "DEBUG"

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "namu"
    db_password: str = "namu123"
    db_name: str = "namu_ai"

    # LLM
    llm_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_provider: Literal["anthropic", "ollama"] = "anthropic"

    # Ollama (local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Webhook (optional — leave empty to disable)
    webhook_url: str = ""

    # Redis cache
    redis_url: str = "redis://localhost:6379"

    allow_origins: str = "http://localhost:3000"
    allow_headers: str = "Content-Type,Authorization"

    model_config = SettingsConfigDict(
        env_file=".env" if _app_env != "production" else None,
        env_file_encoding="utf-8",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def parsed_allow_origins(self) -> list[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]

    @property
    def parsed_allow_headers(self) -> list[str]:
        return [h.strip() for h in self.allow_headers.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
