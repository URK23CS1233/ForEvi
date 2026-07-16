"""Application settings loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ForEvi"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/forevi"

    secret_key: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    admin_email: str = "admin@forevi.in"
    admin_password: str = "ChangeMe@123"

    login_max_attempts: int = 10
    login_window_seconds: int = 300

    # optional Redis for the event bus and rate limiting; empty -> in memory
    redis_url: str = ""

    # pluggable embedding backend: "stub" runs with no downloads
    embedding_provider: str = "stub"

    # ingestion
    max_upload_mb: int = 200
    consistency_threshold: float = 0.62  # cosine distance flag for the stub layer

    log_json: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
