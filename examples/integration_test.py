#!/usr/bin/env python3
"""
GitDataParser와 DiffAnalyzer 통합 테스트

GitDataParser에서 파싱한 데이터를 DiffAnalyzer로 심층 분석하는 전체 워크플로우를 테스트합니다.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.git_data_parser.service import GitDataParserService, DiffAnalyzerAdapter
from modules.diff_analyzer.service import DiffAnalyzer
from modules.diff_analyzer.models import ParsedDiff, CommitMetadata


def create_simple_webhook_payload():
    """간단한 테스트용 webhook payload 생성"""
    return {
        "repository": {
            "full_name": "example/integration-test",
            "name": "integration-test"
        },
        "ref": "refs/heads/main",
        "after": "abc123def456",
        "pusher": {
            "name": "testuser"
        },
        "commits": [
            {
                "id": "abc123def456",
                "message": "feat: Add user authentication system",
                "timestamp": "2024-01-15T10:30:00Z",
                "url": "https://github.com/example/repo/commit/abc123def456",
                "author": {
                    "name": "김개발자",
                    "email": "dev@example.com",
                    "username": "kimdev"
                },
                "added": ["src/auth/user.py"],
                "modified": ["src/api/routes.py"],
                "removed": []
            }
        ],
        "files": [
            {
                "filename": "src/auth/user.py",
                "status": "added",
                "additions": 45,
                "deletions": 0,
                "patch": "+def authenticate_user(username, password):\n+    # User authentication logic\n+    return True"
            },
            {
                "filename": "src/api/routes.py",
                "status": "modified",
                "additions": 15,
                "deletions": 3,
                "patch": "+@app.route('/login')\n+def login():\n+    return authenticate_user()"
            }
        ]
    }


def test_gitdataparser_integration():
    """GitDataParser의 DiffAnalyzer 통합 테스트"""
    print("🔄 GitDataParser와 DiffAnalyzer 통합 테스트 시작")
    print("=" * 60)
    
    # 1. GitDataParser 서비스 초기화 (DiffAnalyzerAdapter 사용)
    print("📝 1. GitDataParser 서비스 초기화...")
    parser_service = GitDataParserService()
    
    # DiffAnalyzerAdapter가 정상적으로 로드되었는지 확인
    adapter = parser_service.diff_processor
    print(f"   ✅ DiffProcessor: {type(adapter).__name__}")
    print(f"   ✅ LanguageAnalyzer 사용 가능: {adapter.language_analyzer is not None}")
    
    # 2. 샘플 webhook 데이터 파싱
    print("\n📝 2. Webhook 데이터 파싱...")
    payload = create_simple_webhook_payload()
    headers = {"x-github-event": "push"}
    
    try:
        parsed_data = parser_service.parse_webhook_data(payload, headers)
        print(f"   ✅ Repository: {parsed_data.repository}")
        print(f"   ✅ 파일 변경: {len(parsed_data.file_changes)}개")
        print(f"   ✅ 총 추가: {parsed_data.diff_stats.total_additions}줄")
        print(f"   ✅ 총 삭제: {parsed_data.diff_stats.total_deletions}줄")
        
        # 파일별 정보 출력
        for file_change in parsed_data.file_changes:
            print(f"     - {file_change.filename} ({file_change.file_type}): +{file_change.additions} -{file_change.deletions}")
            
    except Exception as e:
        print(f"   ❌ 파싱 실패: {e}")
        return False
    
    # 3. DiffAnalyzer로 심층 분석
    print("\n📝 3. DiffAnalyzer로 심층 분석...")
    try:
        # DiffAnalyzer 초기화
        diff_analyzer = DiffAnalyzer()
        
        # ParsedDiff 객체 생성 (GitDataParser 결과를 DiffAnalyzer 입력으로 변환)
        parsed_diff = ParsedDiff(
            repository_name=parsed_data.repository,
            commit_sha=parsed_data.commits[0].sha if parsed_data.commits else "unknown",
            file_changes=parsed_data.file_changes,
            diff_stats=parsed_data.diff_stats
        )
        
        # CommitMetadata 생성
        first_commit = parsed_data.commits[0] if parsed_data.commits else None
        commit_metadata = CommitMetadata(
            sha=first_commit.sha if first_commit else "unknown",
            message=first_commit.message if first_commit else "No message",
            author_name=first_commit.author.name if first_commit else "Unknown",
            author_email=first_commit.author.email if first_commit else "unknown@example.com",
            timestamp=first_commit.timestamp if first_commit else datetime.now(),
            repository_name=parsed_data.repository
        )
        
        # 심층 분석 실행
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
        
    except Exception as e:
        print(f"   ❌ 심층 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 통합 테스트 성공!")
    print("   GitDataParser → DiffAnalyzer 연동이 정상적으로 작동합니다.")
    return True


def test_language_detection_upgrade():
    """언어 감지 기능 업그레이드 테스트"""
    print("\n🔍 언어 감지 기능 업그레이드 테스트")
    print("=" * 60)
    
    # 1. 기본 어댑터와 DiffAnalyzer 비교
    adapter = DiffAnalyzerAdapter()
    
    test_files = [
        "user.py",
        "component.jsx", 
        "api.ts",
        "test_user.py",
        "UserTest.java",
        "setup.cfg",
        "README.md",
        "unknown.xyz"
    ]
    
    print("파일명 → 기본 감지 vs DiffAnalyzer 감지")
    print("-" * 50)
    
    for filename in test_files:
        # 기본 감지 (fallback)
        path = Path(filename)
        extension = path.suffix.lower()
        basic_type = adapter.file_types.get(extension, 'unknown')
        
        # DiffAnalyzer 감지
        detected_type = adapter.detect_file_type(filename)
        
        upgrade_indicator = "🔄" if basic_type != detected_type else "✅"
        print(f"{upgrade_indicator} {filename:15s} → {basic_type:10s} vs {detected_type:10s}")
    
    return True


if __name__ == "__main__":
    print("🚀 GitDataParser ↔ DiffAnalyzer 통합 테스트 시작")
    print("=" * 80)
    
    try:
        # 기본 통합 테스트
        success1 = test_gitdataparser_integration()
        
        # 언어 감지 업그레이드 테스트  
        success2 = test_language_detection_upgrade()
        
        if success1 and success2:
            print("\n✅ 모든 통합 테스트 통과!")
            print("\n💡 다음 단계:")
            print("   1. DataStorage 모듈로 분석 결과 저장")
            print("   2. LLMService로 자연어 요약 생성") 
            print("   3. SlackNotifier로 팀 알림 전송")
            sys.exit(0)
        else:
            print("\n❌ 일부 테스트 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 