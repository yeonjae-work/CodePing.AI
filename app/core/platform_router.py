"""PlatformRouter

Detect the originating SCM platform from webhook headers and route the request
payload to the appropriate processor.  
현재는 GitHub만 지원하지만, GitLab·Bitbucket 등으로 확장이 용이하도록 설계한다.
"""

from __future__ import annotations

from typing import Mapping

from fastapi import HTTPException, status


class PlatformRouter:
    """Hybrid router that detects the SCM platform and delegates processing.

    NOTE: Only GitHub ``push`` 이벤트를 지원하며, 추후 GitLab·Bitbucket 확장을
    고려하여 인터페이스를 정의한다.
    """

    CORE_PLATFORMS = {"github"}

    def detect_platform(self, headers: Mapping[str, str]) -> str:
        """SCM 플랫폼을 헤더/UA 기반으로 판별한다."""
        if "X-GitHub-Event" in headers:
            return "github"
        if "X-Gitlab-Event" in headers:
            return "gitlab"
        if "X-Event-Key" in headers and headers["X-Event-Key"].startswith("repo:"):
            return "bitbucket"
        return "unknown"

    # ---------------------------------------------------------------------
    # 라우팅 로직
    # ---------------------------------------------------------------------
    def route(self, platform: str):  # pragma: no cover – stub for future
        """플랫폼별 프로세서로 라우팅.

        현재는 GitHub Built-in Processor 로 직행한다.
        확장 시 `ExtensionPluginManager` 와 연동될 예정.
        """
        if platform not in self.CORE_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Platform '{platform}' not supported yet.",
            )
        return "github_processor"  # placeholder 