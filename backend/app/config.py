"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEVELOPMENT_JWT_SECRET = "development-only-change-me-before-production"


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
    jwt_secret: SecretStr = SecretStr(DEVELOPMENT_JWT_SECRET)
    jwt_expire_minutes: int = Field(default=60, gt=0, le=1440)
    frontend_url: str = "http://localhost:3000"
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=300)

    @property
    def cors_origins(self) -> list[str]:
        """Return the configured browser origin without a trailing slash."""

        return [self.frontend_url.rstrip("/")]

    @property
    def secure_cookies(self) -> bool:
        """Require HTTPS-only authentication cookies outside local development."""

        return self.app_env.casefold() not in {"development", "test"}

    @model_validator(mode="after")
    def validate_production_jwt_secret(self) -> "Settings":
        """Refuse to start a deployed environment with a weak default secret."""

        secret = self.jwt_secret.get_secret_value()
        if self.secure_cookies and (
            secret == DEVELOPMENT_JWT_SECRET or len(secret) < 32
        ):
            raise ValueError(
                "JWT_SECRET must contain at least 32 characters outside development"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
