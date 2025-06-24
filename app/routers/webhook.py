from __future__ import annotations

import hmac
import hashlib
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.models.github import ValidatedEvent
from app.core.platform_router import PlatformRouter

router = APIRouter(tags=["webhook"])

_SIGNATURE_PREFIX = "sha256="


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


@router.post("/webhook", response_model=ValidatedEvent, status_code=status.HTTP_200_OK)
async def handle_github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    body: bytes = Depends(_verify_github_signature),
) -> JSONResponse:
    """Handle GitHub push webhook and return a validated event structure."""

    # Detect platform using dedicated router (extensible)
    platform_router = PlatformRouter()
    platform = platform_router.detect_platform(request.headers)

    if platform != "github":
        raise HTTPException(status_code=501, detail=f"Platform '{platform}' not supported yet")

    if x_github_event != "push":
        # Unsupported event for now
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Event '{x_github_event}' ignored (only push handled)",
        )

    payload: Dict[str, Any] = json.loads(body.decode())

    # Processor 처리
    processor = platform_router.route(platform)
    validated: ValidatedEvent = processor.process(request.headers, payload)

    return JSONResponse(content=validated.dict()) 