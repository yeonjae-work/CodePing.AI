"""Celery tasks for Notion documentation sync."""

from __future__ import annotations

import logging
from celery import shared_task

# Temporarily disable Notion sync tasks to fix Celery worker startup
# from .service import NotionSyncService, NotionSyncScheduler

logger = logging.getLogger(__name__)


@shared_task(name="notion_sync.sync_documentation")
def sync_notion_documentation() -> dict:
    """Periodic task to sync Notion documentation to Cursor rules."""
    
    # Temporarily disabled - needs proper service implementation
    logger.info("🚧 Notion sync task temporarily disabled")
    return {
        "status": "disabled",
        "message": "Notion sync temporarily disabled during development"
    }


@shared_task(name="notion_sync.sync_specific_page")
def sync_specific_notion_page(page_id: str, doc_type: str, title: str, url: str) -> dict:
    """Sync a specific Notion page on demand."""
    
    # Temporarily disabled - needs proper service implementation
    logger.info("🚧 Specific Notion page sync task temporarily disabled")
    return {
        "status": "disabled",
        "message": "Notion page sync temporarily disabled during development",
        "page_id": page_id
    } 