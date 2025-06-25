"""Data storage models for webhook events."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, DateTime, LargeBinary, Integer, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict

Base = declarative_base()


class Event(Base):
    """Database model for GitHub webhook events."""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    repository = Column(String, nullable=False, index=True)
    commit_sha = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, default="push")
    payload = Column(String, nullable=False)  # JSON string
    diff_data = Column(LargeBinary, nullable=True)  # Compressed diff or None if stored in S3
    diff_s3_url = Column(String, nullable=True)  # S3 URL if diff is too large
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Prevent duplicate events
    __table_args__ = (
        UniqueConstraint('repository', 'commit_sha', name='uq_repo_commit'),
    )
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, repo={self.repository}, sha={self.commit_sha[:8]})>"


class EventCreate(BaseModel):
    """Pydantic model for creating new events."""
    
    repository: str
    commit_sha: str
    event_type: str = "push"
    payload: str
    diff_data: Optional[bytes] = None
    diff_s3_url: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class EventResponse(BaseModel):
    """Pydantic model for event API responses."""
    
    id: int
    repository: str
    commit_sha: str
    event_type: str
    payload: Dict[str, Any]
    diff_s3_url: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True) 