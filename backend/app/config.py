"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """CareerPilot runtime settings."""

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://careerpilot:careerpilot@localhost:5432/careerpilot"
    )
    jwt_secret: SecretStr = SecretStr("")
    jwt_expire_minutes: int = 60
    frontend_url: str = "http://localhost:3000"
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """Return the configured browser origin without a trailing slash."""

        return [self.frontend_url.rstrip("/")]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
