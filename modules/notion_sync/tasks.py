"""Celery tasks for Notion documentation sync."""

from __future__ import annotations

import logging
from celery import shared_task

from .service import NotionSyncService, NotionSyncScheduler

logger = logging.getLogger(__name__)


@shared_task(name="notion_sync.sync_documentation")
def sync_notion_documentation() -> dict:
    """Periodic task to sync Notion documentation to Cursor rules."""
    
    try:
        # Initialize services
        sync_service = NotionSyncService()
        scheduler = NotionSyncScheduler(sync_service)
        
        # Run sync (note: this is a sync wrapper for async function)
        import asyncio
        updates = asyncio.run(sync_service.sync_all_pages())
        
        result = {
            "status": "success",
            "synced_pages": len(updates),
            "updated_rules": [update.rule_file for update in updates]
        }
        
        logger.info(f"✅ Notion sync completed: {result}")
        return result
        
    except Exception as exc:
        logger.exception("❌ Notion sync failed: %s", exc)
        return {
            "status": "error",
            "error": str(exc)
        }


@shared_task(name="notion_sync.sync_specific_page")
def sync_specific_notion_page(page_id: str, doc_type: str, title: str, url: str) -> dict:
    """Sync a specific Notion page on demand."""
    
    try:
        from .models import NotionPage, NotionDocumentType
        
        # Create page object
        page = NotionPage(
            id=page_id,
            title=title,
            url=url,
            doc_type=NotionDocumentType(doc_type),
            last_edited_time="2024-01-01T00:00:00Z"  # Will be updated by service
        )
        
        # Initialize service and sync
        sync_service = NotionSyncService()
        update = asyncio.run(sync_service.sync_page(page))
        
        if update:
            result = {
                "status": "success",
                "rule_file": update.rule_file,
                "page_id": update.notion_page_id
            }
        else:
            result = {
                "status": "no_update_needed",
                "page_id": page_id
            }
        
        logger.info(f"✅ Specific page sync completed: {result}")
        return result
        
    except Exception as exc:
        logger.exception("❌ Specific page sync failed: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "page_id": page_id
        } 