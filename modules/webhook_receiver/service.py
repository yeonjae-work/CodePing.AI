"""Webhook processing service and platform detection."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Mapping

from fastapi import HTTPException, status

from modules.git_data_parser.service import GitDataParserService
from modules.git_data_parser.models import ValidatedEvent
from shared.config.celery_app import celery_app

logger = logging.getLogger(__name__)


class PlatformDetector:
    """Detect SCM platform from webhook headers."""
    
    SUPPORTED_PLATFORMS = {"github", "gitlab"}
    
    @classmethod
    def detect_platform(cls, headers: Mapping[str, str]) -> str:
        """Detect SCM platform from headers (case-insensitive)."""
        # Convert headers to lowercase for case-insensitive comparison
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        if "x-github-event" in headers_lower:
            return "github"
        if "x-gitlab-event" in headers_lower:
            return "gitlab"
        if "x-event-key" in headers_lower and headers_lower["x-event-key"].startswith("repo:"):
            return "bitbucket"
        return "unknown"


class WebhookService:
    """Main webhook processing orchestrator."""
    
    def __init__(self, git_parser=None, task_queue=None):
        self.platform_detector = PlatformDetector()
        self.git_parser = git_parser or GitDataParserService()
        self.task_queue = task_queue or celery_app
    
    async def process_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        github_event: str | None = None
    ) -> ValidatedEvent:
        """Process incoming webhook and orchestrate async tasks."""
        
        # Detect platform
        platform = self.platform_detector.detect_platform(headers)
        
        if platform != "github":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Platform '{platform}' not supported yet"
            )
        
        if github_event != "push":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Event '{github_event}' ignored (only push handled)",
            )
        
        # Parse payload
        try:
            payload: Dict[str, Any] = json.loads(body.decode())
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON payload: {exc}"
            )
        
        # Generate validated event for immediate response
        validated_event = self.git_parser.parse_github_push(headers, payload)
        
        # Enqueue background processing
        self.task_queue.send_task(
            "webhook_receiver.process_webhook_async",
            args=[payload, headers],
        )
        
        return validated_event 