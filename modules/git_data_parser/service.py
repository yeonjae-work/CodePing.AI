"""Git data parsing service for processing webhook payloads (parsing only)."""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

import re
from pathlib import Path

from modules.git_data_parser.models import (
    ValidatedEvent, GitCommit, DiffData, 
    ParsedWebhookData, CommitInfo, Author, FileChange, DiffStats
)
from modules.git_data_parser.exceptions import (
    GitDataParserError, InvalidPayloadError, DiffParsingError
)
from shared.utils.logging import ModuleIOLogger

logger = logging.getLogger(__name__)


class GitDataParserService:
    """Service for parsing git webhook data - 순수 파싱만 담당 (API 호출 없음)"""
    
    def __init__(self):
        # 기본 파일 확장자별 타입 매핑
        self.file_types = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text',
        }
        
        # 입출력 로거 설정
        self.io_logger = ModuleIOLogger("GitDataParser")
    
    def parse_github_push(self, headers: Dict[str, str], payload: Dict[str, Any]) -> ValidatedEvent:
        """Parse GitHub push webhook payload into ValidatedEvent."""
        
        repository = payload["repository"]["full_name"]
        ref = payload.get("ref", "")
        pusher = payload.get("pusher", {}).get("name", "unknown")
        
        # Parse commits
        commits = []
        for commit_data in payload.get("commits", []):
            commit = GitCommit(
                id=commit_data["id"],
                message=commit_data.get("message", ""),
                url=commit_data.get("url", ""),
                author=commit_data.get("author", {}).get("name"),
                timestamp=self._parse_timestamp(commit_data.get("timestamp")),
                added=commit_data.get("added", []),
                removed=commit_data.get("removed", []),
                modified=commit_data.get("modified", []),
            )
            commits.append(commit)
        
        return ValidatedEvent(
            repository=repository,
            ref=ref,
            pusher=pusher,
            commits=commits,
            timestamp=datetime.utcnow(),
        )
    
    def parse_webhook_data(self, payload: Dict[str, Any], headers: Dict[str, str]) -> ParsedWebhookData:
        """
        GitHub webhook payload를 구조화된 데이터로 변환 (순수 파싱, API 호출 없음)
        """
        # 입력 로깅
        self.io_logger.log_input(
            "parse_webhook_data",
            data=payload,
            metadata={
                "headers_count": len(headers),
                "payload_size": len(str(payload)),
                "repository": payload.get("repository", {}).get("full_name", "unknown"),
                "commits_count": len(payload.get("commits", []))
            }
        )
        
        try:
            # 1. Repository 정보 추출
            if "repository" not in payload:
                raise InvalidPayloadError("Missing 'repository' field", missing_fields=["repository"])
            
            repository = payload["repository"]["full_name"]
            ref = payload.get("ref", "")
            pusher = payload.get("pusher", {}).get("name", "unknown")
            
        except KeyError as e:
            error = InvalidPayloadError(f"Missing required field: {e}", missing_fields=[str(e)])
            self.io_logger.log_error(
                "parse_webhook_data",
                error,
                metadata={"missing_field": str(e)}
            )
            raise error
        
        try:
            # 2. Commits 정보 파싱
            commits = []
            for commit_data in payload.get("commits", []):
                commit_info = self.extract_commit_info(commit_data)
                commits.append(commit_info)
            
            # 3. 파일 변경사항 직접 추출 (webhook payload에서)
            file_changes = self.extract_file_changes_from_payload(payload)
            
            # 4. Diff 통계 계산
            diff_stats = self.calculate_diff_stats(file_changes)
            
            result = ParsedWebhookData(
                repository=repository,
                ref=ref,
                pusher=pusher,
                commits=commits,
                file_changes=file_changes,
                diff_stats=diff_stats,
                timestamp=datetime.utcnow()
            )
            
            # 출력 로깅
            self.io_logger.log_output(
                "parse_webhook_data",
                data=result,
                metadata={
                    "repository": repository,
                    "commits_parsed": len(commits),
                    "files_changed": diff_stats.files_changed,
                    "total_additions": diff_stats.total_additions,
                    "total_deletions": diff_stats.total_deletions,
                    "file_types": list(set(fc.file_type for fc in file_changes if fc.file_type))
                }
            )
            
            logger.info(
                "✅ GitDataParser: Parsed webhook data - repo=%s, commits=%d, files=%d (+%d/-%d)",
                repository, len(commits), diff_stats.files_changed, 
                diff_stats.total_additions, diff_stats.total_deletions
            )
            
            return result
            
        except Exception as e:
            self.io_logger.log_error(
                "parse_webhook_data",
                e,
                metadata={
                    "repository": repository if 'repository' in locals() else "unknown",
                    "error_type": type(e).__name__
                }
            )
            raise
    
    def extract_commit_info(self, commit_data: Dict[str, Any]) -> CommitInfo:
        """개별 커밋 정보 추출"""
        author_data = commit_data.get("author", {})
        
        author = Author(
            name=author_data.get("name", "Unknown"),
            email=author_data.get("email", "unknown@example.com"),
            username=author_data.get("username")
        )
        
        return CommitInfo(
            sha=commit_data["id"],
            message=commit_data.get("message", ""),
            author=author,
            timestamp=self._parse_timestamp(commit_data.get("timestamp")),
            url=commit_data.get("url", "")
        )
    
    def extract_file_changes_from_payload(self, payload: Dict[str, Any]) -> List[FileChange]:
        """
        Webhook payload에서 직접 파일 변경사항 추출
        (API 호출 없이 webhook 정보만 사용)
        """
        file_changes = []
        
        # 모든 커밋의 파일 변경사항 수집
        for commit_data in payload.get("commits", []):
            
            # 추가된 파일들
            for filename in commit_data.get("added", []):
                file_changes.append(FileChange(
                    filename=filename,
                    status="added",
                    additions=0,  # webhook에는 정확한 라인 수 없음
                    deletions=0,
                    file_type=self.detect_file_type(filename),
                    patch=None  # webhook에는 실제 patch 내용 없음
                ))
            
            # 삭제된 파일들
            for filename in commit_data.get("removed", []):
                file_changes.append(FileChange(
                    filename=filename,
                    status="removed",
                    additions=0,
                    deletions=0,  # webhook에는 정확한 라인 수 없음
                    file_type=self.detect_file_type(filename),
                    patch=None
                ))
            
            # 수정된 파일들
            for filename in commit_data.get("modified", []):
                file_changes.append(FileChange(
                    filename=filename,
                    status="modified",
                    additions=0,  # webhook에는 정확한 라인 수 없음
                    deletions=0,
                    file_type=self.detect_file_type(filename),
                    patch=None
                ))
        
        # 중복 파일 제거 (여러 커밋에서 같은 파일이 변경된 경우)
        unique_files = {}
        for file_change in file_changes:
            key = file_change.filename
            if key not in unique_files:
                unique_files[key] = file_change
            else:
                # 우선순위: removed > added > modified
                if file_change.status == "removed":
                    unique_files[key] = file_change
                elif file_change.status == "added" and unique_files[key].status == "modified":
                    unique_files[key] = file_change
        
        return list(unique_files.values())
    
    def calculate_diff_stats(self, file_changes: List[FileChange]) -> DiffStats:
        """파일 변경사항으로부터 diff 통계 계산"""
        total_additions = sum(fc.additions for fc in file_changes)
        total_deletions = sum(fc.deletions for fc in file_changes)
        files_changed = len(file_changes)
        
        files_added = len([fc for fc in file_changes if fc.status == "added"])
        files_modified = len([fc for fc in file_changes if fc.status == "modified"])
        files_removed = len([fc for fc in file_changes if fc.status == "removed"])
        
        return DiffStats(
            total_additions=total_additions,
            total_deletions=total_deletions,
            files_changed=files_changed,
            files_added=files_added,
            files_modified=files_modified,
            files_removed=files_removed
        )
    
    def detect_file_type(self, filename: str) -> Optional[str]:
        """파일명에서 파일 타입 감지"""
        if not filename:
            return None
        
        # 기본 확장자 매핑
        path = Path(filename)
        extension = path.suffix.lower()
        return self.file_types.get(extension, 'unknown')
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse ISO timestamp string to datetime."""
        if not timestamp_str:
            return datetime.utcnow()
        
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse timestamp '%s': %s", timestamp_str, e)
            return datetime.utcnow() 