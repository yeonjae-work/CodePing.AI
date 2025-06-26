"""
GitDataParser 모듈 간단 단위 테스트

실제 서비스 구조에 맞춰 핵심 기능만 테스트합니다.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from modules.git_data_parser.service import GitDataParserService


class TestGitDataParserSimple:
    """GitDataParser 간단 테스트 클래스"""

    def setup_method(self):
        """각 테스트 실행 전 초기화"""
        self.parser = GitDataParserService()

    def test_parser_initialization(self):
        """GitDataParser 객체 초기화 테스트"""
        assert self.parser is not None
        assert hasattr(self.parser, 'parse_webhook_data')
        assert hasattr(self.parser, 'extract_commit_info')
        assert hasattr(self.parser, 'detect_file_type')

    def test_parse_webhook_data_basic(self):
        """기본 웹훅 데이터 파싱 테스트"""
        dummy_payload = {
            "repository": {"full_name": "test/repo"},
            "ref": "refs/heads/main",
            "pusher": {"name": "test-user"},
            "commits": [
                {
                    "id": "abc123",
                    "message": "Test commit",
                    "timestamp": "2024-01-20T10:30:00Z",
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com"
                    },
                    "added": ["new_file.py"],
                    "removed": ["old_file.py"],
                    "modified": ["existing_file.py"]
                }
            ]
        }

        result = self.parser.parse_webhook_data(dummy_payload, {})

        assert result.repository == "test/repo"
        assert result.ref == "refs/heads/main"
        assert len(result.commits) == 1
        assert len(result.file_changes) == 3  # added + removed + modified

    def test_detect_file_type(self):
        """파일 타입 감지 테스트"""
        assert self.parser.detect_file_type("main.py") == "python"
        assert self.parser.detect_file_type("app.js") == "javascript"
        assert self.parser.detect_file_type("style.css") == "css"
        assert self.parser.detect_file_type("README.md") == "markdown"
        assert self.parser.detect_file_type("unknown.xyz") == "unknown"

    def test_extract_commit_info(self):
        """커밋 정보 추출 테스트"""
        commit_data = {
            "id": "test-commit-123",
            "message": "Test commit message",
            "timestamp": "2024-01-20T10:30:00Z",
            "author": {
                "name": "Test Developer",
                "email": "dev@test.com"
            },
            "url": "https://github.com/test/repo/commit/test-commit-123"
        }

        commit_info = self.parser.extract_commit_info(commit_data)

        assert commit_info.sha == "test-commit-123"
        assert commit_info.message == "Test commit message"
        assert commit_info.author.name == "Test Developer"
        assert commit_info.author.email == "dev@test.com"

    def test_extract_file_changes_from_payload(self):
        """웹훅 페이로드에서 파일 변경사항 추출 테스트"""
        payload = {
            "commits": [
                {
                    "added": ["src/new_feature.py"],
                    "removed": ["old/deprecated.py"],
                    "modified": ["README.md", "requirements.txt"]
                },
                {
                    "added": ["tests/test_new.py"],
                    "modified": ["README.md"]  # 중복 파일
                }
            ]
        }

        file_changes = self.parser.extract_file_changes_from_payload(payload)

        # 중복 제거로 README.md는 하나만 남아야 함
        filenames = [fc.filename for fc in file_changes]
        assert "src/new_feature.py" in filenames
        assert "old/deprecated.py" in filenames
        assert "README.md" in filenames
        assert "requirements.txt" in filenames
        assert "tests/test_new.py" in filenames
        
        # README.md는 중복 제거되어 한 번만 나타나야 함
        readme_count = sum(1 for fn in filenames if fn == "README.md")
        assert readme_count == 1

    def test_calculate_diff_stats(self):
        """diff 통계 계산 테스트"""
        from modules.git_data_parser.models import FileChange
        
        file_changes = [
            FileChange(filename="file1.py", status="added", additions=10, deletions=0),
            FileChange(filename="file2.py", status="modified", additions=5, deletions=3),
            FileChange(filename="file3.py", status="removed", additions=0, deletions=8)
        ]

        diff_stats = self.parser.calculate_diff_stats(file_changes)

        assert diff_stats.files_changed == 3
        assert diff_stats.total_additions == 15  # 10 + 5 + 0
        assert diff_stats.total_deletions == 11  # 0 + 3 + 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 