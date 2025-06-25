"""Data storage service for persisting events with diff compression."""

from __future__ import annotations

import gzip
import os
import logging
from io import BytesIO
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from modules.data_storage.models import Event
from modules.git_data_parser.models import DiffData
from shared.config.database import get_async_session
from infrastructure.aws.s3_client import S3Client

logger = logging.getLogger(__name__)

GZIP_THRESHOLD = 256 * 1024  # 256 KiB


class DataStorageService:
    """Service for storing events with diff data compression and S3 integration."""
    
    def __init__(self):
        self.s3_client = S3Client() if self._s3_configured() else None
    
    def store_event_with_diff(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        diff_data: DiffData
    ) -> None:
        """Store event with diff data using compression and S3 offloading."""
        
        import asyncio
        asyncio.run(self._store_event_async(payload, headers, diff_data))
    
    async def _store_event_async(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        diff_data: DiffData
    ) -> None:
        """Async implementation of event storage."""
        
        # Compress diff data
        diff_patch = None
        diff_url = None
        
        if diff_data.diff_content:
            compressed_diff = self._compress_bytes(diff_data.diff_content)
            
            if len(compressed_diff) <= GZIP_THRESHOLD:
                diff_patch = compressed_diff
                storage_location = "db"
            else:
                # Upload to S3 if configured
                if self.s3_client:
                    key = f"{diff_data.repository}/{diff_data.commit_sha}.patch.gz"
                    diff_url = await self.s3_client.upload_diff(key, compressed_diff)
                    storage_location = "s3"
                else:
                    # Fallback to DB even if large
                    diff_patch = compressed_diff
                    storage_location = "db_large"
                    logger.warning(
                        "Large diff stored in DB (S3 not configured): %d bytes",
                        len(compressed_diff)
                    )
        else:
            storage_location = "none"
        
        # Prepare event data
        platform = "github" if "x-github-event" in {k.lower() for k in headers} else "gitlab"
        
        event_data = {
            "platform": platform,
            "repository": diff_data.repository,
            "commit_sha": diff_data.commit_sha,
            "author_name": payload.get("pusher", {}).get("name"),
            "author_email": payload.get("pusher", {}).get("email"),
            "timestamp_utc": None,  # Could parse from payload
            "ref": payload.get("ref"),
            "pusher": payload.get("pusher", {}).get("name"),
            "commit_count": len(payload.get("commits", [])),
            "diff_patch": diff_patch,
            "diff_url": diff_url,
            "added_lines": diff_data.added_lines,
            "deleted_lines": diff_data.deleted_lines,
            "files_changed": diff_data.files_changed,
            "payload": payload,
        }
        
        # Save to database
        async with get_async_session() as session:
            await self._save_event(session, event_data)
        
        logger.info(
            "Stored event %s/%s: gzip_size=%s stored_in=%s added=%s deleted=%s files=%s",
            diff_data.repository,
            diff_data.commit_sha,
            f"{len(compressed_diff) / 1024:.1f} KB" if diff_data.diff_content else "0 KB",
            storage_location,
            diff_data.added_lines or 0,
            diff_data.deleted_lines or 0,
            diff_data.files_changed or 0,
        )
    
    async def _save_event(self, session: AsyncSession, event_data: Dict[str, Any]) -> None:
        """Save event to database with error handling."""
        
        event = Event(**event_data)
        session.add(event)
        
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    
    def _compress_bytes(self, data: bytes) -> bytes:
        """Compress bytes using gzip."""
        
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(data)
        return buf.getvalue()
    
    def _s3_configured(self) -> bool:
        """Check if S3 is properly configured."""
        
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
        return all(os.environ.get(var) for var in required_vars) 