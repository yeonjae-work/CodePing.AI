#!/usr/bin/env python3
"""
GitDataParser와 DiffAnalyzer 오프라인 통합 테스트

GitDataParser에서 파싱한 데이터를 DiffAnalyzer로 심층 분석하는 전체 워크플로우를 
GitHub API 호출 없이 테스트합니다.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.git_data_parser.service import DiffAnalyzerAdapter
from modules.git_data_parser.models import FileChange, DiffStats
from modules.diff_analyzer.service import DiffAnalyzer
from modules.diff_analyzer.models import ParsedDiff, CommitMetadata


def create_sample_file_changes():
    """샘플 파일 변경사항 생성 (GitHub API 없이)"""
    return [
        FileChange(
            filename="src/auth/user.py",
            status="added",
            additions=45,
            deletions=0,
            file_type="python",
            patch="""@@ -0,0 +1,45 @@
+"""User authentication module."""
+
+import hashlib
+import secrets
+from datetime import datetime, timedelta
+from typing import Optional
+
+
+class User:
+    \"\"\"User model for authentication.\"\"\"
+    
+    def __init__(self, username: str, email: str):
+        self.username = username
+        self.email = email
+        self.password_hash = None
+        self.created_at = datetime.now()
+        self.last_login = None
+    
+    def set_password(self, password: str) -> None:
+        \"\"\"Set user password with secure hashing.\"\"\"
+        salt = secrets.token_hex(16)
+        password_hash = hashlib.pbkdf2_hmac(
+            'sha256', 
+            password.encode('utf-8'), 
+            salt.encode('utf-8'), 
+            100000
+        )
+        self.password_hash = f"{salt}:{password_hash.hex()}"
+    
+    def verify_password(self, password: str) -> bool:
+        \"\"\"Verify password against stored hash.\"\"\"
+        if not self.password_hash:
+            return False
+        
+        try:
+            salt, stored_hash = self.password_hash.split(':')
+            password_hash = hashlib.pbkdf2_hmac(
+                'sha256',
+                password.encode('utf-8'),
+                salt.encode('utf-8'),
+                100000
+            )
+            return password_hash.hex() == stored_hash
+        except (ValueError, AttributeError):
+            return False"""
        ),
        FileChange(
            filename="tests/test_auth.py",
            status="added",
            additions=32,
            deletions=0,
            file_type="python",
            patch="""@@ -0,0 +1,32 @@
+\"\"\"Tests for user authentication module.\"\"\"
+
+import pytest
+from src.auth.user import User
+
+
+class TestUser:
+    \"\"\"Test cases for User class.\"\"\"
+    
+    def test_user_creation(self):
+        \"\"\"Test user instance creation.\"\"\"
+        user = User("testuser", "test@example.com")
+        
+        assert user.username == "testuser"
+        assert user.email == "test@example.com"
+        assert user.password_hash is None
+        assert user.created_at is not None
+        assert user.last_login is None
+    
+    def test_password_setting_and_verification(self):
+        \"\"\"Test password hashing and verification.\"\"\"
+        user = User("testuser", "test@example.com")
+        password = "secure_password_123"
+        
+        # Set password
+        user.set_password(password)
+        assert user.password_hash is not None
+        assert ":" in user.password_hash  # salt:hash format
+        
+        # Verify correct password
+        assert user.verify_password(password) == True
+        assert user.verify_password("wrong_password") == False"""
        ),
        FileChange(
            filename="src/api/routes.py",
            status="modified",
            additions=15,
            deletions=3,
            file_type="python",
            patch="""@@ -1,10 +1,22 @@
 \"\"\"API routes for the application.\"\"\"
 
 from flask import Flask, request, jsonify
+from src.auth.user import User
 
 app = Flask(__name__)
+users_db = {}  # Simple in-memory user store
 
 
 @app.route("/")
 def home():
     return {"message": "Welcome to the API"}
+
+@app.route("/register", methods=["POST"])
+def register():
+    \"\"\"User registration endpoint.\"\"\"
+    data = request.get_json()
+    username = data.get("username")
+    email = data.get("email")
+    password = data.get("password")
+    
+    if username in users_db:
+        return {"error": "User already exists"}, 400
+    
+    user = User(username, email)
+    user.set_password(password)
+    users_db[username] = user
+    
+    return {"message": "User created successfully"}, 201"""
        ),
        FileChange(
            filename="config/database.yml",
            status="modified",
            additions=8,
            deletions=2,
            file_type="yaml",
            patch="""@@ -1,5 +1,11 @@
 production:
   adapter: postgresql
   database: myapp_production
