"""
WebhookReceiver 모듈 간단 단위 테스트

실제 서비스 구조에 맞춰 핵심 기능만 테스트합니다.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

from modules.webhook_receiver.service import WebhookService, PlatformDetector


class TestPlatformDetector:
    """PlatformDetector 테스트 클래스"""

    def test_detect_github_platform(self):
        """GitHub 플랫폼 감지 테스트"""
        headers = {"X-GitHub-Event": "push"}
        platform = PlatformDetector.detect_platform(headers)
        assert platform == "github"

    def test_detect_gitlab_platform(self):
        """GitLab 플랫폼 감지 테스트"""
        headers = {"X-GitLab-Event": "push"}
        platform = PlatformDetector.detect_platform(headers)
        assert platform == "gitlab"

    def test_detect_unknown_platform(self):
        """알 수 없는 플랫폼 감지 테스트"""
        headers = {"Content-Type": "application/json"}
        platform = PlatformDetector.detect_platform(headers)
        assert platform == "unknown"

    def test_case_insensitive_detection(self):
        """대소문자 구분 없는 플랫폼 감지 테스트"""
        headers = {"x-github-event": "push"}  # 소문자
        platform = PlatformDetector.detect_platform(headers)
        assert platform == "github"


class TestWebhookService:
    """WebhookService 간단 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.service = WebhookService()

    def test_service_initialization(self):
        """WebhookService 객체 초기화 테스트"""
        assert self.service is not None
        assert hasattr(self.service, 'process_webhook')
        assert hasattr(self.service, 'platform_detector')
        assert hasattr(self.service, 'git_parser')

    @patch("shared.config.celery_app.celery_app.send_task")
    async def test_process_github_push_webhook_success(self, mock_send_task):
        """GitHub push 웹훅 처리 성공 테스트"""
        mock_send_task.return_value = AsyncMock()

        headers = {"X-GitHub-Event": "push"}
        payload = self._create_github_push_payload()
        body = json.dumps(payload).encode()

        result = await self.service.process_webhook(headers, body, "push")

        assert result.repository == "test/repo"
        assert len(result.commits) == 1
        mock_send_task.assert_called_once()

    async def test_process_unsupported_platform(self):
        """지원하지 않는 플랫폼 처리 테스트"""
        headers = {"X-Unknown-Event": "push"}
        payload = {"test": "data"}
        body = json.dumps(payload).encode()

        with pytest.raises(Exception):  # HTTPException 예상
            await self.service.process_webhook(headers, body, "push")

    async def test_process_unsupported_event_type(self):
        """지원하지 않는 이벤트 타입 처리 테스트"""
        headers = {"X-GitHub-Event": "pull_request"}
        payload = {"action": "opened"}
        body = json.dumps(payload).encode()

        with pytest.raises(Exception):  # HTTPException 예상
            await self.service.process_webhook(headers, body, "pull_request")

    async def test_process_malformed_json(self):
        """잘못된 JSON 처리 테스트"""
        headers = {"X-GitHub-Event": "push"}
        body = b"invalid json data"

        with pytest.raises(Exception):  # HTTPException 예상
            await self.service.process_webhook(headers, body, "push")

    def _create_github_push_payload(self) -> Dict[str, Any]:
        """GitHub push 웹훅 더미 페이로드 생성"""
        return {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "test/repo",
                "name": "repo",
                "owner": {"login": "test"}
            },
            "pusher": {"name": "test-user"},
            "commits": [
                {
                    "id": "test-commit-sha-123",
                    "message": "Test commit message",
                    "timestamp": "2024-01-20T10:30:00Z",
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com"
                    }
                }
            ]
        }


class TestWebhookServiceIntegration:
    """WebhookService 통합 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.service = WebhookService()

    @patch("shared.config.celery_app.celery_app.send_task")
    async def test_full_webhook_processing_flow(self, mock_send_task):
        """전체 웹훅 처리 플로우 테스트"""
        mock_send_task.return_value = AsyncMock()

        # 1. 복잡한 더미 페이로드 생성
        headers = {"X-GitHub-Event": "push"}
        payload = {
            "ref": "refs/heads/feature/new-feature",
            "repository": {
                "full_name": "company/advanced-project",
                "name": "advanced-project",
                "owner": {"login": "company"}
            },
            "pusher": {"name": "senior-dev"},
            "commits": [
                {
                    "id": "complex-commit-abc123",
                    "message": "Implement advanced feature with tests",
                    "timestamp": "2024-01-20T15:30:00Z",
                    "author": {
                        "name": "Senior Developer",
                        "email": "senior@company.com"
                    }
                },
                {
                    "id": "complex-commit-def456",
                    "message": "Fix bug in previous implementation",
                    "timestamp": "2024-01-20T15:45:00Z",
                    "author": {
                        "name": "Senior Developer",
                        "email": "senior@company.com"
                    }
                }
            ]
        }

        body = json.dumps(payload).encode()

        # 2. 웹훅 처리
        result = await self.service.process_webhook(headers, body, "push")

        # 3. 결과 검증
        assert result.repository == "company/advanced-project"
        assert result.ref == "refs/heads/feature/new-feature"
        assert result.pusher == "senior-dev"
        assert len(result.commits) == 2

        # 4. 백그라운드 태스크 호출 확인
        mock_send_task.assert_called_once_with(
            "webhook_receiver.process_webhook_async",
            args=[payload, headers]
        )

        print("✅ WebhookService 전체 플로우 테스트 통과")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
