#!/usr/bin/env python3
"""
DataStorage MVP 버전 데모 스크립트

이 스크립트는 DataStorage 모듈의 주요 기능들을 시연합니다.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.data_storage.models import CommitData, DiffData, StorageStatus
from modules.data_storage.service import DataStorageManager


def demo_basic_storage():
    """기본 저장 기능 데모"""
    print("🚀 DataStorage MVP 데모 시작\n")

    print("1️⃣ 기본 커밋 저장")
    print("=" * 50)

    # 샘플 커밋 데이터
    commit_data = CommitData(
        commit_hash="demo123abc456def",
        message="DataStorage MVP 데모 커밋",
        author="demo@codeping.ai",
        author_email="demo@codeping.ai",
        timestamp=datetime.now(timezone.utc),
        repository="codeping/demo-repo",
        branch="feature/datastorage-mvp",
        pusher="demo-user",
        commit_count=1,
    )

    # 샘플 diff 데이터
    diff_data = [
        DiffData(
            file_path="src/data_storage/manager.py",
            additions=45,
            deletions=12,
            changes="Added MVP DataStorageManager implementation",
            diff_content=b"""diff --git a/src/data_storage/manager.py b/src/data_storage/manager.py
index 1234567..abcdefg 100644
--- a/src/data_storage/manager.py
+++ b/src/data_storage/manager.py
@@ -1,3 +1,48 @@
+class DataStorageManager:
+    def __init__(self):
+        self.db_session = None
+    
+    def store_commit(self, commit_data, diff_data):
+        # MVP implementation
+        pass
""",
        ),
        DiffData(
            file_path="tests/test_data_storage.py",
            additions=28,
            deletions=5,
            changes="Added comprehensive test cases",
            diff_content=b"""diff --git a/tests/test_data_storage.py b/tests/test_data_storage.py
