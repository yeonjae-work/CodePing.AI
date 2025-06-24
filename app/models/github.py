from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Normalized commit information extracted from a GitHub push event."""

    id: str
    message: str
    url: str
    added: List[str]
    removed: List[str]
    modified: List[str]


class ValidatedEvent(BaseModel):
    """Schema returned by the WebhookReceiver after validating a push event."""

    repository: str  # owner/repo
    ref: str  # branch or tag ref
    pusher: str
    commits: List[CommitInfo]
    timestamp: datetime

    class Config:
        orm_mode = True 