"""
HTTPAPIClient 모듈의 데이터 모델 정의
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from enum import Enum


class HTTPMethod(Enum):
    """HTTP 메서드 정의"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class Platform(Enum):
    """지원하는 플랫폼 정의"""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    GENERIC = "generic"


@dataclass
class PlatformConfig:
    """플랫폼별 설정"""
    name: str
    base_url: str
    auth_header: str
    auth_prefix: str = ""
    rate_limit_per_hour: int = 5000
    rate_limit_per_minute: Optional[int] = None
    default_headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    
    def get_auth_header(self, token: str) -> Dict[str, str]:
        """인증 헤더 생성"""
        if self.auth_prefix:
            auth_value = f"{self.auth_prefix} {token}"
        else:
            auth_value = token
        return {self.auth_header: auth_value}


@dataclass
class APIRequest:
    """API 요청 정보"""
    platform: Platform
    method: HTTPMethod
    endpoint: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "platform": self.platform.value,
            "method": self.method.value,
            "endpoint": self.endpoint,
            "headers": self.headers or {},
            "params": self.params or {},
            "data": self.data or {},
            "timeout": self.timeout
        }


@dataclass
class APIResponse:
    """API 응답 정보"""
    status_code: int
    data: Dict[str, Any]
    headers: Dict[str, str]
    success: bool
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    cached: bool = False
    
    @classmethod
    def success_response(
        cls,
        status_code: int,
        data: Dict[str, Any],
        headers: Dict[str, str],
        response_time: Optional[float] = None,
        cached: bool = False
    ) -> 'APIResponse':
        """성공 응답 생성"""
        return cls(
            status_code=status_code,
            data=data,
            headers=headers,
            success=True,
            response_time=response_time,
            cached=cached
        )
    
    @classmethod
    def error_response(
        cls,
        status_code: int,
        error_message: str,
        headers: Optional[Dict[str, str]] = None
    ) -> 'APIResponse':
        """에러 응답 생성"""
        return cls(
            status_code=status_code,
            data={},
            headers=headers or {},
            success=False,
            error_message=error_message
        )


@dataclass
class RateLimitInfo:
    """Rate Limit 정보"""
    remaining: int
    limit: int
    reset_time: datetime
    retry_after: Optional[int] = None
    
    @property
    def is_exhausted(self) -> bool:
        """Rate limit 고갈 여부"""
        return self.remaining <= 0
    
    def is_near_limit(self, threshold: int = 10) -> bool:
        """Rate limit 임계값 근접 여부"""
        return self.remaining <= threshold


@dataclass
class CacheKey:
    """캐시 키 정보"""
    platform: str
    endpoint: str
    params_hash: str
    
    def __str__(self) -> str:
        return f"{self.platform}:{self.endpoint}:{self.params_hash}"


@dataclass
class CachedResponse:
    """캐시된 응답 정보"""
    response: APIResponse
    cached_at: datetime
    ttl: int
    
    @property
    def is_expired(self) -> bool:
        """캐시 만료 여부"""
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone.utc) > self.cached_at + timedelta(seconds=self.ttl)


# 플랫폼별 설정 정의
PLATFORM_CONFIGS = {
    Platform.GITHUB: PlatformConfig(
        name="GitHub",
        base_url="https://api.github.com",
        auth_header="Authorization",
        auth_prefix="token",
        rate_limit_per_hour=5000,
        rate_limit_per_minute=None,
        default_headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodePing-HTTPAPIClient/1.0"
        }
    ),
    Platform.GITLAB: PlatformConfig(
        name="GitLab",
        base_url="https://gitlab.com/api/v4",
        auth_header="PRIVATE-TOKEN",
        auth_prefix="",
        rate_limit_per_hour=None,
        rate_limit_per_minute=300,
        default_headers={
            "Content-Type": "application/json",
            "User-Agent": "CodePing-HTTPAPIClient/1.0"
        }
    ),
    Platform.BITBUCKET: PlatformConfig(
        name="Bitbucket",
        base_url="https://api.bitbucket.org/2.0",
        auth_header="Authorization",
        auth_prefix="Bearer",
        rate_limit_per_hour=1000,
        default_headers={
            "Accept": "application/json",
            "User-Agent": "CodePing-HTTPAPIClient/1.0"
        }
    )
} 