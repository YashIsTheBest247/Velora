"""Application configuration loaded from environment variables."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/transactions"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # LLM
    gemini_api_key: str = ""
    # 'gemini-flash-latest' always tracks the current stable Gemini Flash model
    # (the dated 1.5/2.0 ids get retired over time).
    gemini_model: str = "gemini-flash-latest"
    llm_batch_size: int = 25
    llm_max_retries: int = 3

    # CORS: comma-separated origins, or "*" for any.
    cors_origins: str = "*"

    # Pipeline tuning
    outlier_multiplier: float = 3.0

    @field_validator("database_url", "redis_url", "gemini_model", mode="before")
    @classmethod
    def _clean(cls, value, info):
        # An empty env var (e.g. GEMINI_MODEL=) must not override the default.
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return cls.model_fields[info.field_name].default
        # Managed Postgres (Render/Heroku) hands out postgres:// or postgresql://
        # URLs; SQLAlchemy needs the explicit psycopg2 driver.
        if info.field_name == "database_url" and isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg2://" + value.split("://", 1)[1]
        return value


settings = Settings()
