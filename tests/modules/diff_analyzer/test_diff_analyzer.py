"""
DiffAnalyzer 모듈 통합 테스트
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from modules.diff_analyzer import DiffAnalyzer, LanguageAnalyzer, CodeComplexityAnalyzer, StructuralChangeAnalyzer
from modules.diff_analyzer.models import (
    ParsedDiff, CommitMetadata, DiffAnalysisResult,
    LanguageStats, AnalyzedFile, FileType, ChangeType
)
from modules.diff_analyzer.exceptions import DiffAnalyzerError


class TestLanguageAnalyzer:
    """LanguageAnalyzer 테스트"""

    def test_detect_language_python(self):
        analyzer = LanguageAnalyzer()
        assert analyzer._detect_language("test.py") == "python"
        assert analyzer._detect_language("test_file.py") == "python"

    def test_detect_language_javascript(self):
        analyzer = LanguageAnalyzer()
        assert analyzer._detect_language("test.js") == "javascript"
        assert analyzer._detect_language("test.ts") == "typescript"
        assert analyzer._detect_language("test.jsx") == "javascript"

    def test_detect_language_unknown(self):
        analyzer = LanguageAnalyzer()
        assert analyzer._detect_language("test.xyz") == "unknown"
        assert analyzer._detect_language("") == "unknown"
        assert analyzer._detect_language(None) == "unknown"

    def test_is_supported_language(self):
        analyzer = LanguageAnalyzer()
        assert analyzer._is_supported_language("python") is True
        assert analyzer._is_supported_language("javascript") is True
        assert analyzer._is_supported_language("unknown") is False
        assert analyzer._is_supported_language("markdown") is False

    def test_determine_file_type(self):
        analyzer = LanguageAnalyzer()

        # 테스트 파일
        assert analyzer._determine_file_type("test_user.py", "python") == FileType.TEST_FILE
        assert analyzer._determine_file_type("user_test.py", "python") == FileType.TEST_FILE
        assert analyzer._determine_file_type("user.spec.js", "javascript") == FileType.TEST_FILE

        # 설정 파일
        assert analyzer._determine_file_type("config.json", "json") == FileType.CONFIG_FILE
        assert analyzer._determine_file_type("docker-compose.yml", "yaml") == FileType.CONFIG_FILE

        # 소스 코드
        assert analyzer._determine_file_type("user.py", "python") == FileType.SOURCE_CODE
        assert analyzer._determine_file_type("main.js", "javascript") == FileType.SOURCE_CODE

    def test_classify_by_language(self):
        analyzer = LanguageAnalyzer()

        # Mock 파일 변경사항
        mock_file_changes = [
            Mock(filename="user.py", additions=10, deletions=5),
            Mock(filename="main.js", additions=15, deletions=3),
            Mock(filename="README.md", additions=2, deletions=0),
            Mock(filename="config.json", additions=1, deletions=1)
        ]

        result = analyzer.classify_by_language(mock_file_changes)

        # 언어별 그룹화 확인
        assert "python" in result.language_groups
        assert "javascript" in result.language_groups
        assert "markdown" in result.language_groups
        assert "json" in result.language_groups

        # 통계 확인
        python_stats = result.language_stats["python"]
        assert python_stats.file_count == 1
        assert python_stats.lines_added == 10
        assert python_stats.lines_deleted == 5

        # 지원 파일 분류 확인
        assert len(result.supported_files) == 2  # Python, JavaScript
        assert len(result.unsupported_files) == 2  # Markdown, JSON


class TestCodeComplexityAnalyzer:
    """CodeComplexityAnalyzer 테스트"""

    def test_analyze_python_complexity(self):
        analyzer = CodeComplexityAnalyzer()

        # Mock 파일 변경사항
        mock_file = Mock()
        mock_file.filename = "test.py"
        mock_file.additions = 10
        mock_file.deletions = 2
        mock_file.status = "modified"
        mock_file.patch = """
+def simple_function():
+    return True
+
+def complex_function(x):
+    if x > 0:
+        for i in range(x):
+            if i % 2 == 0:
+                print(i)
+    return x
"""

        result = analyzer.analyze_complexity(mock_file, "python")

        assert result.analysis_success is True
        assert result.file_path == "test.py"
        assert result.language == "python"
        assert result.metrics.complexity_delta >= 0

    def test_analyze_basic_complexity(self):
        analyzer = CodeComplexityAnalyzer()

        mock_file = Mock()
        mock_file.filename = "test.unknown"
        mock_file.additions = 20
        mock_file.deletions = 5
        mock_file.patch = "some code changes"

        result = analyzer.analyze_complexity(mock_file, "unknown")

        assert result.analysis_success is True
        assert result.metrics.complexity_delta == 1.5  # (20 - 5) * 0.1


class TestStructuralChangeAnalyzer:
    """StructuralChangeAnalyzer 테스트"""

    def test_analyze_python_structure(self):
        analyzer = StructuralChangeAnalyzer()

        mock_file = Mock()
        mock_file.filename = "user.py"
        mock_file.patch = """
