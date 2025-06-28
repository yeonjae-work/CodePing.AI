"""DataStorage MVP 버전 테스트"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.data_storage.models import (
    Base, CommitRecord, DiffRecord,
    CommitData, DiffData, StorageResult, StorageStatus
)
from modules.data_storage.service import DataStorageManager


@pytest.fixture
def db_session():
    """테스트용 인메모리 데이터베이스 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_commit_data():
    """테스트용 커밋 데이터"""
    return CommitData(
        commit_hash="abc123def456",
        message="Add new feature for MVP testing",
        author="test@example.com",
        author_email="test@example.com",
        timestamp=datetime.now(timezone.utc),
        repository="test-org/test-repo",
        branch="main",
        pusher="test-user",
        commit_count=1
    )


@pytest.fixture
def sample_diff_data():
    """테스트용 diff 데이터"""
    return [
        DiffData(
            file_path="src/main.py",
            additions=10,
            deletions=5,
            changes="Added new function\nRemoved old code",
            diff_content=b"diff --git a/src/main.py b/src/main.py\n+new code\n-old code"
        ),
        DiffData(
            file_path="tests/test_main.py",
            additions=15,
            deletions=2,
            changes="Added test cases",
            diff_content=b"diff --git a/tests/test_main.py b/tests/test_main.py\n+test code"
        )
    ]


class TestDataStorageManager:
    """DataStorageManager MVP 버전 테스트"""

    def test_store_commit_success(self, db_session, sample_commit_data, sample_diff_data):
        """커밋 저장 성공 테스트"""
        storage = DataStorageManager(db_session)

        result = storage.store_commit(sample_commit_data, sample_diff_data)

        # 결과 검증
        assert result.success is True
        assert result.status == StorageStatus.SUCCESS
        assert result.commit_id is not None
        assert result.message == "Commit stored successfully"
        assert "commit_hash" in result.metadata
        assert result.metadata["files_changed"] == 2
        assert result.metadata["total_additions"] == 25
        assert result.metadata["total_deletions"] == 7

        # 데이터베이스 확인
        commit = db_session.query(CommitRecord).filter(
            CommitRecord.hash == sample_commit_data.commit_hash
        ).first()
        assert commit is not None
        assert commit.message == sample_commit_data.message
        assert commit.author == sample_commit_data.author
        assert commit.repository == sample_commit_data.repository

        # Diff 레코드 확인
        diffs = db_session.query(DiffRecord).filter(
            DiffRecord.commit_id == commit.id
        ).all()
        assert len(diffs) == 2
        assert diffs[0].file_path == "src/main.py"
        assert diffs[0].additions == 10
        assert diffs[0].deletions == 5
        assert diffs[1].file_path == "tests/test_main.py"
        assert diffs[1].additions == 15
        assert diffs[1].deletions == 2

    def test_store_duplicate_commit(self, db_session, sample_commit_data, sample_diff_data):
        """중복 커밋 저장 테스트"""
        storage = DataStorageManager(db_session)

        # 첫 번째 저장
        result1 = storage.store_commit(sample_commit_data, sample_diff_data)
        assert result1.success is True

        # 같은 커밋 해시로 다시 저장 시도
        result2 = storage.store_commit(sample_commit_data, sample_diff_data)

        # 중복 검증
        assert result2.success is False
        assert result2.status == StorageStatus.DUPLICATE
        assert result2.message == "Commit already exists"
        assert "commit_hash" in result2.metadata

        # 데이터베이스에는 하나만 존재
        commits = db_session.query(CommitRecord).filter(
            CommitRecord.hash == sample_commit_data.commit_hash
        ).all()
        assert len(commits) == 1

    def test_get_commit_by_hash(self, db_session, sample_commit_data, sample_diff_data):
        """커밋 해시로 조회 테스트"""
        storage = DataStorageManager(db_session)

        # 커밋 저장
        result = storage.store_commit(sample_commit_data, sample_diff_data)
        assert result.success is True

        # 해시로 조회
        commit_with_diffs = storage.get_commit_by_hash(sample_commit_data.commit_hash)

        # 조회 결과 검증
        assert commit_with_diffs is not None
        assert commit_with_diffs.commit.hash == sample_commit_data.commit_hash
        assert commit_with_diffs.commit.message == sample_commit_data.message
        assert commit_with_diffs.commit.author == sample_commit_data.author
        assert commit_with_diffs.commit.diff_count == 2
        assert commit_with_diffs.commit.total_additions == 25
        assert commit_with_diffs.commit.total_deletions == 7

        # Diff 정보 검증
        assert len(commit_with_diffs.diffs) == 2
        diff1 = commit_with_diffs.diffs[0]
        assert diff1.file_path == "src/main.py"
        assert diff1.additions == 10
        assert diff1.deletions == 5
        assert diff1.has_content is True

    def test_get_commit_by_hash_not_found(self, db_session):
        """존재하지 않는 커밋 해시 조회 테스트"""
        storage = DataStorageManager(db_session)

        result = storage.get_commit_by_hash("nonexistent-hash")

        assert result is None

    def test_get_recent_commits(self, db_session):
        """최근 커밋 목록 조회 테스트"""
        storage = DataStorageManager(db_session)

        # 여러 커밋 저장
        commits_data = []
        for i in range(3):
            commit_data = CommitData(
                commit_hash=f"hash{i}",
                message=f"Commit {i}",
                author="test@example.com",
                timestamp=datetime.now(timezone.utc),
                repository="test-org/test-repo",
                branch="main"
            )
            diff_data = [DiffData(
                file_path=f"file{i}.py",
                additions=i + 1,
                deletions=i,
                changes=f"Changes {i}"
            )]

            result = storage.store_commit(commit_data, diff_data)
            assert result.success is True
            commits_data.append(commit_data)

        # 최근 커밋 조회
        recent_commits = storage.get_recent_commits("test-org/test-repo", limit=5)

        # 결과 검증 (최신순으로 정렬됨)
        assert len(recent_commits) == 3
        assert recent_commits[0].hash == "hash2"  # 가장 최근
        assert recent_commits[1].hash == "hash1"
        assert recent_commits[2].hash == "hash0"  # 가장 오래된

        # 각 커밋의 통계 정보 확인
        for i, commit in enumerate(recent_commits):
            expected_idx = 2 - i  # 역순
            assert commit.diff_count == 1
            assert commit.total_additions == expected_idx + 1
            assert commit.total_deletions == expected_idx

    def test_store_commit_without_diff_content(self, db_session):
        """diff 내용 없이 커밋 저장 테스트"""
        storage = DataStorageManager(db_session)

        commit_data = CommitData(
            commit_hash="no-diff-hash",
            message="Commit without diff content",
            author="test@example.com",
            timestamp=datetime.now(timezone.utc),
            repository="test-org/test-repo",
            branch="main"
        )

        diff_data = [DiffData(
            file_path="empty.py",
            additions=0,
            deletions=0,
            changes=None,
            diff_content=None  # diff 내용 없음
        )]

        result = storage.store_commit(commit_data, diff_data)

        # 저장 성공 확인
        assert result.success is True
        assert result.status == StorageStatus.SUCCESS

        # 데이터베이스 확인
        commit = db_session.query(CommitRecord).filter(
            CommitRecord.hash == "no-diff-hash"
        ).first()
        assert commit is not None

        diff = db_session.query(DiffRecord).filter(
            DiffRecord.commit_id == commit.id
        ).first()
        assert diff is not None
        assert diff.diff_patch is None
        assert diff.diff_url is None

    def test_compress_bytes(self, db_session):
        """바이트 압축 기능 테스트"""
        storage = DataStorageManager(db_session)

        original_data = b"This is a test data for compression" * 100
        compressed_data = storage._compress_bytes(original_data)

        # 압축된 데이터가 원본보다 작은지 확인
        assert len(compressed_data) < len(original_data)
        assert len(compressed_data) > 0

        # gzip 헤더 확인 (첫 두 바이트가 0x1f, 0x8b)
        assert compressed_data[0] == 0x1f
        assert compressed_data[1] == 0x8b


