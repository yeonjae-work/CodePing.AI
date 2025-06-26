"""
DiffAnalyzer 모듈 사용 예제

이 예제는 GitDataParser에서 파싱된 데이터를 DiffAnalyzer로 분석하는 과정을 보여줍니다.
"""

import os
import sys
from datetime import datetime
from typing import List

# 프로젝트 루트 디렉터리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.diff_analyzer import DiffAnalyzer
from modules.diff_analyzer.models import ParsedDiff, CommitMetadata, RepositoryContext
from modules.git_data_parser.models import FileChange, DiffStats


def create_sample_file_changes() -> List[FileChange]:
    """샘플 파일 변경사항 생성"""
    
    # Python 파일 변경 (새로운 사용자 인증 기능)
    python_patch = """@@ -1,10 +1,25 @@
+from datetime import datetime
+from typing import Optional
+
 class User:
-    def __init__(self, name):
+    def __init__(self, name: str, email: str):
         self.name = name
+        self.email = email
+        self.created_at = datetime.now()
+    
+    def authenticate(self, password: str) -> bool:
+        \"\"\"사용자 인증\"\"\"
+        if not password:
+            return False
+        
+        # 실제로는 해시 비교를 해야 함
+        return len(password) >= 8
+    
+    def get_profile(self) -> dict:
+        \"\"\"사용자 프로필 정보 반환\"\"\"
+        return {
+            "name": self.name,
+            "email": self.email,
+            "created_at": self.created_at.isoformat()
+        }
"""
    
    # JavaScript 파일 변경 (API 클라이언트)
    js_patch = """@@ -5,15 +5,30 @@
 class ApiClient {
-    constructor(baseUrl) {
+    constructor(baseUrl, apiKey = null) {
         this.baseUrl = baseUrl;
+        this.apiKey = apiKey;
+        this.timeout = 5000;
     }
     
-    async get(endpoint) {
-        const response = await fetch(`${this.baseUrl}${endpoint}`);
+    async get(endpoint, options = {}) {
+        const headers = {
+            'Content-Type': 'application/json',
+            ...options.headers
+        };
+        
+        if (this.apiKey) {
+            headers['Authorization'] = `Bearer ${this.apiKey}`;
+        }
+        
+        const response = await fetch(`${this.baseUrl}${endpoint}`, {
+            method: 'GET',
+            headers,
+            timeout: this.timeout,
+            ...options
+        });
+        
+        if (!response.ok) {
+            throw new Error(`API request failed: ${response.status}`);
+        }
+        
         return response.json();
     }
 }
"""
    
    # 테스트 파일 변경
    test_patch = """@@ -0,0 +1,25 @@
+import pytest
+from user import User
+
+class TestUser:
+    def test_user_creation(self):
+        user = User("John Doe", "john@example.com")
+        assert user.name == "John Doe"
+        assert user.email == "john@example.com"
+        assert user.created_at is not None
+    
+    def test_authentication_success(self):
+        user = User("John Doe", "john@example.com")
+        assert user.authenticate("password123") == True
+    
+    def test_authentication_failure(self):
+        user = User("John Doe", "john@example.com")
+        assert user.authenticate("123") == False
+        assert user.authenticate("") == False
+    
+    def test_get_profile(self):
+        user = User("John Doe", "john@example.com")
+        profile = user.get_profile()
+        assert profile["name"] == "John Doe"
+        assert profile["email"] == "john@example.com"
+        assert "created_at" in profile
"""
    
    return [
        FileChange(
            filename="src/auth/user.py",
            status="modified",
            additions=18,
            deletions=2,
            file_type="python",
            patch=python_patch
        ),
        FileChange(
            filename="src/api/client.js",
            status="modified", 
            additions=15,
            deletions=3,
            file_type="javascript",
            patch=js_patch
        ),
        FileChange(
            filename="tests/test_user.py",
            status="added",
            additions=25,
            deletions=0,
            file_type="python",
            patch=test_patch
        ),
        FileChange(
            filename="README.md",
            status="modified",
            additions=5,
            deletions=1,
            file_type="markdown",
            patch="@@ -1,3 +1,7 @@\n # User Auth System\n+\n+## Features\n+- User authentication\n+- Profile management\n+- API client with auth support"
        )
    ]


