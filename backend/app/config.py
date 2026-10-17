from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (and `.env` when running locally)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DL Intelligence API"
    environment: Literal["local", "production"] = "local"
    log_level: str = "INFO"

    # Comma-separated list, e.g. "http://localhost:3000,https://my-app.vercel.app"
    allowed_origins: str = "http://localhost:3000"

    # Injected from Secret Manager on Cloud Run; optional so /health works without it.
    llm_api_key: SecretStr | None = None

    max_upload_mb: int = Field(default=10, gt=0, le=30)  # Cloud Run caps HTTP/1 bodies at 32 MB

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
