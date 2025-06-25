"""FastAPI router for webhook endpoints."""

from __future__ import annotations

import hmac
import hashlib
import json
from typing import Any, Dict
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from shared.config.settings import Settings, get_settings
from modules.git_data_parser.models import ValidatedEvent
from modules.webhook_receiver.service import WebhookService

router = APIRouter(prefix="/webhook", tags=["webhook"])

_SIGNATURE_PREFIX = "sha256="

# Module logger
logger = logging.getLogger(__name__)


async def _verify_github_signature(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
) -> bytes:
    """Verify GitHub signature and return raw body bytes if valid.

    Raises 401 if missing/invalid.
    """
    body: bytes = await request.body()

    if not x_hub_signature_256 or not x_hub_signature_256.startswith(_SIGNATURE_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    signature = x_hub_signature_256[len(_SIGNATURE_PREFIX) :]
    mac = hmac.new(settings.github_webhook_secret.encode(), msg=body, digestmod=hashlib.sha256)
    expected = mac.hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    return body


@router.post("/", response_model=ValidatedEvent, status_code=status.HTTP_200_OK)
async def handle_github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    body: bytes = Depends(_verify_github_signature),
) -> JSONResponse:
    """Handle GitHub push webhook and return a validated event structure."""
    
    webhook_service = WebhookService()
    validated_event = await webhook_service.process_webhook(
        headers=dict(request.headers),
        body=body,
        github_event=x_github_event
    )

    # Summary log
    logger.info(
        "✅ Webhook processed: repo=%s ref=%s commits=%d",
        validated_event.repository,
        validated_event.ref,
        len(validated_event.commits),
    )

    return JSONResponse(content=jsonable_encoder(validated_event)) 