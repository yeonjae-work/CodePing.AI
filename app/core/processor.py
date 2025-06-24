"""Processor interfaces and built-in core processors."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Protocol

from fastapi import HTTPException, status

from app.models.github import CommitInfo, ValidatedEvent


class IProcessor(Protocol):
    """Generic interface every platform processor must implement."""

    def process(self, headers: Mapping[str, str], payload: Dict[str, Any]) -> ValidatedEvent:  # noqa: D401,E501
        """Validate/transform *payload* into a `ValidatedEvent`.

        Implementations must raise `HTTPException` (400/422 등) on invalid input.
        """


class GitHubPushProcessor:
    """Built-in processor for GitHub *push* events (core platform)."""

    REQUIRED_PATHS = [
        ("repository", "full_name"),
        ("pusher", "name"),
        ("commits",),
    ]

    def process(self, headers: Mapping[str, str], payload: Dict[str, Any]) -> ValidatedEvent:  # noqa: D401,E501
        # 1) 필수 필드 검증
        for path in self.REQUIRED_PATHS:
            ptr = payload
            for key in path:
                if key not in ptr:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing field: {'.'.join(path)}",
                    )
                ptr = ptr[key]

        # 2) Commit 리스트 파싱
        commits: List[CommitInfo] = [
            CommitInfo(
                id=commit["id"],
                message=commit.get("message", ""),
                url=commit.get("url", ""),
                added=commit.get("added", []),
                removed=commit.get("removed", []),
                modified=commit.get("modified", []),
            )
            for commit in payload["commits"]
        ]

        # 3) ValidatedEvent 생성
        return ValidatedEvent(
            repository=payload["repository"]["full_name"],
            ref=payload.get("ref", ""),
            pusher=payload["pusher"].get("name", ""),
            commits=commits,
            timestamp=datetime.now(tz=timezone.utc),
        ) 