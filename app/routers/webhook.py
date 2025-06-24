from __future__ import annotations

import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.models.github import CommitInfo, ValidatedEvent

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

    if x_github_event != "push":
        # Unsupported event for now
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Event '{x_github_event}' ignored (only push handled)",
        )

    payload: Dict[str, Any] = json.loads(body.decode())

    # Minimal JSON schema validation
    required_paths = [
        ("repository", "full_name"),
        ("pusher", "name"),
        ("commits",),
    ]
    for path in required_paths:
        ptr = payload
        for key in path:
            if key not in ptr:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing field: {'.'.join(path)}",
                )
            ptr = ptr[key]

    # Build CommitInfo list
    commits: List[CommitInfo] = []
    for commit in payload["commits"]:
        commits.append(
            CommitInfo(
                id=commit["id"],
                message=commit.get("message", ""),
                url=commit.get("url", ""),
                added=commit.get("added", []),
                removed=commit.get("removed", []),
                modified=commit.get("modified", []),
            )
        )

    validated = ValidatedEvent(
        repository=payload["repository"]["full_name"],
        ref=payload.get("ref", ""),
        pusher=payload["pusher"].get("name", ""),
        commits=commits,
        timestamp=datetime.now(tz=timezone.utc),
    )

    return JSONResponse(content=validated.dict()) 