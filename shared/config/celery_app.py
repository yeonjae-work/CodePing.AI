"""Celery application configuration."""

from __future__ import annotations

import os
import logging
from typing import Any

from celery import Celery
from celery.schedules import crontab

from .settings import get_settings

logger = logging.getLogger(__name__)


class MockCelery:
    """Mock Celery for testing when broker is not available."""
    
    def send_task(self, task_name: str, args: list[Any] = None, kwargs: dict[str, Any] = None) -> Any:
        """Mock send_task method."""
        logger.info("Mock Celery: Would send task %s with args=%s kwargs=%s", task_name, args, kwargs)
        return None


def create_celery_app():
    """Create Celery app instance or mock for testing."""
    
    # Check if we should use mock (for testing or when no broker available)
    if os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true":
        logger.info("Using mock Celery (always eager mode)")
        return MockCelery()
    
    try:
        # Get settings
        settings = get_settings()
        
        # Create Celery app
        celery_app = Celery("codeping")
        
        # Configure Celery
        celery_app.conf.update(
            broker_url=settings.celery_broker_url,
            task_always_eager=settings.celery_always_eager,
            task_eager_propagates=settings.celery_eager_propagates_exceptions,
            
            # Task discovery
            include=[
                "modules.webhook_receiver.tasks",
                "modules.notion_sync.tasks",
            ],
            
            # Timezone
            timezone="Asia/Seoul",
            enable_utc=True,
            
            # Periodic tasks
            beat_schedule={
                "sync-notion-documentation": {
                    "task": "notion_sync.sync_documentation",
                    "schedule": crontab(minute=f"*/{settings.notion_sync_interval_minutes}"),
                },
            },
            
            # Task routing
            task_routes={
                "webhook_receiver.*": {"queue": "webhook"},
                "notion_sync.*": {"queue": "notion_sync"},
            },
            
            # Result backend (optional)
            result_backend=settings.celery_broker_url,
            result_expires=3600,  # 1 hour
        )
        
        logger.info("Celery app initialized with broker: %s", settings.celery_broker_url)
        return celery_app
        
    except ImportError:
        logger.warning("Celery not available, using mock")
        return MockCelery()
    except Exception as exc:
        logger.warning("Failed to initialize Celery, using mock: %s", exc)
        return MockCelery()


# Create the global Celery app instance
celery_app = create_celery_app() 