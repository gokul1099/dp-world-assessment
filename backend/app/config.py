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
    groq_api_key: SecretStr | None = None
    groq_vision_model: str = "qwen/qwen3.8-27b"
    # Text-only Q&A model; separate from the vision model so it has its own rate limits.
    groq_chat_model: str = "openai/gpt-oss-120b"

    max_upload_mb: int = Field(default=10, gt=0, le=30)  # Cloud Run caps HTTP/1 bodies at 32 MB
    max_pdf_pages: int = Field(default=10, gt=0)  # licences are 1–2 pages
    max_stored_documents: int = Field(default=50, gt=0)  # in-memory store; oldest evicted

    # Milvus Lite (embedded, file-based) + local embedding model cache live here.
    data_dir: str = "data"
    embedding_model: str = "BAAI/bge-small-en-v1.5"  # 384-dim, runs on CPU via fastembed

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