class TestStorageIntegration:
    """DataStorage 통합 테스트"""

    def test_full_workflow(self, db_session):
        """전체 워크플로우 통합 테스트"""
        storage = DataStorageManager(db_session)

        # 1. 커밋 저장
        commit_data = CommitData(
            commit_hash="integration-test-hash",
            message="Integration test commit",
            author="integration@example.com",
            timestamp=datetime.now(timezone.utc),
            repository="integration/repo",
            branch="feature/integration"
        )

        diff_data = [
            DiffData(
                file_path="src/integration.py",
                additions=20,
                deletions=5,
                changes="Integration test changes",
                diff_content=b"diff content for integration test"
            )
        ]

        # 저장
        store_result = storage.store_commit(commit_data, diff_data)
        assert store_result.success is True

        # 2. 저장된 커밋 조회
        retrieved_commit = storage.get_commit_by_hash("integration-test-hash")
        assert retrieved_commit is not None
        assert retrieved_commit.commit.message == "Integration test commit"
        assert retrieved_commit.commit.author == "integration@example.com"
        assert len(retrieved_commit.diffs) == 1

        # 3. 최근 커밋 목록에서 확인
        recent_commits = storage.get_recent_commits("integration/repo")
        assert len(recent_commits) == 1
        assert recent_commits[0].hash == "integration-test-hash"

        # 4. 중복 저장 시도
        duplicate_result = storage.store_commit(commit_data, diff_data)
        assert duplicate_result.success is False
        assert duplicate_result.status == StorageStatus.DUPLICATE

        # 5. 여전히 하나만 존재하는지 확인
        final_commits = storage.get_recent_commits("integration/repo")
        assert len(final_commits) == 1
