"""Git data parsing service for fetching and processing diffs."""

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
    GitDataParserError, InvalidPayloadError, GitHubAPIError,
    DiffParsingError, CommitNotFoundError, NetworkTimeoutError
)
from modules.http_api_client import HTTPAPIClient, Platform

logger = logging.getLogger(__name__)


class DiffProcessorInterface(ABC):
    """DiffAnalyzer 모듈과의 인터페이스 정의 (향후 분리 준비)"""
    
    @abstractmethod
    def parse_file_changes(self, diff_content: bytes, commit_data: Dict[str, Any] = None) -> List[FileChange]:
        """Diff 내용에서 파일별 변경사항 추출"""
        pass
    
    @abstractmethod
    def calculate_diff_stats(self, file_changes: List[FileChange]) -> DiffStats:
        """파일 변경사항으로부터 diff 통계 계산"""
        pass
    
    @abstractmethod
    def detect_file_type(self, filename: str) -> Optional[str]:
        """파일명에서 파일 타입 감지"""
        pass


class DiffAnalyzerAdapter(DiffProcessorInterface):
    """DiffAnalyzer 모듈을 GitDataParser에서 사용하기 위한 어댑터 클래스"""
    
    def __init__(self):
        # DiffAnalyzer 모듈을 지연 로딩으로 가져옴 (순환 import 방지)
        try:
            from modules.diff_analyzer.service import LanguageAnalyzer
            self.language_analyzer = LanguageAnalyzer()
        except ImportError:
            logger.warning("DiffAnalyzer module not available, falling back to basic processing")
            self.language_analyzer = None
        
        # 기본 파일 확장자별 타입 매핑 (fallback)
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
    
    def parse_file_changes(self, diff_content: bytes, commit_data: Dict[str, Any] = None) -> List[FileChange]:
        """Diff 내용에서 파일별 변경사항 추출"""
        if not diff_content:
            return []
        
        try:
            diff_text = diff_content.decode('utf-8', errors='ignore')
        except:
            logger.warning("Failed to decode diff content")
            return []
        
        file_changes = []
        
        # GitHub API에서 가져온 파일 정보가 있으면 우선 사용
        if commit_data and 'files' in commit_data:
            for file_data in commit_data['files']:
                filename = file_data.get('filename', '')
                status = file_data.get('status', 'modified')
                additions = file_data.get('additions', 0)
                deletions = file_data.get('deletions', 0)
                patch = file_data.get('patch', '')
                
                file_changes.append(FileChange(
                    filename=filename,
                    status=status,
                    additions=additions,
                    deletions=deletions,
                    file_type=self.detect_file_type(filename),
                    patch=patch
                ))
        else:
            # Fallback: diff 텍스트 직접 파싱
            file_changes = self._parse_diff_text(diff_text)
        
        return file_changes
    
    def _parse_diff_text(self, diff_text: str) -> List[FileChange]:
        """Diff 텍스트를 직접 파싱 (Fallback)"""
        file_changes = []
        
        # diff --git a/file b/file 패턴으로 파일 찾기
        file_headers = re.findall(r'diff --git a/(.*?) b/(.*?)(?:\n|$)', diff_text, re.MULTILINE)
        
        for old_file, new_file in file_headers:
            filename = new_file
            
            # 각 파일별 diff 섹션 추출
            file_section_pattern = rf'diff --git a/{re.escape(old_file)} b/{re.escape(new_file)}(.*?)(?=diff --git|\Z)'
            file_match = re.search(file_section_pattern, diff_text, re.DOTALL)
            
            if not file_match:
                continue
                
            file_diff = file_match.group(1)
            
            # 파일 상태 감지
            if 'new file mode' in file_diff:
                status = "added"
            elif 'deleted file mode' in file_diff:
                status = "removed"
            else:
                status = "modified"
            
            # 라인 수 계산
            additions = len(re.findall(r'^\+[^+]', file_diff, re.MULTILINE))
            deletions = len(re.findall(r'^-[^-]', file_diff, re.MULTILINE))
            
            file_changes.append(FileChange(
                filename=filename,
                status=status,
                additions=additions,
                deletions=deletions,
                file_type=self.detect_file_type(filename),
                patch=file_diff.strip()
            ))
        
        return file_changes
    
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
        
        # DiffAnalyzer가 사용 가능하면 해당 기능 사용
        if self.language_analyzer:
            try:
                return self.language_analyzer._detect_language(filename)
            except Exception as e:
                logger.warning(f"DiffAnalyzer language detection failed: {e}")
        
        # Fallback: 기본 확장자 매핑
        path = Path(filename)
        extension = path.suffix.lower()
        return self.file_types.get(extension, 'unknown')


# Backward compatibility: BasicDiffProcessor를 DiffAnalyzerAdapter로 대체
BasicDiffProcessor = DiffAnalyzerAdapter


