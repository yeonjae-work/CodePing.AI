"""
GitDataParser 모듈 단위 테스트

이 모듈은 GitHub/GitLab API 응답 데이터를 파싱하여 
DiffData 객체로 변환하는 기능을 테스트합니다.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from modules.git_data_parser.service import GitDataParserService
from modules.git_data_parser.models import ParsedWebhookData, FileChange, CommitInfo
from modules.git_data_parser.exceptions import GitDataParserError


class TestGitDataParser:
    """GitDataParser 독립 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.parser = GitDataParserService()

    def test_parser_initialization(self):
        """GitDataParser 객체 초기화 테스트"""
        assert self.parser is not None
        assert hasattr(self.parser, 'parse_webhook_data')

    def test_parse_github_commit_data_success(self):
        """GitHub API 응답 데이터 파싱 성공 테스트"""
        # 더미 GitHub 커밋 데이터
        github_data = self._create_github_commit_dummy()

        result = self.parser.parse_commit_data(github_data, "test-repo")

        assert isinstance(result, DiffData)
        assert result.repository == "test-repo"
        assert result.commit_sha == "abc123def456"
        assert result.commit_message == "Fix bug in authentication"
        assert result.author_name == "John Doe"
        assert result.author_email == "john@example.com"
        assert len(result.file_changes) == 2

    def test_parse_gitlab_commit_data_success(self):
        """GitLab API 응답 데이터 파싱 성공 테스트"""
        # 더미 GitLab 커밋 데이터
        gitlab_data = self._create_gitlab_commit_dummy()

        result = self.parser.parse_commit_data(gitlab_data, "test-repo")

        assert isinstance(result, DiffData)
        assert result.repository == "test-repo"
        assert result.commit_sha == "def456ghi789"
        assert result.commit_message == "Add new feature"
        assert result.author_name == "Jane Smith"
        assert result.author_email == "jane@example.com"

    def test_parse_commit_data_with_empty_files(self):
        """파일 변경사항이 없는 커밋 데이터 파싱 테스트"""
        empty_data = {
            "sha": "empty123",
            "commit": {
                "message": "Empty commit",
                "author": {
                    "name": "Empty Author",
                    "email": "empty@example.com",
                    "date": "2024-01-01T12:00:00Z"
                }
            },
            "files": []
        }

        result = self.parser.parse_commit_data(empty_data, "empty-repo")

        assert result.repository == "empty-repo"
        assert result.commit_sha == "empty123"
        assert len(result.file_changes) == 0

    def test_parse_commit_data_missing_required_fields(self):
        """필수 필드가 누락된 데이터 파싱 실패 테스트"""
        invalid_data = {
            "commit": {
                "message": "Invalid commit"
            }
            # sha, author 정보 등 누락
        }

        with pytest.raises(GitDataParsingError) as exc_info:
            self.parser.parse_commit_data(invalid_data, "test-repo")

        assert "필수 필드가 누락되었습니다" in str(exc_info.value)

    def test_parse_commit_data_invalid_date_format(self):
        """잘못된 날짜 형식 처리 테스트"""
        invalid_date_data = {
            "sha": "invalid123",
            "commit": {
                "message": "Invalid date commit",
                "author": {
                    "name": "Test Author",
                    "email": "test@example.com",
                    "date": "invalid-date-format"
                }
            },
            "files": []
        }

        with pytest.raises(GitDataParsingError) as exc_info:
            self.parser.parse_commit_data(invalid_date_data, "test-repo")

        assert "날짜 형식이 올바르지 않습니다" in str(exc_info.value)

    def test_extract_file_changes_github_format(self):
        """GitHub 형식의 파일 변경사항 추출 테스트"""
        github_files = [
            {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "changes": 15,
                "patch": "@@ -1,4 +1,4 @@\n-old line\n+new line"
            },
            {
                "filename": "tests/test_new.py",
                "status": "added",
                "additions": 50,
                "deletions": 0,
                "changes": 50,
                "patch": "@@ -0,0 +1,50 @@\n+new test file"
            }
        ]

        file_changes = self.parser._extract_file_changes(github_files)

        assert len(file_changes) == 2
        assert file_changes[0].filename == "src/main.py"
        assert file_changes[0].status == "modified"
        assert file_changes[0].additions == 10
        assert file_changes[0].deletions == 5
        assert file_changes[1].filename == "tests/test_new.py"
        assert file_changes[1].status == "added"

    def test_extract_file_changes_empty_list(self):
        """빈 파일 변경사항 리스트 처리 테스트"""
        file_changes = self.parser._extract_file_changes([])
        assert len(file_changes) == 0

    def test_parse_commit_info_github(self):
        """GitHub 형식 커밋 정보 파싱 테스트"""
        commit_data = {
            "commit": {
                "message": "Test commit message",
                "author": {
                    "name": "Test Author",
                    "email": "test@example.com",
                    "date": "2024-01-15T10:30:00Z"
                }
            }
        }

        commit_info = self.parser._parse_commit_info(commit_data)

        assert commit_info.message == "Test commit message"
        assert commit_info.author_name == "Test Author"
        assert commit_info.author_email == "test@example.com"
        assert isinstance(commit_info.timestamp, datetime)

    def test_large_commit_data_handling(self):
        """대용량 커밋 데이터 처리 테스트"""
        large_data = self._create_large_commit_dummy()

        result = self.parser.parse_commit_data(large_data, "large-repo")

        assert result.repository == "large-repo"
        assert len(result.file_changes) == 100  # 100개 파일 변경
        assert sum(fc.additions for fc in result.file_changes) > 1000

    def _create_github_commit_dummy(self) -> Dict[str, Any]:
        """GitHub API 응답 더미 데이터 생성"""
        return {
            "sha": "abc123def456",
            "commit": {
                "message": "Fix bug in authentication",
                "author": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "date": "2024-01-15T10:30:00Z"
                }
            },
            "files": [
                {
                    "filename": "src/auth.py",
                    "status": "modified",
                    "additions": 15,
                    "deletions": 8,
                    "changes": 23,
                    "patch": "@@ -10,7 +10,7 @@ def authenticate(token):\n-    if not token:\n+    if not token or len(token) < 10:"
                },
                {
                    "filename": "tests/test_auth.py",
                    "status": "added",
                    "additions": 25,
                    "deletions": 0,
                    "changes": 25,
                    "patch": "@@ -0,0 +1,25 @@\n+import pytest\n+def test_auth():\n+    pass"
                }
            ]
        }

    def _create_gitlab_commit_dummy(self) -> Dict[str, Any]:
        """GitLab API 응답 더미 데이터 생성"""
        return {
            "id": "def456ghi789",
            "message": "Add new feature",
            "author_name": "Jane Smith",
            "author_email": "jane@example.com",
            "authored_date": "2024-01-16T14:20:00Z",
            "stats": {
                "additions": 45,
                "deletions": 12,
                "total": 57
            },
            "diff": [
                {
                    "old_path": "src/features.py",
                    "new_path": "src/features.py",
                    "diff": "@@ -1,3 +1,8 @@\n+def new_feature():\n+    return True"
                }
            ]
        }

    def _create_large_commit_dummy(self) -> Dict[str, Any]:
        """대용량 커밋 더미 데이터 생성"""
        files = []
        for i in range(100):
            files.append({
                "filename": f"src/file_{i:03d}.py",
                "status": "modified" if i % 3 == 0 else "added",
                "additions": 10 + (i % 50),
                "deletions": i % 10,
                "changes": 10 + (i % 50) + (i % 10),
                "patch": f"@@ -1,1 +1,{10 + (i % 50)} @@\n+line {i}"
            })

        return {
            "sha": "large123commit456",
            "commit": {
                "message": "Large commit with many file changes",
                "author": {
                    "name": "Bulk Author",
                    "email": "bulk@example.com",
                    "date": "2024-01-17T09:15:00Z"
                }
            },
            "files": files
        }


