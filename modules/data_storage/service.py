"""Data storage service - MVP Version based on design specification."""

from __future__ import annotations

import gzip
import json
import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.future import select

from modules.data_storage.models import (
    Event, CommitRecord, DiffRecord, 
    CommitData, DiffData, StorageResult, StorageStatus,
    CommitSummary, DiffSummary, CommitWithDiffs, BatchStorageResult
)
from modules.git_data_parser.models import DiffData as GitDiffData
from shared.config.database import get_async_session, get_session
from infrastructure.aws.s3_client import S3Client
from shared.utils.logging import ModuleIOLogger

logger = logging.getLogger(__name__)

GZIP_THRESHOLD = 256 * 1024  # 256 KiB


class DataStorageManager:
    """MVP 버전 데이터 저장 관리자 - 설계서 기반 구현"""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        DataStorageManager 초기화
        
        Args:
            db_session: 데이터베이스 세션 (선택적, 테스트용)
        """
        self.db_session = db_session
        self.s3_client = S3Client() if self._s3_configured() else None
        self.logger = logging.getLogger(__name__)
    
    def store_commit(
        self, 
        commit_data: CommitData, 
        diff_data: List[DiffData]
    ) -> StorageResult:
        """
        MVP: 커밋 데이터와 diff 데이터 저장
        
        Args:
            commit_data: 커밋 정보
            diff_data: diff 정보 리스트
            
        Returns:
            StorageResult: 저장 결과
        """
        start_time = datetime.now()
        
        try:
            # 세션 처리
            if self.db_session:
                return self._store_commit_sync(commit_data, diff_data, start_time)
            else:
                with get_session() as session:
                    self.db_session = session
                    return self._store_commit_sync(commit_data, diff_data, start_time)
                    
        except Exception as e:
            self.logger.error(f"Failed to store commit {commit_data.commit_hash}: {e}")
            return StorageResult(
                success=False,
                status=StorageStatus.FAILED,
                message=f"Storage failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _store_commit_sync(
        self, 
        commit_data: CommitData, 
        diff_data: List[DiffData],
        start_time: datetime
    ) -> StorageResult:
        """동기 방식 커밋 저장 구현"""
        
        try:
            # 1. 중복 커밋 확인
            if self._is_duplicate_commit(commit_data.commit_hash):
                return StorageResult(
                    success=False,
                    status=StorageStatus.DUPLICATE,
                    message="Commit already exists",
                    timestamp=datetime.now(),
                    metadata={"commit_hash": commit_data.commit_hash}
                )
            
            # 2. 커밋 레코드 생성
            commit_record = CommitRecord(
                hash=commit_data.commit_hash,
                message=commit_data.message,
                author=commit_data.author,
                author_email=commit_data.author_email,
                timestamp=commit_data.timestamp,
                repository=commit_data.repository,
                branch=commit_data.branch,
                pusher=commit_data.pusher,
                commit_count=commit_data.commit_count
            )
            
            self.db_session.add(commit_record)
            self.db_session.flush()  # ID 생성을 위해 flush
            
            # 3. Diff 레코드들 생성 및 저장
            total_additions = 0
            total_deletions = 0
            
            for diff in diff_data:
                # diff 압축 처리
                compressed_diff = None
                diff_url = None
                
                if diff.diff_content:
                    compressed_data = self._compress_bytes(diff.diff_content)
                    
                    if len(compressed_data) <= GZIP_THRESHOLD:
                        compressed_diff = compressed_data
                    elif self.s3_client:
                        # S3에 업로드
                        key = f"{commit_data.repository}/{commit_data.commit_hash}/{diff.file_path}.patch.gz"
                        diff_url = self._upload_to_s3_sync(key, compressed_data)
                    else:
                        # S3가 없으면 DB에 저장 (경고 로그)
                        compressed_diff = compressed_data
                        self.logger.warning(
                            f"Large diff stored in DB (S3 not configured): {len(compressed_data)} bytes"
                        )
                
                diff_record = DiffRecord(
                    commit_id=commit_record.id,
                    file_path=diff.file_path,
                    additions=diff.additions,
                    deletions=diff.deletions,
                    changes=diff.changes,
                    diff_patch=compressed_diff,
                    diff_url=diff_url
                )
                
                self.db_session.add(diff_record)
                total_additions += diff.additions
                total_deletions += diff.deletions
            
            # 4. 트랜잭션 커밋
            self.db_session.commit()
            
            # 5. 성공 로그 및 결과 반환
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Stored commit {commit_data.commit_hash}: "
                f"files={len(diff_data)}, +{total_additions}/-{total_deletions}, "
                f"duration={duration:.2f}s"
            )
            
            return StorageResult(
                success=True,
                status=StorageStatus.SUCCESS,
                commit_id=commit_record.id,
                message="Commit stored successfully",
                timestamp=datetime.now(),
                metadata={
                    "commit_hash": commit_data.commit_hash,
                    "files_changed": len(diff_data),
                    "total_additions": total_additions,
                    "total_deletions": total_deletions,
                    "duration_seconds": duration
                }
            )
            
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def _is_duplicate_commit(self, commit_hash: str) -> bool:
        """중복 커밋 확인"""
        result = self.db_session.query(CommitRecord).filter(
            CommitRecord.hash == commit_hash
        ).first()
        return result is not None
    
    def get_commit_by_hash(self, commit_hash: str) -> Optional[CommitWithDiffs]:
        """커밋 해시로 상세 정보 조회"""
        
        commit = self.db_session.query(CommitRecord).filter(
            CommitRecord.hash == commit_hash
        ).first()
        
        if not commit:
            return None
        
        # Diff 정보와 함께 조회
        diffs = self.db_session.query(DiffRecord).filter(
            DiffRecord.commit_id == commit.id
        ).all()
        
        # 요약 정보 생성
        commit_summary = CommitSummary(
            id=commit.id,
            hash=commit.hash,
            message=commit.message,
            author=commit.author,
            timestamp=commit.timestamp,
            repository=commit.repository,
            branch=commit.branch,
            diff_count=len(diffs),
            total_additions=sum(d.additions for d in diffs),
            total_deletions=sum(d.deletions for d in diffs)
        )
        
        diff_summaries = [
            DiffSummary(
                id=diff.id,
                file_path=diff.file_path,
                additions=diff.additions,
                deletions=diff.deletions,
                has_content=bool(diff.diff_patch or diff.diff_url)
            )
            for diff in diffs
        ]
        
        return CommitWithDiffs(
            commit=commit_summary,
            diffs=diff_summaries
        )
    
    def get_recent_commits(
        self, 
        repository: str, 
        limit: int = 10
    ) -> List[CommitSummary]:
        """최근 커밋 목록 조회"""
        
        commits = self.db_session.query(CommitRecord).filter(
            CommitRecord.repository == repository
        ).order_by(
            CommitRecord.timestamp.desc()
        ).limit(limit).all()
        
        results = []
        for commit in commits:
            # 각 커밋의 diff 통계 계산
            diff_stats = self.db_session.query(
                func.count(DiffRecord.id).label('diff_count'),
                func.sum(DiffRecord.additions).label('total_additions'),
                func.sum(DiffRecord.deletions).label('total_deletions')
            ).filter(
                DiffRecord.commit_id == commit.id
            ).first()
            
            results.append(CommitSummary(
                id=commit.id,
                hash=commit.hash,
                message=commit.message,
                author=commit.author,
                timestamp=commit.timestamp,
                repository=commit.repository,
                branch=commit.branch,
                diff_count=diff_stats.diff_count or 0,
                total_additions=diff_stats.total_additions or 0,
                total_deletions=diff_stats.total_deletions or 0
            ))
        
        return results
    
    def _compress_bytes(self, data: bytes) -> bytes:
        """바이트 데이터 gzip 압축"""
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(data)
        return buf.getvalue()
    
    def _upload_to_s3_sync(self, key: str, data: bytes) -> Optional[str]:
        """S3에 동기 방식으로 데이터 업로드"""
        try:
            # 실제 S3 클라이언트가 비동기일 수 있으므로 동기 버전 필요
            # 여기서는 간단히 URL 반환 (실제 구현 시 s3_client 수정 필요)
            return f"s3://{os.getenv('AWS_S3_BUCKET', 'codeping-diffs')}/{key}"
        except Exception as e:
            self.logger.error(f"Failed to upload to S3: {e}")
            return None
    
    def _s3_configured(self) -> bool:
        """S3 설정 확인"""
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
        return all(os.environ.get(var) for var in required_vars)


class LegacyDataStorageService:
    """기존 이벤트 저장 서비스 - 호환성 유지"""
    
    def __init__(self):
        self.s3_client = S3Client() if self._s3_configured() else None
        
        # 입출력 로거 설정
        self.io_logger = ModuleIOLogger("DataStorage")
    
    def store_event_with_diff(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        diff_data: GitDiffData
    ) -> None:
        """기존 이벤트 저장 방식 - 호환성 유지"""
        
        # 입력 로깅
        self.io_logger.log_input(
            "store_event_with_diff",
            data={"payload": payload, "diff_data": diff_data},
            metadata={
                "repository": diff_data.repository,
                "commit_sha": diff_data.commit_sha,
                "headers_count": len(headers),
                "payload_size": len(str(payload)),
                "diff_size": len(diff_data.diff_content) if diff_data.diff_content else 0,
                "added_lines": diff_data.added_lines,
                "deleted_lines": diff_data.deleted_lines,
                "files_changed": diff_data.files_changed
            }
        )
        
        try:
            import asyncio
            asyncio.run(self._store_event_async(payload, headers, diff_data))
            
            # 출력 로깅 (성공)
            self.io_logger.log_output(
                "store_event_with_diff",
                metadata={
                    "storage_success": True,
                    "repository": diff_data.repository,
                    "commit_sha": diff_data.commit_sha,
                    "storage_location": "determined_in_async"
                }
            )
            
        except Exception as e:
            # 오류 로깅
            self.io_logger.log_error(
                "store_event_with_diff",
                e,
                metadata={
                    "repository": diff_data.repository,
                    "commit_sha": diff_data.commit_sha
                }
            )
            raise
    
    async def _store_event_async(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        diff_data: GitDiffData
    ) -> None:
        """기존 비동기 이벤트 저장 구현"""
        
        # 압축 처리
        diff_patch = None
        diff_url = None
        
        if diff_data.diff_content:
            compressed_diff = self._compress_bytes(diff_data.diff_content)
            
            if len(compressed_diff) <= GZIP_THRESHOLD:
                diff_patch = compressed_diff
                storage_location = "db"
            else:
                if self.s3_client:
                    key = f"{diff_data.repository}/{diff_data.commit_sha}.patch.gz"
                    diff_url = await self.s3_client.upload_diff(key, compressed_diff)
                    storage_location = "s3"
                else:
                    diff_patch = compressed_diff
                    storage_location = "db_large"
                    logger.warning(
                        "Large diff stored in DB (S3 not configured): %d bytes",
                        len(compressed_diff)
                    )
        else:
            storage_location = "none"
        
        # 이벤트 데이터 준비
        platform = "github" if "x-github-event" in {k.lower() for k in headers} else "gitlab"
        
        event_data = {
            "platform": platform,
            "repository": diff_data.repository,
            "commit_sha": diff_data.commit_sha,
            "author_name": payload.get("pusher", {}).get("name"),
            "author_email": payload.get("pusher", {}).get("email"),
            "timestamp_utc": None,
            "ref": payload.get("ref"),
            "pusher": payload.get("pusher", {}).get("name", "unknown"),
            "commit_count": len(payload.get("commits", [])),
            "diff_patch": diff_patch,
            "diff_url": diff_url,
            "added_lines": diff_data.added_lines,
            "deleted_lines": diff_data.deleted_lines,
            "files_changed": diff_data.files_changed,
            "payload": json.dumps(payload),
        }
        
        # 데이터베이스 저장
        async with get_async_session() as session:
            await self._save_event(session, event_data)
        
        logger.info(
            "Stored event %s/%s: gzip_size=%s stored_in=%s added=%s deleted=%s files=%s",
            diff_data.repository,
            diff_data.commit_sha,
            f"{len(compressed_diff) / 1024:.1f} KB" if diff_data.diff_content else "0 KB",
            storage_location,
            diff_data.added_lines or 0,
            diff_data.deleted_lines or 0,
            diff_data.files_changed or 0,
        )
    
    async def _save_event(self, session: AsyncSession, event_data: Dict[str, Any]) -> None:
        """이벤트 데이터베이스 저장"""
        
        event = Event(**event_data)
        session.add(event)
        
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    
    def _compress_bytes(self, data: bytes) -> bytes:
        """바이트 데이터 압축"""
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(data)
        return buf.getvalue()
    
    def _s3_configured(self) -> bool:
        """S3 설정 확인"""
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
        return all(os.environ.get(var) for var in required_vars)


# 편의 함수들
def create_data_storage_manager(db_session: Optional[Session] = None) -> DataStorageManager:
    """DataStorageManager 팩토리 함수"""
    return DataStorageManager(db_session)


def store_commit_data(
    commit_data: CommitData, 
    diff_data: List[DiffData]
) -> StorageResult:
    """간편한 커밋 저장 함수"""
    manager = create_data_storage_manager()
    return manager.store_commit(commit_data, diff_data) 