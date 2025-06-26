"""Data storage models for webhook events - MVP Version based on design spec."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, LargeBinary, Integer, 
    UniqueConstraint, ForeignKey, Text, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict

from shared.config.database import Base


class StorageStatus(str, Enum):
    """저장 상태"""
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATE = "duplicate"
    PENDING = "pending"


# SQLAlchemy Models (Database Tables)
class CommitRecord(Base):
    """커밋 정보 테이블 - MVP 버전"""
    
    __tablename__ = "commits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hash = Column(String(40), unique=True, nullable=False, index=True)
    message = Column(Text, nullable=False)
    author = Column(String(255), nullable=False, index=True)
    author_email = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    repository = Column(String(255), nullable=False, index=True)
    branch = Column(String(255), nullable=False)
    pusher = Column(String(255), nullable=True)
    commit_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # 관계 설정
    diffs = relationship("DiffRecord", back_populates="commit", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<CommitRecord(id={self.id}, hash={self.hash[:8]}, repo={self.repository})>"


class DiffRecord(Base):
    """Diff 정보 테이블 - MVP 버전"""
    
    __tablename__ = "commit_diffs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(Text, nullable=False)
    additions = Column(Integer, nullable=False, default=0)
    deletions = Column(Integer, nullable=False, default=0)
    changes = Column(Text, nullable=True)  # diff 내용 (압축된 형태)
    diff_patch = Column(LargeBinary, nullable=True)  # 압축된 diff 데이터
    diff_url = Column(String, nullable=True)  # S3 URL (큰 파일의 경우)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # 관계 설정
    commit = relationship("CommitRecord", back_populates="diffs")
    
    # 인덱스 추가
    __table_args__ = (
        Index('idx_diffs_commit_id', 'commit_id'),
        Index('idx_diffs_file_path', 'file_path'),
    )
    
    def __repr__(self) -> str:
        return f"<DiffRecord(id={self.id}, commit_id={self.commit_id}, file={self.file_path})>"


# Legacy Event Model (기존 호환성 유지)
class Event(Base):
    """Database model for GitHub webhook events - Legacy support."""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False, default="github")
    repository = Column(String, nullable=False, index=True)
    commit_sha = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=True)
    author_email = Column(String, nullable=True)
    timestamp_utc = Column(DateTime, nullable=True)
    ref = Column(String, nullable=True)
    pusher = Column(String, nullable=False, index=True)
    commit_count = Column(Integer, nullable=False, default=1)
    diff_patch = Column(LargeBinary, nullable=True)  # Compressed diff or None if stored in S3
    diff_url = Column(String, nullable=True)  # S3 URL if diff is too large
    added_lines = Column(Integer, nullable=True)
    deleted_lines = Column(Integer, nullable=True)
    files_changed = Column(Integer, nullable=True)
    payload = Column(String, nullable=False)  # JSON string
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Prevent duplicate events
    __table_args__ = (
        UniqueConstraint('repository', 'commit_sha', name='uq_repo_commit'),
    )
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, repo={self.repository}, sha={self.commit_sha[:8]})>"


# Pydantic Models (API Request/Response)
class CommitData(BaseModel):
    """커밋 데이터 입력 모델"""
    
    commit_hash: str
    message: str
    author: str
    author_email: Optional[str] = None
    timestamp: datetime
    repository: str
    branch: str
    pusher: Optional[str] = None
    commit_count: int = 1
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class DiffData(BaseModel):
    """Diff 데이터 입력 모델"""
    
    file_path: str
    additions: int = 0
    deletions: int = 0
    changes: Optional[str] = None
    diff_content: Optional[bytes] = None  # 원본 diff 내용
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class StorageResult(BaseModel):
    """저장 결과 응답 모델"""
    
    success: bool
    status: StorageStatus
    commit_id: Optional[int] = None
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)


class CommitSummary(BaseModel):
    """커밋 요약 정보"""
    
    id: int
    hash: str
    message: str
    author: str
    timestamp: datetime
    repository: str
    branch: str
    diff_count: int
    total_additions: int
    total_deletions: int
    
    model_config = ConfigDict(from_attributes=True)


class DiffSummary(BaseModel):
    """Diff 요약 정보"""
    
    id: int
    file_path: str
    additions: int
    deletions: int
    has_content: bool
    
    model_config = ConfigDict(from_attributes=True)


# Legacy Models (기존 호환성)
class EventCreate(BaseModel):
    """Pydantic model for creating new events."""
    
    repository: str
    commit_sha: str
    event_type: str = "push"
    payload: str
    diff_data: Optional[bytes] = None
    diff_s3_url: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class EventResponse(BaseModel):
    """Pydantic model for event API responses."""
    
    id: int
    repository: str
    commit_sha: str
    event_type: str
    payload: Dict[str, Any]
    diff_s3_url: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Aggregated Models
class CommitWithDiffs(BaseModel):
    """커밋과 관련 Diff 정보를 포함한 집계 모델"""
    
    commit: CommitSummary
    diffs: List[DiffSummary]
    
    model_config = ConfigDict(from_attributes=True)


class BatchStorageResult(BaseModel):
    """배치 저장 결과"""
    
    total_commits: int
    successful_commits: int
    failed_commits: int
    results: List[StorageResult]
    duration_seconds: float
    
    @property
    def success_rate(self) -> float:
        if self.total_commits == 0:
            return 0.0
        return self.successful_commits / self.total_commits
    
    model_config = ConfigDict(from_attributes=True) 