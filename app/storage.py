"""Data storage utilities for webhook events."""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.github import ValidatedEvent


async def save_event(session: AsyncSession, validated: ValidatedEvent, payload: Dict[str, Any]) -> None:
    """Persist validated event and raw payload to the database."""
    event = Event(
        repository=validated.repository,
        ref=validated.ref,
        pusher=validated.pusher,
        commit_count=len(validated.commits),
        payload=payload,
    )
    session.add(event) 