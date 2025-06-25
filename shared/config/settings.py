"""Application settings and configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        description="Database connection URL"
    )
    
    # GitHub Webhook
    github_webhook_secret: str = Field(
        default="changeme",
        description="GitHub webhook signature verification secret"
    )
    
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub API token for fetching commit data"
    )
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    
    celery_always_eager: bool = Field(
        default=False,
        description="Execute Celery tasks synchronously for testing"
    )
    
    # AWS S3
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key for S3 uploads"
    )
    
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret key for S3 uploads"
    )
    
    aws_s3_bucket: Optional[str] = Field(
        default=None,
        description="S3 bucket for large diff storage"
    )
    
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket"
    )
    
    # Slack (future)
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL for notifications"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 