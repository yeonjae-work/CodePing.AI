"""Configuration management for Notion sync."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from .models import NotionPage, NotionSyncConfig, NotionDocumentType

logger = logging.getLogger(__name__)


class NotionSyncConfigManager:
    """Manage Notion sync configuration."""
    
    def __init__(self, config_file: str = "notion_sync_config.json"):
        self.config_file = Path(config_file)
        self.config: NotionSyncConfig = self._load_config()
    
    def _load_config(self) -> NotionSyncConfig:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return NotionSyncConfig(**data)
            except Exception as exc:
                logger.error(f"Failed to load config: {exc}")
        
        # Return default config
        return self._create_default_config()
    
    def _create_default_config(self) -> NotionSyncConfig:
        """Create default configuration."""
        return NotionSyncConfig(
            token="",  # To be set via environment variable
            pages=[],
            sync_interval_minutes=30,
            auto_update_rules=True
        )
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=2, default=str)
            logger.info(f"✅ Saved Notion sync config to {self.config_file}")
        except Exception as exc:
            logger.error(f"Failed to save config: {exc}")
    
    def add_page(
        self, 
        page_id: str, 
        title: str, 
        url: str, 
        doc_type: NotionDocumentType,
        module_name: str = None
    ) -> None:
        """Add a new page to sync configuration."""
        page = NotionPage(
            id=page_id,
            title=title,
            url=url,
            doc_type=doc_type,
            module_name=module_name,
            last_edited_time="2024-01-01T00:00:00Z"  # Will be updated
        )
        
        # Remove existing page with same ID
        self.config.pages = [p for p in self.config.pages if p.id != page_id]
        
        # Add new page
        self.config.pages.append(page)
        self.save_config()
        
        logger.info(f"✅ Added page {title} ({doc_type.value}) to sync config")
    
    def remove_page(self, page_id: str) -> None:
        """Remove a page from sync configuration."""
        original_count = len(self.config.pages)
        self.config.pages = [p for p in self.config.pages if p.id != page_id]
        
        if len(self.config.pages) < original_count:
            self.save_config()
            logger.info(f"✅ Removed page {page_id} from sync config")
        else:
            logger.warning(f"Page {page_id} not found in config")
    
    def list_pages(self) -> List[Dict[str, Any]]:
        """List all configured pages."""
        return [
            {
                "id": page.id,
                "title": page.title,
                "doc_type": page.doc_type.value,
                "module_name": page.module_name,
                "url": str(page.url)
            }
            for page in self.config.pages
        ]
    
    def get_config(self) -> NotionSyncConfig:
        """Get current configuration."""
        return self.config


# Global config manager instance
config_manager = NotionSyncConfigManager()


def setup_default_pages():
    """Setup default pages for CodePing.AI project."""
    
    # Example configuration - replace with actual Notion page IDs and URLs
    default_pages = [
        {
            "page_id": "REPLACE_WITH_ARCHITECTURE_PAGE_ID",
            "title": "CodePing.AI 아키텍처",
            "url": "https://notion.so/REPLACE_WITH_ACTUAL_URL",
            "doc_type": NotionDocumentType.ARCHITECTURE
        },
        {
            "page_id": "REPLACE_WITH_WEBHOOK_SPEC_ID", 
            "title": "WebhookReceiver 모듈 설계서",
            "url": "https://notion.so/REPLACE_WITH_ACTUAL_URL",
            "doc_type": NotionDocumentType.MODULE_SPEC,
            "module_name": "webhook_receiver"
        },
        {
            "page_id": "REPLACE_WITH_PARSER_SPEC_ID",
            "title": "GitDataParser 모듈 설계서", 
            "url": "https://notion.so/REPLACE_WITH_ACTUAL_URL",
            "doc_type": NotionDocumentType.MODULE_SPEC,
            "module_name": "git_data_parser"
        },
        {
            "page_id": "REPLACE_WITH_STORAGE_SPEC_ID",
            "title": "DataStorage 모듈 설계서",
            "url": "https://notion.so/REPLACE_WITH_ACTUAL_URL", 
            "doc_type": NotionDocumentType.MODULE_SPEC,
            "module_name": "data_storage"
        }
    ]
    
    for page_config in default_pages:
        if not page_config["page_id"].startswith("REPLACE_WITH"):
            config_manager.add_page(**page_config)
    
    logger.info("✅ Default Notion pages configuration completed") 