+class User:
+    def __init__(self, name):
+        self.name = name
+
+def get_user(user_id):
+    return User("test")
+
+import requests
+from datetime import datetime
"""

        result = analyzer.analyze_structural_changes(mock_file, "python")

        assert result.analysis_success is True
        assert "User" in result.changes.classes_added or "User" in result.changes.classes_modified
        assert "get_user" in result.changes.functions_added or "get_user" in result.changes.functions_modified
        assert len(result.changes.imports_added) > 0 or len(result.changes.imports_changed) > 0

    def test_is_test_file(self):
        analyzer = StructuralChangeAnalyzer()

        assert analyzer._is_test_file("test_user.py") is True
        assert analyzer._is_test_file("user_test.py") is True
        assert analyzer._is_test_file("tests/test_auth.py") is True
        assert analyzer._is_test_file("user.spec.js") is True
        assert analyzer._is_test_file("UserTest.java") is True

        assert analyzer._is_test_file("user.py") is False
        assert analyzer._is_test_file("main.js") is False


class TestDiffAnalyzer:
    """DiffAnalyzer 메인 클래스 테스트"""

    def test_analyze_success(self):
        analyzer = DiffAnalyzer()

        # Mock 데이터 생성
        parsed_diff = ParsedDiff(
            repository_name="test/repo",
            commit_sha="abc123",
            file_changes=[
                Mock(filename="user.py", additions=10, deletions=2, status="modified"),
                Mock(filename="test_user.py", additions=5, deletions=0, status="added")
            ],
            diff_stats=Mock()
        )

        commit_metadata = CommitMetadata(
            sha="abc123",
            message="Add user functionality",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=datetime.now(),
            repository_name="test/repo"
        )

        result = analyzer.analyze(parsed_diff, commit_metadata)

        # 결과 검증
        assert isinstance(result, DiffAnalysisResult)
        assert result.commit_sha == "abc123"
        assert result.repository_name == "test/repo"
        assert result.author_email == "test@example.com"
        assert result.total_files_changed == 2
        assert result.total_additions == 15
        assert result.total_deletions == 2
        assert len(result.analyzed_files) >= 0
        assert result.analysis_duration_seconds > 0

    def test_analyze_empty_file_changes(self):
        analyzer = DiffAnalyzer()

        parsed_diff = ParsedDiff(
            repository_name="test/repo",
            commit_sha="abc123",
            file_changes=[],
            diff_stats=Mock()
        )

        commit_metadata = CommitMetadata(
            sha="abc123",
            message="Empty commit",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=datetime.now(),
            repository_name="test/repo"
        )

        with pytest.raises(DiffAnalyzerError, match="No file changes to analyze"):
            analyzer.analyze(parsed_diff, commit_metadata)

    def test_analyze_missing_commit_sha(self):
        analyzer = DiffAnalyzer()

        parsed_diff = ParsedDiff(
            repository_name="test/repo",
            commit_sha="abc123",
            file_changes=[Mock(filename="test.py")],
            diff_stats=Mock()
        )

        commit_metadata = CommitMetadata(
            sha="",  # 빈 SHA
            message="Test commit",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=datetime.now(),
            repository_name="test/repo"
        )

        with pytest.raises(DiffAnalyzerError, match="Missing commit SHA"):
            analyzer.analyze(parsed_diff, commit_metadata)


class TestDiffAnalysisResult:
    """DiffAnalysisResult 모델 테스트"""

    def test_get_summary(self):
        # 언어별 통계 데이터 생성
        language_stats = {
            "python": LanguageStats(
                language="python",
                file_count=2,
                lines_added=15,
                lines_deleted=3
            ),
            "javascript": LanguageStats(
                language="javascript",
                file_count=1,
                lines_added=10,
                lines_deleted=5
            )
        }

        result = DiffAnalysisResult(
            commit_sha="abc123",
            repository_name="test/repo",
            author_email="test@example.com",
            timestamp=datetime.now(),
            total_files_changed=3,
            total_additions=25,
            total_deletions=8,
            language_breakdown=language_stats,
            functions_added=["new_func"],
            functions_modified=["existing_func"],
            classes_added=["NewClass"],
            complexity_delta=2.5
        )

        summary = result.get_summary()

        # 요약 정보 검증
        assert summary["commit_info"]["sha"] == "abc123"
        assert summary["commit_info"]["repository"] == "test/repo"
        assert summary["change_summary"]["files_changed"] == 3
        assert summary["change_summary"]["lines_added"] == 25
        assert summary["change_summary"]["net_change"] == 17
        assert summary["structural_summary"]["functions_total_changed"] == 2
        assert summary["structural_summary"]["classes_total_changed"] == 1
        assert summary["language_summary"]["primary_language"] == "python"
        assert summary["quality_impact"]["complexity_delta"] == 2.5


if __name__ == "__main__":
    pytest.main([__file__])