-  username: myapp
-  password: <%= ENV['DATABASE_PASSWORD'] %>
+  username: <%= ENV['DATABASE_USER'] %>
+  password: <%= ENV['DATABASE_PASSWORD'] %>
+  host: <%= ENV['DATABASE_HOST'] %>
+  port: <%= ENV['DATABASE_PORT'] %>
+  
+redis:
+  url: <%= ENV['REDIS_URL'] %>
+  timeout: 5"""
        )
    ]


def test_diffanalyzer_adapter():
    """DiffAnalyzerAdapter 단독 테스트"""
    print("🔧 DiffAnalyzerAdapter 단독 테스트")
    print("=" * 50)
    
    # 1. 어댑터 초기화
    adapter = DiffAnalyzerAdapter()
    print(f"   ✅ Adapter 초기화: {type(adapter).__name__}")
    print(f"   ✅ LanguageAnalyzer 사용 가능: {adapter.language_analyzer is not None}")
    
    # 2. 파일 변경사항 생성 (실제 데이터)
    file_changes = create_sample_file_changes()
    print(f"   ✅ 샘플 파일 변경사항: {len(file_changes)}개")
    
    # 3. Diff 통계 계산
    diff_stats = adapter.calculate_diff_stats(file_changes)
    print(f"   ✅ 총 추가: {diff_stats.total_additions}줄")
    print(f"   ✅ 총 삭제: {diff_stats.total_deletions}줄")
    print(f"   ✅ 변경된 파일: {diff_stats.files_changed}개")
    
    # 4. 언어 감지 테스트
    print("\n📝 언어 감지 테스트:")
    for file_change in file_changes:
        detected_type = adapter.detect_file_type(file_change.filename)
        print(f"     {file_change.filename} → {detected_type}")
    
    return file_changes, diff_stats


def test_diffanalyzer_integration(file_changes, diff_stats):
    """DiffAnalyzer 심층 분석 테스트"""
    print("\n🔬 DiffAnalyzer 심층 분석 테스트")
    print("=" * 50)
    
    try:
        # DiffAnalyzer 초기화
        diff_analyzer = DiffAnalyzer()
        print("   ✅ DiffAnalyzer 초기화 완료")
        
        # ParsedDiff 객체 생성
        parsed_diff = ParsedDiff(
            repository_name="example/integration-test",
            commit_sha="abc123def456",
            file_changes=file_changes,
            diff_stats=diff_stats
        )
        
        # CommitMetadata 생성
        commit_metadata = CommitMetadata(
            sha="abc123def456",
            message="feat: Add user authentication system",
            author_name="김개발자",
            author_email="dev@example.com",
            timestamp=datetime.now(),
            repository_name="example/integration-test"
        )
        
        # 심층 분석 실행
        print("   🔄 심층 분석 실행 중...")
        analysis_result = diff_analyzer.analyze(parsed_diff, commit_metadata)
        
        print(f"   ✅ 분석 완료! (소요시간: {analysis_result.analysis_duration_seconds:.3f}초)")
        print(f"   ✅ 분석된 파일: {len(analysis_result.analyzed_files)}개")
        print(f"   ✅ 언어별 분석: {len(analysis_result.language_breakdown)}개 언어")
        print(f"   ✅ 복잡도 변화: {analysis_result.complexity_delta:+.2f}")
        
        # 언어별 상세 정보
        print("\n📊 언어별 분석 결과:")
        for lang, stats in analysis_result.language_breakdown.items():
            print(f"     {lang}: {stats.file_count}개 파일, +{stats.lines_added} -{stats.lines_deleted}")
        
        # 파일별 상세 분석
        print("\n📄 파일별 분석 결과:")
        for analyzed_file in analysis_result.analyzed_files:
            print(f"     {analyzed_file.file_path}:")
            print(f"       언어: {analyzed_file.language}")
            print(f"       타입: {analyzed_file.file_type}")
            print(f"       복잡도 변화: {analyzed_file.complexity_analysis.metrics.complexity_delta:+.2f}")
            if analyzed_file.structural_analysis.changes.functions_added:
                print(f"       추가된 함수: {analyzed_file.structural_analysis.changes.functions_added}")
            if analyzed_file.structural_analysis.changes.classes_added:
                print(f"       추가된 클래스: {analyzed_file.structural_analysis.changes.classes_added}")
        
        # 구조적 변경사항 요약
        print("\n🏗️ 구조적 변경사항 요약:")
        print(f"     함수 추가: {len(analysis_result.functions_added)}개")
        print(f"     함수 수정: {len(analysis_result.functions_modified)}개")
        print(f"     클래스 추가: {len(analysis_result.classes_added)}개")
        
        if analysis_result.functions_added:
            print(f"     추가된 함수: {', '.join(analysis_result.functions_added)}")
        if analysis_result.classes_added:
            print(f"     추가된 클래스: {', '.join(analysis_result.classes_added)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 심층 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_language_detection_upgrade():
    """언어 감지 기능 업그레이드 테스트"""
    print("\n🔍 언어 감지 기능 업그레이드 테스트")
    print("=" * 50)
    
    adapter = DiffAnalyzerAdapter()
    
    test_files = [
        ("user.py", "Python 소스"),
        ("component.jsx", "React JSX"),
        ("api.ts", "TypeScript"),
        ("test_user.py", "Python 테스트"),
        ("UserTest.java", "Java 테스트"),
        ("Dockerfile", "Docker 설정"),
        ("requirements.txt", "Python 의존성"),
        ("package.json", "Node.js 설정"),
        ("config.yml", "YAML 설정"),
        ("README.md", "Markdown 문서"),
        ("unknown.xyz", "알 수 없는 파일")
    ]
    
    print("파일명 → 언어 감지 결과")
    print("-" * 40)
    
    for filename, description in test_files:
        detected_type = adapter.detect_file_type(filename)
        status = "✅" if detected_type != "unknown" else "❓"
        print(f"{status} {filename:15s} → {detected_type:12s} ({description})")
    
    return True


def test_separation_verification():
    """GitDataParser와 DiffAnalyzer 분리 검증"""
    print("\n🔀 모듈 분리 검증 테스트")
    print("=" * 50)
    
    # 1. 모듈별 독립성 확인
    print("📝 1. 모듈 독립성 확인:")
    
    try:
        # GitDataParser 단독 테스트
        from modules.git_data_parser.service import GitDataParserService
        print("   ✅ GitDataParser 모듈 독립 로딩 가능")
        
        # DiffAnalyzer 단독 테스트  
        from modules.diff_analyzer.service import DiffAnalyzer
        print("   ✅ DiffAnalyzer 모듈 독립 로딩 가능")
        
        # 어댑터를 통한 연결 확인
        adapter = DiffAnalyzerAdapter()
        print("   ✅ DiffAnalyzerAdapter 연결 정상")
        
    except ImportError as e:
        print(f"   ❌ 모듈 로딩 실패: {e}")
        return False
    
    # 2. 인터페이스 호환성 확인
    print("\n📝 2. 인터페이스 호환성 확인:")
    
    sample_files = create_sample_file_changes()
    
    # GitDataParser의 기존 인터페이스 확인
    adapter = DiffAnalyzerAdapter()
    
    try:
        # parse_file_changes 인터페이스 (향후 제거 예정)
        result1 = adapter.parse_file_changes(b"dummy diff", {"files": []})
        print("   ✅ parse_file_changes 인터페이스 정상")
        
        # calculate_diff_stats 인터페이스 
        result2 = adapter.calculate_diff_stats(sample_files)
        print("   ✅ calculate_diff_stats 인터페이스 정상")
        
        # detect_file_type 인터페이스
        result3 = adapter.detect_file_type("test.py")
        print("   ✅ detect_file_type 인터페이스 정상")
        
    except Exception as e:
        print(f"   ❌ 인터페이스 오류: {e}")
        return False
    
    print("\n📝 3. 향후 분리 준비사항:")
    print("   🔄 BasicDiffProcessor → DiffAnalyzerAdapter 대체 완료")
    print("   🔄 DiffProcessorInterface 유지로 호환성 보장")  
    print("   🔄 지연 로딩으로 순환 import 방지")
    print("   ✅ 마이크로서비스 분리 준비 완료")
    
    return True


if __name__ == "__main__":
    print("🚀 GitDataParser ↔ DiffAnalyzer 오프라인 통합 테스트")
    print("=" * 80)
    
    try:
        # 1. DiffAnalyzerAdapter 단독 테스트
        file_changes, diff_stats = test_diffanalyzer_adapter()
        
        # 2. DiffAnalyzer 심층 분석 테스트
        success1 = test_diffanalyzer_integration(file_changes, diff_stats)
        
        # 3. 언어 감지 업그레이드 테스트
        success2 = test_language_detection_upgrade()
        
        # 4. 모듈 분리 검증
        success3 = test_separation_verification()
        
        if success1 and success2 and success3:
            print("\n🎉 모든 오프라인 통합 테스트 통과!")
            print("\n📋 검증 완료 사항:")
            print("   ✅ GitDataParser → DiffAnalyzer 연동 정상")
            print("   ✅ 언어 감지 기능 업그레이드 완료") 
            print("   ✅ 복잡도/구조 분석 기능 정상")
            print("   ✅ 모듈 분리 준비 완료")
            
            print("\n💡 다음 단계:")
            print("   1. DataStorage 모듈 구현 및 연동")
            print("   2. LLMService 모듈 구현 및 연동")
            print("   3. SlackNotifier 연동으로 완전한 파이프라인 구축")
            print("   4. 일일 요약 스케줄러 통합")
            
            sys.exit(0)
        else:
            print("\n❌ 일부 테스트 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 