class GitDataParserService:
    """Service for parsing git webhook data and fetching diffs."""
    
    def __init__(self, http_client: Optional[HTTPAPIClient] = None, 
                 diff_processor: Optional[DiffProcessorInterface] = None):
        self.github_token = os.environ.get("GITHUB_TOKEN")
        
        # DiffProcessor 의존성 주입 (DiffAnalyzer 모듈 통합)
        self.diff_processor = diff_processor or DiffAnalyzerAdapter()
        
        # HTTPAPIClient 의존성 주입
        if http_client:
            self.http_client = http_client
        elif self.github_token:
            self.http_client = HTTPAPIClient(Platform.GITHUB, auth_token=self.github_token)
        else:
            logger.warning("No GitHub token provided. API calls will be limited.")
            self.http_client = HTTPAPIClient(Platform.GITHUB)
    
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
        MVP: GitHub webhook payload를 구조화된 데이터로 변환
        """
        try:
            # 1. Repository 정보 추출
            if "repository" not in payload:
                raise InvalidPayloadError("Missing 'repository' field", missing_fields=["repository"])
            
            repository = payload["repository"]["full_name"]
            ref = payload.get("ref", "")
            pusher = payload.get("pusher", {}).get("name", "unknown")
            
        except KeyError as e:
            raise InvalidPayloadError(f"Missing required field: {e}", missing_fields=[str(e)])
        
        # 2. Commits 정보 파싱
        commits = []
        for commit_data in payload.get("commits", []):
            commit_info = self.extract_commit_info(commit_data)
            commits.append(commit_info)
        
        # 3. Diff 데이터 가져오기 및 파싱
        try:
            diff_data = self.fetch_diff_data(payload, headers)
            
            # GitHub API 응답에서 상세 정보 가져오기
            commit_sha = payload.get("after") or payload.get("checkout_sha")
            commit_detail = self._fetch_commit_detail(repository, commit_sha) if commit_sha else None
            
            # 파일 변경사항 파싱
            file_changes = self.diff_processor.parse_file_changes(
                diff_data.diff_content, 
                commit_detail
            )
            
            # Diff 통계 계산
            diff_stats = self.diff_processor.calculate_diff_stats(file_changes)
            
        except (GitHubAPIError, DiffParsingError) as exc:
            logger.warning("Failed to fetch/parse diff data: %s", exc)
            file_changes = []
            diff_stats = DiffStats()
        except Exception as exc:
            logger.exception("Unexpected error in diff processing: %s", exc)
            file_changes = []
            diff_stats = DiffStats()
        
        return ParsedWebhookData(
            repository=repository,
            ref=ref,
            pusher=pusher,
            commits=commits,
            file_changes=file_changes,
            diff_stats=diff_stats,
            timestamp=datetime.utcnow()
        )
    
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
    
    def fetch_diff_data(self, payload: Dict[str, Any], headers: Dict[str, str]) -> DiffData:
        """Fetch diff data from GitHub API."""
        
        platform = "github" if "x-github-event" in {k.lower() for k in headers} else "gitlab"
        
        if platform == "github":
            return self._fetch_github_diff(payload)
        else:
            raise NotImplementedError(f"Platform '{platform}' not implemented yet")
    
    def _fetch_github_diff(self, payload: Dict[str, Any]) -> DiffData:
        """Fetch diff from GitHub Commits API using HTTPAPIClient."""
        
        repo = payload["repository"]["full_name"]
        commit_sha = payload.get("after") or payload.get("checkout_sha")
        
        if not commit_sha:
            raise InvalidPayloadError("No commit SHA found in payload")
        
        try:
            # HTTPAPIClient를 사용하여 커밋 정보 가져오기
            endpoint = f"/repos/{repo}/commits/{commit_sha}"
            response = self.http_client.get(endpoint)
            
            if not response.success:
                raise GitHubAPIError(
                    f"Failed to fetch commit data: {response.error}",
                    status_code=response.status_code
                )
            
            data = response.data
            stats = data.get("stats", {})
            
            # Try to get patch format for diff content
            diff_content = b""
            try:
                patch_response = self.http_client.get(endpoint + ".patch")
                if patch_response.success and hasattr(patch_response, 'raw_content'):
                    diff_content = patch_response.raw_content
                else:
                    # Fallback: construct diff from files in the commit data
                    files = data.get("files", [])
                    if files:
                        diff_parts = []
                        for file_data in files:
                            if "patch" in file_data:
                                diff_parts.append(f"--- a/{file_data['filename']}")
                                diff_parts.append(f"+++ b/{file_data['filename']}")
                                diff_parts.append(file_data["patch"])
                        diff_content = "\n".join(diff_parts).encode("utf-8")
            except Exception as patch_exc:
                logger.warning("Failed to fetch patch format: %s", patch_exc)
                # Use files data as fallback
                files = data.get("files", [])
                if files:
                    diff_parts = []
                    for file_data in files:
                        if "patch" in file_data:
                            diff_parts.append(f"--- a/{file_data['filename']}")
                            diff_parts.append(f"+++ b/{file_data['filename']}")
                            diff_parts.append(file_data["patch"])
                    diff_content = "\n".join(diff_parts).encode("utf-8")
            
            return DiffData(
                commit_sha=commit_sha,
                repository=repo,
                diff_content=diff_content,
                added_lines=stats.get("additions", 0),
                deleted_lines=stats.get("deletions", 0),
                files_changed=stats.get("total", 0),
                stats=stats,
            )
                
        except GitHubAPIError:
            raise  # Re-raise GitHubAPIError as is
        except Exception as exc:
            logger.exception("Failed to fetch GitHub diff: %s", exc)
            raise GitDataParserError(f"Failed to fetch GitHub diff: {exc}")
    
    def _fetch_commit_detail(self, repository: str, commit_sha: str) -> Optional[Dict[str, Any]]:
        """GitHub API에서 커밋 상세 정보 가져오기 (파일 목록 포함) - HTTPAPIClient 사용"""
        try:
            endpoint = f"/repos/{repository}/commits/{commit_sha}"
            response = self.http_client.get(endpoint)
            
            if response.success:
                return response.data
            else:
                logger.warning("Failed to fetch commit detail: %s", response.error)
                return None
                
        except Exception as exc:
            logger.warning("Failed to fetch commit detail: %s", exc)
            return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse ISO timestamp string to datetime."""
        if not timestamp_str:
            return datetime.utcnow()
        
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse timestamp '%s': %s", timestamp_str, e)
            return datetime.utcnow() 