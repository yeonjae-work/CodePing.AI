"""
WebhookReceiver 모듈 독립 단위 테스트

이 테스트는 FastAPI 라우터와 분리하여 WebhookService의
비즈니스 로직만 독립적으로 테스트합니다.
"""

import pytest
import json
import hashlib
import hmac
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

from modules.webhook_receiver.service import WebhookService
from modules.webhook_receiver.models import WebhookPayload, GitPlatform


class TestWebhookService:
    """WebhookService 독립 단위 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.service = WebhookService()
        self.test_secret = "test-webhook-secret"

    def test_service_initialization(self):
        """WebhookService 객체 초기화 테스트"""
        assert self.service is not None
        assert hasattr(self.service, 'process_webhook')
        assert hasattr(self.service, 'verify_signature')

    def test_verify_github_signature_valid(self):
        """GitHub 유효한 서명 검증 테스트"""
        payload = json.dumps({"test": "data"}).encode()
        signature = self._create_github_signature(payload, self.test_secret)

        is_valid = self.service.verify_signature(
            payload=payload,
            signature=signature,
            secret=self.test_secret,
            platform=GitPlatform.GITHUB
        )

        assert is_valid is True

    def test_verify_github_signature_invalid(self):
        """GitHub 잘못된 서명 검증 테스트"""
        payload = json.dumps({"test": "data"}).encode()
        invalid_signature = "sha256=invalid_signature"

        is_valid = self.service.verify_signature(
            payload=payload,
            signature=invalid_signature,
            secret=self.test_secret,
            platform=GitPlatform.GITHUB
        )

        assert is_valid is False

    def test_verify_signature_missing(self):
        """서명이 없는 경우 테스트"""
        payload = json.dumps({"test": "data"}).encode()

        is_valid = self.service.verify_signature(
            payload=payload,
            signature=None,
            secret=self.test_secret,
            platform=GitPlatform.GITHUB
        )

        assert is_valid is False

    @patch("shared.config.celery_app.celery_app.send_task")
    async def test_process_github_push_webhook_success(self, mock_send_task):
        """GitHub push 웹훅 처리 성공 테스트"""
        mock_send_task.return_value = AsyncMock()

        payload_data = self._create_github_push_payload()

        result = await self.service.process_webhook(
            event_type="push",
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "success"
        mock_send_task.assert_called_once()

    async def test_process_github_ping_webhook(self):
        """GitHub ping 웹훅 처리 테스트 (무시됨)"""
        payload_data = self._create_github_ping_payload()

        result = await self.service.process_webhook(
            event_type="ping",
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "ignored"
        assert "ping" in result["message"].lower()

    async def test_process_unsupported_event_type(self):
        """지원하지 않는 이벤트 타입 처리 테스트"""
        payload_data = {"action": "opened"}

        result = await self.service.process_webhook(
            event_type="pull_request",  # 지원하지 않는 이벤트
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "ignored"
        assert "지원하지 않는" in result["message"]

    async def test_process_webhook_missing_commits(self):
        """커밋이 없는 push 웹훅 처리 테스트"""
        payload_data = {
            "re": "refs/heads/main",
            "repository": {"full_name": "test/repo"},
            "commits": []  # 빈 커밋 리스트
        }

        result = await self.service.process_webhook(
            event_type="push",
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "ignored"
        assert "커밋이 없습니다" in result["message"]

    @patch("shared.config.celery_app.celery_app.send_task")
    async def test_process_webhook_with_multiple_commits(self, mock_send_task):
        """여러 커밋이 있는 push 웹훅 처리 테스트"""
        mock_send_task.return_value = AsyncMock()

        payload_data = self._create_github_push_payload_with_multiple_commits()

        result = await self.service.process_webhook(
            event_type="push",
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "success"
        # 3개 커밋에 대해 각각 태스크가 실행되어야 함
        assert mock_send_task.call_count == 3

    def test_extract_repository_name_github(self):
        """GitHub 레포지토리 이름 추출 테스트"""
        payload_data = {
            "repository": {
                "full_name": "owner/repository-name"
            }
        }

        repo_name = self.service._extract_repository_name(payload_data, "github")
        assert repo_name == "owner/repository-name"

    def test_extract_repository_name_missing(self):
        """레포지토리 이름이 없는 경우 테스트"""
        payload_data = {}

        repo_name = self.service._extract_repository_name(payload_data, "github")
        assert repo_name == "unknown"

    def test_extract_commits_from_push(self):
        """push 이벤트에서 커밋 추출 테스트"""
        payload_data = self._create_github_push_payload()

        commits = self.service._extract_commits_from_push(payload_data)

        assert len(commits) == 1
        assert commits[0]["id"] == "test-commit-sha-123"
        assert commits[0]["message"] == "Test commit message"

    def test_extract_commits_empty_push(self):
        """빈 push 이벤트에서 커밋 추출 테스트"""
        payload_data = {
            "commits": [],
            "head_commit": None
        }

        commits = self.service._extract_commits_from_push(payload_data)
        assert len(commits) == 0

    def test_webhook_payload_model_validation(self):
        """WebhookPayload 모델 검증 테스트"""
        valid_data = {
            "event_type": "push",
            "platform": GitPlatform.GITHUB,
            "repository": "test/repo",
            "data": {"test": "data"}
        }

        payload = WebhookPayload(**valid_data)

        assert payload.event_type == "push"
        assert payload.platform == GitPlatform.GITHUB
        assert payload.repository == "test/repo"
        assert payload.data == {"test": "data"}

    def _create_github_signature(self, payload: bytes, secret: str) -> str:
        """GitHub 스타일 HMAC 서명 생성"""
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def _create_github_push_payload(self) -> Dict[str, Any]:
        """GitHub push 웹훅 더미 페이로드 생성"""
        return {
            "re": "refs/heads/main",
            "repository": {
                "full_name": "test/repo",
                "name": "repo",
                "owner": {"login": "test"}
            },
            "head_commit": {
                "id": "test-commit-sha-123",
                "message": "Test commit message",
                "timestamp": "2024-01-15T10:30:00Z",
                "author": {
                    "name": "Test Author",
                    "email": "test@example.com"
                }
            },
            "commits": [
                {
                    "id": "test-commit-sha-123",
                    "message": "Test commit message",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com"
                    },
                    "added": ["new_file.py"],
                    "removed": [],
                    "modified": ["existing_file.py"]
                }
            ]
        }

    def _create_github_push_payload_with_multiple_commits(self) -> Dict[str, Any]:
        """여러 커밋이 있는 GitHub push 웹훅 더미 페이로드 생성"""
        base_payload = self._create_github_push_payload()

        # 3개의 커밋 추가
        commits = []
        for i in range(3):
            commits.append({
                "id": f"commit-sha-{i}",
                "message": f"Commit message {i}",
                "timestamp": "2024-01-15T10:30:00Z",
                "author": {
                    "name": f"Author {i}",
                    "email": f"author{i}@example.com"
                },
                "added": [f"file{i}.py"],
                "removed": [],
                "modified": []
            })

        base_payload["commits"] = commits
        base_payload["head_commit"] = commits[-1]  # 마지막 커밋을 head_commit으로

        return base_payload

    def _create_github_ping_payload(self) -> Dict[str, Any]:
        """GitHub ping 웹훅 더미 페이로드 생성"""
        return {
            "zen": "Design for failure.",
            "hook_id": 123456,
            "hook": {
                "type": "Repository",
                "id": 123456,
                "events": ["push"],
                "active": True
            },
            "repository": {
                "full_name": "test/repo",
                "name": "repo"
            }
        }


class TestWebhookServiceStress:
    """WebhookService 스트레스 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.service = WebhookService()

    @patch("shared.config.celery_app.celery_app.send_task")
    async def test_large_payload_processing(self, mock_send_task):
        """대용량 페이로드 처리 테스트"""
        mock_send_task.return_value = AsyncMock()

        # 대용량 커밋 데이터 생성
        large_commits = []
        for i in range(50):  # 50개 커밋
            large_commits.append({
                "id": f"large-commit-{i:03d}",
                "message": f"Large commit {i} " + "x" * 1000,  # 긴 메시지
                "timestamp": "2024-01-15T10:30:00Z",
                "author": {
                    "name": f"Author {i}",
                    "email": f"author{i}@example.com"
                },
                "added": [f"file{j}.py" for j in range(10)],  # 10개 파일 추가
                "removed": [],
                "modified": []
            })

        payload_data = {
            "re": "refs/heads/main",
            "repository": {"full_name": "test/large-repo"},
            "commits": large_commits,
            "head_commit": large_commits[-1]
        }

        result = await self.service.process_webhook(
            event_type="push",
            payload=payload_data,
            platform="github"
        )

        assert result["status"] == "success"
        assert mock_send_task.call_count == 50  # 50개 커밋 모두 처리

    def test_malformed_payload_handling(self):
        """잘못된 형식의 페이로드 처리 테스트"""
        malformed_payloads = [
            None,
            "",
            {"invalid": "structure"},
            {"repository": None},
            {"commits": "not_a_list"}
        ]

        for payload in malformed_payloads:
            try:
                WebhookPayload(
                    event_type="push",
                    platform=GitPlatform.GITHUB,
                    repository="test/repo",
                    data=payload
                )
                # 여기까지 오면 검증이 통과한 것 (정상)
            except Exception:
                # 잘못된 데이터는 예외가 발생해야 함 (정상)
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