def main():
    """메인 실행 함수"""
    
    print("🔍 DiffAnalyzer 모듈 데모 시작")
    print("=" * 50)
    
    # 1. 샘플 데이터 생성
    file_changes = create_sample_file_changes()
    
    diff_stats = DiffStats(
        total_additions=63,
        total_deletions=6,
        files_changed=4,
        files_added=1,
        files_modified=3,
        files_removed=0
    )
    
    # ParsedDiff 객체 생성
    parsed_diff = ParsedDiff(
        repository_name="example/auth-system",
        commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
        file_changes=file_changes,
        diff_stats=diff_stats
    )
    
    # 커밋 메타데이터 생성
    commit_metadata = CommitMetadata(
        sha="a1b2c3d4e5f6789012345678901234567890abcd",
        message="feat: Add user authentication and API client improvements",
        author_name="김개발자",
        author_email="dev@example.com",
        timestamp=datetime.now(),
        repository_name="example/auth-system",
        branch_name="feature/user-auth"
    )
    
    # 저장소 컨텍스트 (선택적)
    repository_context = RepositoryContext(
        repository_name="example/auth-system",
        default_branch="main",
        primary_language="python",
        project_type="web",
        frameworks=["FastAPI", "React"]
    )
    
    print(f"📊 분석 대상: {parsed_diff.repository_name}")
    print(f"📝 커밋: {commit_metadata.sha[:8]}... - {commit_metadata.message}")
    print(f"👤 작성자: {commit_metadata.author_name} ({commit_metadata.author_email})")
    print(f"📁 변경된 파일: {len(file_changes)}개")
    print(f"➕ 추가: {diff_stats.total_additions}줄, ➖ 삭제: {diff_stats.total_deletions}줄")
    print()
    
    # 2. DiffAnalyzer로 분석 수행
    print("🔬 코드 변경사항 분석 중...")
    
    analyzer = DiffAnalyzer()
    
    try:
        analysis_result = analyzer.analyze(
            parsed_diff=parsed_diff,
            commit_metadata=commit_metadata,
            repository_context=repository_context
        )
        
        print("✅ 분석 완료!")
        print()
        
        # 3. 결과 출력
        print("📈 분석 결과")
        print("-" * 30)
        
        print(f"⏱️  분석 시간: {analysis_result.analysis_duration_seconds:.3f}초")
        print(f"📁 총 파일 변경: {analysis_result.total_files_changed}개")
        print(f"➕ 총 추가 라인: {analysis_result.total_additions}줄")
        print(f"➖ 총 삭제 라인: {analysis_result.total_deletions}줄")
        print(f"📊 복잡도 변화: {analysis_result.complexity_delta:+.2f}")
        print()
        
        # 언어별 분석 결과
        print("🔤 언어별 분석")
        print("-" * 20)
        for language, stats in analysis_result.language_breakdown.items():
            print(f"  {language}:")
            print(f"    - 파일 수: {stats.file_count}개")
            print(f"    - 추가: {stats.lines_added}줄, 삭제: {stats.lines_deleted}줄")
            print(f"    - 복잡도 변화: {stats.complexity_delta:+.2f}")
        print()
        
        # 파일별 상세 분석
        print("📄 파일별 분석")
        print("-" * 20)
        for analyzed_file in analysis_result.analyzed_files:
            print(f"  📝 {analyzed_file.file_path}")
            print(f"     언어: {analyzed_file.language}")
            print(f"     타입: {analyzed_file.file_type.value}")
            print(f"     변경: {analyzed_file.change_type.value}")
            print(f"     라인: +{analyzed_file.lines_added} -{analyzed_file.lines_deleted}")
            print(f"     복잡도: {analyzed_file.complexity_delta:+.2f}")
            if analyzed_file.functions_changed > 0:
                print(f"     함수 변경: {analyzed_file.functions_changed}개")
            if analyzed_file.classes_changed > 0:
                print(f"     클래스 변경: {analyzed_file.classes_changed}개")
            print()
        
        # 지원되지 않는 파일
        if analysis_result.unsupported_files_count > 0:
            print(f"⚠️  지원되지 않는 파일: {analysis_result.unsupported_files_count}개")
            print()
        
        # 요약 정보
        print("📋 분석 요약")
        print("-" * 20)
        summary = analysis_result.get_summary()
        
        change_summary = summary["change_summary"]
        structural_summary = summary["structural_summary"]
        language_summary = summary["language_summary"]
        quality_impact = summary["quality_impact"]
        
        print(f"순 변경량: {change_summary['net_change']:+d}줄")
        print(f"주요 언어: {language_summary['primary_language']}")
        print(f"영향받은 언어: {', '.join(language_summary['languages_affected'])}")
        print(f"총 구조 변경: 함수 {structural_summary['functions_total_changed']}개, "
              f"클래스 {structural_summary['classes_total_changed']}개")
        print(f"품질 영향: 복잡도 {quality_impact['complexity_delta']:+.2f}")
        
        print()
        print("🎉 분석 완료! DiffAnalyzer가 성공적으로 코드 변경사항을 분석했습니다.")
        
        # DataStorage 연동 힌트
        print()
        print("💡 다음 단계:")
        print("   1. DataStorage 모듈로 분석 결과 저장")
        print("   2. LLMService로 자연어 요약 생성")
        print("   3. SlackNotifier로 팀에 알림 전송")
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 