index 7890123..fedcba9 100644
--- a/tests/test_data_storage.py
+++ b/tests/test_data_storage.py
@@ -1,2 +1,30 @@
+import pytest
+from modules.data_storage.service import DataStorageManager
""",
        ),
        DiffData(
            file_path="docs/datastorage_guide.md",
            additions=156,
            deletions=0,
            changes="Added complete usage documentation",
            diff_content=b"""diff --git a/docs/datastorage_guide.md b/docs/datastorage_guide.md
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/docs/datastorage_guide.md
@@ -0,0 +1,156 @@
+# DataStorage MVP Guide
+
+This guide explains how to use the DataStorage module.
""",
        ),
    ]

    # 저장 실행
    manager = DataStorageManager()
    result = manager.store_commit(commit_data, diff_data)

    # 결과 출력
    print(f"✅ 저장 결과: {result.status.value}")
    print(f"📊 커밋 ID: {result.commit_id}")
    print(f"📈 통계:")
    print(f"   - 변경된 파일: {result.metadata.get('files_changed', 0)}개")
    print(f"   - 추가된 라인: +{result.metadata.get('total_additions', 0)}")
    print(f"   - 삭제된 라인: -{result.metadata.get('total_deletions', 0)}")
    print(f"   - 처리 시간: {result.metadata.get('duration_seconds', 0):.3f}초")
    print()

    return result


def demo_duplicate_handling(manager):
    """중복 커밋 처리 데모"""
    print("2️⃣ 중복 커밋 처리")
    print("=" * 50)

    # 같은 해시로 다시 저장 시도
    duplicate_commit = CommitData(
        commit_hash="demo123abc456def",  # 같은 해시
        message="중복된 커밋 시도",
        author="another@codeping.ai",
        timestamp=datetime.now(timezone.utc),
        repository="codeping/demo-repo",
        branch="main",
    )

    result = manager.store_commit(duplicate_commit, [])

    print(f"🔒 중복 저장 시도 결과: {result.status.value}")
    print(f"💬 메시지: {result.message}")
    print(f"🏷️  커밋 해시: {result.metadata.get('commit_hash', 'N/A')}")
    print()


def demo_commit_retrieval(manager):
    """커밋 조회 기능 데모"""
    print("3️⃣ 커밋 조회")
    print("=" * 50)

    # 해시로 조회
    commit_hash = "demo123abc456def"
    commit_with_diffs = manager.get_commit_by_hash(commit_hash)

    if commit_with_diffs:
        commit = commit_with_diffs.commit
        print(f"🔍 조회된 커밋 정보:")
        print(f"   - 해시: {commit.hash}")
        print(f"   - 메시지: {commit.message}")
        print(f"   - 작성자: {commit.author}")
        print(f"   - 저장소: {commit.repository}")
        print(f"   - 브랜치: {commit.branch}")
        print(f"   - 시간: {commit.timestamp}")
        print(f"   - 파일 수: {commit.diff_count}")
        print(f"   - 총 변경: +{commit.total_additions}/-{commit.total_deletions}")

        print(f"\n📁 변경된 파일들:")
        for i, diff in enumerate(commit_with_diffs.diffs, 1):
            print(f"   {i}. {diff.file_path}")
            print(
                f"      +{diff.additions}/-{diff.deletions} (내용 있음: {diff.has_content})"
            )
    else:
        print(f"❌ 커밋을 찾을 수 없습니다: {commit_hash}")

    print()


def demo_recent_commits(manager):
    """최근 커밋 목록 조회 데모"""
    print("4️⃣ 최근 커밋 목록")
    print("=" * 50)

    recent_commits = manager.get_recent_commits("codeping/demo-repo", limit=5)

    if recent_commits:
        print(f"📋 최근 커밋 {len(recent_commits)}개:")
        for i, commit in enumerate(recent_commits, 1):
            print(f"   {i}. {commit.hash[:12]} - {commit.message[:50]}")
            print(f"      👤 {commit.author} | 🌿 {commit.branch}")
            print(
                f"      📊 {commit.diff_count}개 파일, +{commit.total_additions}/-{commit.total_deletions}"
            )
            print()
    else:
        print("📭 저장된 커밋이 없습니다.")


def demo_multiple_commits(manager):
    """여러 커밋 저장 데모"""
    print("5️⃣ 여러 커밋 저장")
    print("=" * 50)

    commits_to_store = [
        {
            "hash": "feature1_hash123",
            "message": "Feature: Add user authentication",
            "files": ["auth/login.py", "auth/models.py"],
            "stats": [(25, 3), (15, 0)],
        },
        {
            "hash": "bugfix1_hash456",
            "message": "Bugfix: Fix database connection timeout",
            "files": ["database/connection.py"],
            "stats": [(8, 12)],
        },
        {
            "hash": "refactor1_hash789",
            "message": "Refactor: Improve error handling",
            "files": ["utils/errors.py", "core/handlers.py", "tests/test_errors.py"],
            "stats": [(45, 23), (12, 8), (67, 2)],
        },
    ]

    print(f"📦 {len(commits_to_store)}개 커밋 배치 저장 중...")

    successful = 0
    total_files = 0
    total_additions = 0
    total_deletions = 0

    for i, commit_info in enumerate(commits_to_store, 1):
        commit_data = CommitData(
            commit_hash=commit_info["hash"],
            message=commit_info["message"],
            author="batch@codeping.ai",
            timestamp=datetime.now(timezone.utc),
            repository="codeping/demo-repo",
            branch="main",
        )

        diff_data = []
        for j, (file_path, (adds, dels)) in enumerate(
            zip(commit_info["files"], commit_info["stats"])
        ):
            diff_data.append(
                DiffData(
                    file_path=file_path,
                    additions=adds,
                    deletions=dels,
                    changes=f"Changes in {file_path}",
                    diff_content=f"Sample diff content for {file_path}".encode(),
                )
            )

        result = manager.store_commit(commit_data, diff_data)

        if result.success:
            successful += 1
            total_files += len(diff_data)
            total_additions += result.metadata.get("total_additions", 0)
            total_deletions += result.metadata.get("total_deletions", 0)
            print(f"   ✅ {i}/3: {commit_info['message'][:40]}...")
        else:
            print(f"   ❌ {i}/3: 실패 - {result.message}")

    print(f"\n📈 배치 처리 결과:")
    print(f"   - 성공한 커밋: {successful}/{len(commits_to_store)}")
    print(f"   - 총 파일 수: {total_files}")
    print(f"   - 총 변경: +{total_additions}/-{total_deletions}")
    print()


def demo_compression():
    """압축 기능 데모"""
    print("6️⃣ 압축 기능")
    print("=" * 50)

    manager = DataStorageManager()

    # 큰 diff 데이터 생성
    large_diff_content = b"Sample diff line\n" * 10000  # 약 170KB
    print(f"📏 원본 diff 크기: {len(large_diff_content):,} bytes")

    # 압축 테스트
    compressed = manager._compress_bytes(large_diff_content)
    compression_ratio = len(compressed) / len(large_diff_content)

    print(f"🗜️  압축 후 크기: {len(compressed):,} bytes")
    print(f"📊 압축률: {compression_ratio:.2%}")
    print(
        f"💾 저장 위치: {'DB' if len(compressed) <= 256*1024 else 'S3 (if configured)'}"
    )
    print()


def main():
    """메인 데모 함수"""
    try:
        # 1. 기본 저장
        result = demo_basic_storage()

        if result.success:
            manager = DataStorageManager()

            # 2. 중복 처리
            demo_duplicate_handling(manager)

            # 3. 조회
            demo_commit_retrieval(manager)

            # 4. 여러 커밋 저장
            demo_multiple_commits(manager)

            # 5. 최근 커밋 목록
            demo_recent_commits(manager)

            # 6. 압축 기능
            demo_compression()

        print("🎉 DataStorage MVP 데모 완료!")
        print("\n💡 더 자세한 사용법은 docs/data_storage_mvp_guide.md 를 참조하세요.")

    except Exception as e:
        print(f"❌ 데모 실행 중 오류: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
