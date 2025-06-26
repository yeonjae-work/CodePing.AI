"""
모듈별 더미 페이로드 통합 테스트

각 모듈이 독립적으로 실제 더미 데이터를 처리할 수 있는지 
전체 체인을 통해 테스트합니다.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# 모듈 임포트
from modules.webhook_receiver.service import WebhookService
from modules.http_api_client.client import HTTPAPIClient
from modules.git_data_parser.service import GitDataParser
from modules.diff_analyzer.service import DiffAnalyzer
from modules.data_storage.service import DataStorageManager


class TestModuleChainWithDummyPayloads:
    """모듈 체인 더미 페이로드 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.webhook_service = WebhookService()
        self.http_client = HTTPAPIClient()
        self.git_parser = GitDataParser()
        self.diff_analyzer = DiffAnalyzer()
        self.storage_manager = DataStorageManager()

    def test_module_1_webhook_receiver_dummy_payload(self):
        """모듈 1: WebhookReceiver 더미 페이로드 테스트"""
        # GitHub push 웹훅 더미 데이터
        dummy_webhook_payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "test-org/test-repo",
                "name": "test-repo",
                "owner": {"login": "test-org"}
            },
            "head_commit": {
                "id": "abc123def456ghi789",
                "message": "Add new feature for testing",
                "timestamp": "2024-01-20T10:30:00Z",
                "author": {
                    "name": "Test Developer",
                    "email": "dev@test.com"
                }
            },
            "commits": [
                {
                    "id": "abc123def456ghi789",
                    "message": "Add new feature for testing",
                    "timestamp": "2024-01-20T10:30:00Z",
                    "author": {
                        "name": "Test Developer",
                        "email": "dev@test.com"
                    },
                    "added": ["src/new_feature.py", "tests/test_new_feature.py"],
                    "removed": ["old_deprecated.py"],
                    "modified": ["README.md", "requirements.txt"]
                }
            ]
        }

        # 서비스 레벨에서 테스트
        commits = self.webhook_service._extract_commits_from_push(dummy_webhook_payload)
        repo_name = self.webhook_service._extract_repository_name(dummy_webhook_payload, "github")

        assert len(commits) == 1
        assert commits[0]["id"] == "abc123def456ghi789"
        assert repo_name == "test-org/test-repo"

        print("✅ 모듈 1 (WebhookReceiver) 더미 페이로드 테스트 통과")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
