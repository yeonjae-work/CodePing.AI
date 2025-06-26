"""
플랫폼별 API 어댑터 구현
"""

import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from .models import Platform, PlatformConfig, APIRequest, APIResponse, RateLimitInfo, PLATFORM_CONFIGS
from .exceptions import RateLimitError, PlatformNotSupportedError


class PlatformAPIAdapter(ABC):
    """플랫폼 API 어댑터 기본 클래스"""
    
    def __init__(self, config: PlatformConfig, auth_token: str):
        self.config = config
        self.auth_token = auth_token
    
    @abstractmethod
    def build_url(self, endpoint: str) -> str:
        """API URL 구성"""
        pass
    
    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """인증 헤더 반환"""
        pass
    
    @abstractmethod
    def parse_rate_limit(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """Rate limit 정보 파싱"""
        pass
    
    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """응답 데이터 파싱"""
        pass
    
    def get_default_headers(self) -> Dict[str, str]:
        """기본 헤더 반환"""
        headers = self.config.default_headers.copy()
        headers.update(self.get_auth_headers())
        return headers
    
    def get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """캐시 키 생성"""
        params_str = ""
        if params:
            # 파라미터를 정렬하여 일관된 해시 생성
            sorted_params = sorted(params.items())
            params_str = str(sorted_params)
        
        cache_data = f"{self.config.name}:{endpoint}:{params_str}"
        return hashlib.md5(cache_data.encode()).hexdigest()


class GitHubAdapter(PlatformAPIAdapter):
    """GitHub API 어댑터"""
    
    def build_url(self, endpoint: str) -> str:
        """GitHub API URL 구성"""
        # endpoint가 이미 전체 URL이면 그대로 반환
        if endpoint.startswith('http'):
            return endpoint
        
        # 앞에 슬래시가 없으면 추가
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"
        
        return f"{self.config.base_url}{endpoint}"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """GitHub 인증 헤더"""
        return self.config.get_auth_header(self.auth_token)
    
    def parse_rate_limit(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """GitHub Rate limit 정보 파싱"""
        try:
            remaining = int(headers.get('X-RateLimit-Remaining', 0))
            limit = int(headers.get('X-RateLimit-Limit', 5000))
            reset_timestamp = int(headers.get('X-RateLimit-Reset', 0))
            reset_time = datetime.fromtimestamp(reset_timestamp)
            
            return RateLimitInfo(
                remaining=remaining,
                limit=limit,
                reset_time=reset_time
            )
        except (ValueError, TypeError):
            return None
    
    def parse_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """GitHub 응답 데이터 파싱"""
        if operation == "get_commit":
            return self._parse_commit_response(response_data)
        elif operation == "get_diff":
            return self._parse_diff_response(response_data)
        elif operation == "get_repository":
            return self._parse_repository_response(response_data)
        else:
            return response_data
    
    def _parse_commit_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """커밋 응답 파싱"""
        return {
            "sha": data.get("sha"),
            "message": data.get("commit", {}).get("message"),
            "author": data.get("commit", {}).get("author", {}),
            "committer": data.get("commit", {}).get("committer", {}),
            "stats": data.get("stats", {}),
            "files": data.get("files", []),
            "parents": data.get("parents", []),
            "url": data.get("html_url")
        }
    
    def _parse_diff_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Diff 응답 파싱"""
        return {
            "files": data.get("files", []),
            "stats": data.get("stats", {}),
            "total_additions": sum(f.get("additions", 0) for f in data.get("files", [])),
            "total_deletions": sum(f.get("deletions", 0) for f in data.get("files", [])),
            "total_changes": sum(f.get("changes", 0) for f in data.get("files", []))
        }
    
    def _parse_repository_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """저장소 응답 파싱"""
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "owner": data.get("owner", {}),
            "private": data.get("private"),
            "description": data.get("description"),
            "language": data.get("language"),
            "size": data.get("size"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "url": data.get("html_url")
        }


class GitLabAdapter(PlatformAPIAdapter):
    """GitLab API 어댑터"""
    
    def build_url(self, endpoint: str) -> str:
        """GitLab API URL 구성"""
        if endpoint.startswith('http'):
            return endpoint
        
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"
        
        return f"{self.config.base_url}{endpoint}"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """GitLab 인증 헤더"""
        return self.config.get_auth_header(self.auth_token)
    
    def parse_rate_limit(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """GitLab Rate limit 정보 파싱"""
        try:
            remaining = int(headers.get('RateLimit-Remaining', 0))
            limit = int(headers.get('RateLimit-Limit', 300))
            reset_timestamp = int(headers.get('RateLimit-Reset', 0))
            reset_time = datetime.fromtimestamp(reset_timestamp)
            
            return RateLimitInfo(
                remaining=remaining,
                limit=limit,
                reset_time=reset_time
            )
        except (ValueError, TypeError):
            return None
    
    def parse_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """GitLab 응답 데이터 파싱"""
        if operation == "get_commit":
            return self._parse_commit_response(response_data)
        elif operation == "get_diff":
            return self._parse_diff_response(response_data)
        elif operation == "get_project":
            return self._parse_project_response(response_data)
        else:
            return response_data
    
    def _parse_commit_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """커밋 응답 파싱"""
        return {
            "sha": data.get("id"),
            "message": data.get("message"),
            "author": {
                "name": data.get("author_name"),
                "email": data.get("author_email"),
                "date": data.get("authored_date")
            },
            "committer": {
                "name": data.get("committer_name"), 
                "email": data.get("committer_email"),
                "date": data.get("committed_date")
            },
            "stats": data.get("stats", {}),
            "parent_ids": data.get("parent_ids", []),
            "url": data.get("web_url")
        }
    
    def _parse_diff_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Diff 응답 파싱"""
        # GitLab의 diff 응답은 파일별로 분리되어 있음
        files = []
        total_additions = 0
        total_deletions = 0
        
        if isinstance(data, list):
            for file_diff in data:
                files.append(file_diff)
                # GitLab diff에서 통계 정보 추출
                diff_text = file_diff.get("diff", "")
                additions = diff_text.count("\n+") if diff_text else 0
                deletions = diff_text.count("\n-") if diff_text else 0
                total_additions += additions
                total_deletions += deletions
        
        return {
            "files": files,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_changes": total_additions + total_deletions
        }
    
    def _parse_project_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """프로젝트 응답 파싱"""
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "full_name": data.get("path_with_namespace"),
            "owner": data.get("owner", {}),
            "private": data.get("visibility") == "private",
            "description": data.get("description"),
            "language": None,  # GitLab API에서는 별도 조회 필요
            "size": data.get("repository_size"),
            "stars": data.get("star_count"),
            "forks": data.get("forks_count"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("last_activity_at"),
            "url": data.get("web_url")
        }


class BitbucketAdapter(PlatformAPIAdapter):
    """Bitbucket API 어댑터"""
    
    def build_url(self, endpoint: str) -> str:
        """Bitbucket API URL 구성"""
        if endpoint.startswith('http'):
            return endpoint
        
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"
        
        return f"{self.config.base_url}{endpoint}"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Bitbucket 인증 헤더"""
        return self.config.get_auth_header(self.auth_token)
    
    def parse_rate_limit(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """Bitbucket Rate limit 정보 파싱"""
        # Bitbucket은 특별한 rate limit 헤더가 없음
        return None
    
    def parse_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Bitbucket 응답 데이터 파싱"""
        # Bitbucket API 응답 구조에 맞게 파싱
        return response_data


class AdapterFactory:
    """어댑터 팩토리"""
    
    _adapters = {
        Platform.GITHUB: GitHubAdapter,
        Platform.GITLAB: GitLabAdapter,
        Platform.BITBUCKET: BitbucketAdapter
    }
    
    @classmethod
    def create_adapter(cls, platform: Platform, auth_token: str) -> PlatformAPIAdapter:
        """플랫폼에 맞는 어댑터 생성"""
        if platform not in cls._adapters:
            supported = [p.value for p in cls._adapters.keys()]
            raise PlatformNotSupportedError(platform.value, supported)
        
        config = PLATFORM_CONFIGS.get(platform)
        if not config:
            raise PlatformNotSupportedError(platform.value)
        
        adapter_class = cls._adapters[platform]
        return adapter_class(config, auth_token)
    
    @classmethod
    def register_adapter(cls, platform: Platform, adapter_class: type):
        """새로운 어댑터 등록"""
        cls._adapters[platform] = adapter_class
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """지원하는 플랫폼 목록 반환"""
        return [platform.value for platform in cls._adapters.keys()] 