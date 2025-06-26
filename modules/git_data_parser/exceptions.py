"""GitDataParser 모듈 예외 정의"""

from typing import Optional, Dict, Any


class GitDataParserError(Exception):
    """GitDataParser 모듈 기본 예외"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class InvalidPayloadError(GitDataParserError):
    """잘못된 페이로드 구조"""
    
    def __init__(self, message: str = "Invalid payload structure", missing_fields: Optional[list] = None):
        details = {"missing_fields": missing_fields} if missing_fields else {}
        super().__init__(message, details)


class GitHubAPIError(GitDataParserError):
    """GitHub API 호출 실패"""
    
    def __init__(self, message: str = "GitHub API call failed", status_code: Optional[int] = None, 
                 api_response: Optional[Dict[str, Any]] = None):
        details = {}
        if status_code:
            details["status_code"] = status_code
        if api_response:
            details["api_response"] = api_response
        super().__init__(message, details)


class DiffParsingError(GitDataParserError):
    """Diff 파싱 오류"""
    
    def __init__(self, message: str = "Failed to parse diff content", diff_size: Optional[int] = None):
        details = {"diff_size": diff_size} if diff_size else {}
        super().__init__(message, details)


class CommitNotFoundError(GitDataParserError):
    """커밋 정보를 찾을 수 없음"""
    
    def __init__(self, commit_sha: str, repository: Optional[str] = None):
        message = f"Commit not found: {commit_sha}"
        details = {"commit_sha": commit_sha}
        if repository:
            details["repository"] = repository
        super().__init__(message, details)


class UnsupportedPlatformError(GitDataParserError):
    """지원하지 않는 플랫폼"""
    
    def __init__(self, platform: str):
        message = f"Unsupported platform: {platform}"
        details = {"platform": platform}
        super().__init__(message, details)


class TimestampParsingError(GitDataParserError):
    """타임스탬프 파싱 오류"""
    
    def __init__(self, timestamp_str: str):
        message = f"Failed to parse timestamp: {timestamp_str}"
        details = {"timestamp": timestamp_str}
        super().__init__(message, details)


class FileTooLargeError(GitDataParserError):
    """파일 크기 초과"""
    
    def __init__(self, filename: str, size: int, max_size: int):
        message = f"File too large: {filename} ({size} bytes, max: {max_size})"
        details = {"filename": filename, "size": size, "max_size": max_size}
        super().__init__(message, details)


class NetworkTimeoutError(GitDataParserError):
    """네트워크 타임아웃"""
    
    def __init__(self, url: str, timeout: int):
        message = f"Network timeout for {url} (timeout: {timeout}s)"
        details = {"url": url, "timeout": timeout}
        super().__init__(message, details)


class RateLimitExceededError(GitDataParserError):
    """API 요청 제한 초과"""
    
    def __init__(self, reset_time: Optional[str] = None):
        message = "API rate limit exceeded"
        details = {"reset_time": reset_time} if reset_time else {}
        super().__init__(message, details) 