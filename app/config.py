from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    github_webhook_secret: str = Field("mydevsecret", env="GITHUB_WEBHOOK_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:  # pragma: no cover
    """Cached settings instance."""
    return Settings() 