class TestGitDataParserIntegration:
    """GitDataParser 통합 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.parser = GitDataParser()

    def test_parse_real_github_webhook_payload(self):
        """실제 GitHub 웹훅 페이로드와 유사한 데이터 파싱 테스트"""
        webhook_payload = {
            "head_commit": {
                "id": "webhook123commit456",
                "message": "Update README.md",
                "timestamp": "2024-01-18T16:45:00-05:00",
                "author": {
                    "name": "GitHub User",
                    "email": "user@github.com"
                },
                "added": ["docs/new_guide.md"],
                "removed": ["old_file.txt"],
                "modified": ["README.md", "src/main.py"]
            }
        }

        # 웹훅 형식을 GitHub API 형식으로 변환하여 테스트
        commit_data = self._convert_webhook_to_api_format(webhook_payload["head_commit"])
        
        result = self.parser.parse_commit_data(commit_data, "webhook-repo")

        assert result.repository == "webhook-repo"
        assert result.commit_sha == "webhook123commit456"
        assert result.commit_message == "Update README.md"

    def test_error_handling_with_corrupted_data(self):
        """손상된 데이터에 대한 에러 처리 테스트"""
        corrupted_data = {
            "sha": None,  # null 값
            "commit": "invalid_structure",  # 잘못된 구조
            "files": "not_a_list"  # 리스트가 아님
        }

        with pytest.raises(GitDataParsingError):
            self.parser.parse_commit_data(corrupted_data, "corrupted-repo")

    def _convert_webhook_to_api_format(self, webhook_commit: Dict[str, Any]) -> Dict[str, Any]:
        """웹훅 형식을 GitHub API 형식으로 변환하는 헬퍼 메서드"""
        return {
            "sha": webhook_commit["id"],
            "commit": {
                "message": webhook_commit["message"],
                "author": {
                    "name": webhook_commit["author"]["name"],
                    "email": webhook_commit["author"]["email"],
                    "date": webhook_commit["timestamp"]
                }
            },
            "files": [
                {"filename": f, "status": "added", "additions": 10, "deletions": 0, "changes": 10}
                for f in webhook_commit.get("added", [])
            ] + [
                {"filename": f, "status": "removed", "additions": 0, "deletions": 10, "changes": 10}
                for f in webhook_commit.get("removed", [])
            ] + [
                {"filename": f, "status": "modified", "additions": 5, "deletions": 3, "changes": 8}
                for f in webhook_commit.get("modified", [])
            ]
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 