"""
HTTPAPIClient 모듈의 예외 클래스 정의
"""

from typing import Optional, Dict, Any


class APIError(Exception):
    """API 호출 관련 기본 예외"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        platform: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        self.platform = platform
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform:
            parts.append(f"Platform: {self.platform}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)


class RateLimitError(APIError):
    """Rate Limit 초과 예외"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        remaining: int = 0,
        reset_time: Optional[int] = None,
        platform: Optional[str] = None
    ):
        super().__init__(message, 429, platform=platform)
        self.retry_after = retry_after
        self.remaining = remaining
        self.reset_time = reset_time
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform:
            parts.append(f"Platform: {self.platform}")
        if self.retry_after:
            parts.append(f"Retry after: {self.retry_after}s")
        if self.remaining is not None:
            parts.append(f"Remaining: {self.remaining}")
        return " | ".join(parts)


class AuthenticationError(APIError):
    """인증 관련 예외"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        platform: Optional[str] = None
    ):
        super().__init__(message, 401, platform=platform)


class AuthorizationError(APIError):
    """권한 관련 예외"""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        platform: Optional[str] = None
    ):
        super().__init__(message, 403, platform=platform)


class NotFoundError(APIError):
    """리소스를 찾을 수 없음 예외"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        platform: Optional[str] = None
    ):
        super().__init__(message, 404, platform=platform)


class ServerError(APIError):
    """서버 에러 예외"""
    
    def __init__(
        self,
        message: str = "Internal server error",
        status_code: int = 500,
        platform: Optional[str] = None
    ):
        super().__init__(message, status_code, platform=platform)


class NetworkError(APIError):
    """네트워크 관련 예외"""
    
    def __init__(
        self,
        message: str = "Network error occurred",
        platform: Optional[str] = None
    ):
        super().__init__(message, platform=platform)


class TimeoutError(APIError):
    """타임아웃 예외"""
    
    def __init__(
        self,
        message: str = "Request timeout",
        timeout: Optional[float] = None,
        platform: Optional[str] = None
    ):
        super().__init__(message, platform=platform)
        self.timeout = timeout
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform:
            parts.append(f"Platform: {self.platform}")
        if self.timeout:
            parts.append(f"Timeout: {self.timeout}s")
        return " | ".join(parts)


class ValidationError(APIError):
    """데이터 검증 예외"""
    
    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        super().__init__(message)
        self.field = field
        self.value = value
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {self.value}")
        return " | ".join(parts)


class CacheError(APIError):
    """캐시 관련 예외"""
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        operation: Optional[str] = None
    ):
        super().__init__(message)
        self.operation = operation
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        return " | ".join(parts)


class PlatformNotSupportedError(APIError):
    """지원하지 않는 플랫폼 예외"""
    
    def __init__(
        self,
        platform: str,
        supported_platforms: Optional[list] = None
    ):
        message = f"Platform '{platform}' is not supported"
        super().__init__(message, platform=platform)
        self.supported_platforms = supported_platforms or []
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.supported_platforms:
            parts.append(f"Supported: {', '.join(self.supported_platforms)}")
        return " | ".join(parts)


def handle_http_error(status_code: int, message: str, platform: Optional[str] = None) -> APIError:
    """HTTP 상태 코드에 따른 적절한 예외 반환"""
    if status_code == 401:
        return AuthenticationError(message, platform)
    elif status_code == 403:
        return AuthorizationError(message, platform)
    elif status_code == 404:
        return NotFoundError(message, platform)
    elif status_code == 429:
        return RateLimitError(message, platform=platform)
    elif 500 <= status_code < 600:
        return ServerError(message, status_code, platform)
    else:
        return APIError(message, status_code, platform=platform) 