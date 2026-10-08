from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str
    ingestion_interval_minutes: int = Field(default=60, ge=1)
    jobicy_enabled: bool = True
    jobicy_base_url: str = "https://jobicy.com/api/v2/remote-jobs"
    jobicy_count: int = 100
    jobicy_geo: str = ""
    jobicy_industry: str = "engineering"
    arbeitnow_enabled: bool = True
    arbeitnow_base_url: str = "https://www.arbeitnow.com/api/job-board-api"
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=2, ge=0)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def scheduler_interval_minutes(self) -> int:
        return self.ingestion_interval_minutes


@lru_cache
def get_settings() -> Settings:
    return Settings()
