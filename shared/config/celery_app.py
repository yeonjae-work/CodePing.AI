"""Celery configuration and app instance."""

from __future__ import annotations

import os
import logging
from typing import Any

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
        from celery import Celery
        
        broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        
        app = Celery(
            "codeping",
            broker=broker_url,
            backend=broker_url,
            include=["modules.webhook_receiver.tasks"]
        )
        
        # Configuration
        app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_routes={
                "webhook_receiver.*": {"queue": "webhook_queue"},
            },
        )
        
        logger.info("Celery app initialized with broker: %s", broker_url)
        return app
        
    except ImportError:
        logger.warning("Celery not available, using mock")
        return MockCelery()
    except Exception as exc:
        logger.warning("Failed to initialize Celery, using mock: %s", exc)
        return MockCelery()


# Create the global Celery app instance
celery_app = create_celery_app() 