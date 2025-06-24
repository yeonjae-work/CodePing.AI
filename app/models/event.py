"""ORM model for storing webhook events."""

from __future__ import annotations

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Event(Base):
    """Persisted webhook event."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository: Mapped[str] = mapped_column(String(255), index=True)
    ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pusher: Mapped[str] = mapped_column(String(100), index=True)
    commit_count: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now()) 