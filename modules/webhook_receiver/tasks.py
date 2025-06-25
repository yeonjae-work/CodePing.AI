"""Celery tasks for webhook async processing."""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

from modules.git_data_parser.service import GitDataParserService
from modules.data_storage.service import DataStorageService

logger = logging.getLogger(__name__)


@shared_task(name="webhook_receiver.process_webhook_async")
def process_webhook_async(payload: Dict[str, Any], headers: Dict[str, str]) -> None:
    """Background task for processing webhook data and storing diff."""
    
    try:
        # Parse and fetch diff data
        git_parser = GitDataParserService()
        diff_data = git_parser.fetch_diff_data(payload, headers)
        
        # Store in database/S3
        storage_service = DataStorageService()
        storage_service.store_event_with_diff(payload, headers, diff_data)
        
        logger.info(
            "✅ Async webhook processing completed: repo=%s, commit=%s",
            payload.get("repository", {}).get("full_name", "unknown"),
            payload.get("after", "unknown")
        )
        
    except Exception as exc:
        logger.exception("❌ Webhook async processing failed: %s", exc)
        raise 