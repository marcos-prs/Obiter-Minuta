from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change_me_in_production"
    api_version: str = "v1"

    google_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    job_ttl_minutes: int = 15
    result_ttl_hours: int = 2

    max_pdf_size_mb: int = 50
    max_pages: int = 150

    sentry_dsn: str = ""
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
