"""
HTTPAPIClient 핵심 클라이언트 구현
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta, timezone

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    Platform, HTTPMethod, APIRequest, APIResponse, 
    RateLimitInfo, CacheKey, CachedResponse
)
from .adapters import AdapterFactory, PlatformAPIAdapter
from .exceptions import (
    APIError, RateLimitError, AuthenticationError, NetworkError, 
    TimeoutError, handle_http_error
)
from shared.utils.logging import ModuleIOLogger


class RateLimiter:
    """Rate Limiter 구현"""
    
    def __init__(self):
        self._limits: Dict[str, RateLimitInfo] = {}
        self._requests: Dict[str, list] = {}
    
    def can_make_request(self, platform: str, current_limit: Optional[RateLimitInfo] = None) -> bool:
        """요청 가능 여부 확인"""
        if current_limit and current_limit.is_exhausted:
            return False
        
        # 플랫폼별 요청 이력 확인
        now = time.time()
        platform_requests = self._requests.get(platform, [])
        
        # 1분 전 요청들 제거
        recent_requests = [req_time for req_time in platform_requests if now - req_time < 60]
        self._requests[platform] = recent_requests
        
        # 분당 요청 제한 확인 (예: 60 요청/분)
        return len(recent_requests) < 60
    
    def record_request(self, platform: str):
        """요청 기록"""
        now = time.time()
        if platform not in self._requests:
            self._requests[platform] = []
        self._requests[platform].append(now)
    
    def update_limits(self, platform: str, limit_info: RateLimitInfo):
        """Rate limit 정보 업데이트"""
        self._limits[platform] = limit_info
    
    def get_wait_time(self, platform: str) -> float:
        """대기 시간 계산"""
        limit_info = self._limits.get(platform)
        if limit_info and limit_info.is_exhausted:
            return (limit_info.reset_time - datetime.now()).total_seconds()
        return 0


class SimpleCache:
    """간단한 인메모리 캐시"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CachedResponse] = {}
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[APIResponse]:
        """캐시에서 응답 조회"""
        cached = self._cache.get(key)
        if cached and not cached.is_expired:
            response = cached.response
            response.cached = True
            return response
        elif cached:
            # 만료된 캐시 제거
            del self._cache[key]
        return None
    
    def set(self, key: str, response: APIResponse, ttl: int = 300):
        """캐시에 응답 저장"""
        if len(self._cache) >= self._max_size:
            # 가장 오래된 항목 제거
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].cached_at)
            del self._cache[oldest_key]
        
        self._cache[key] = CachedResponse(
            response=response,
            cached_at=datetime.now(timezone.utc),
            ttl=ttl
        )
    
    def clear(self):
        """캐시 초기화"""
        self._cache.clear()


class HTTPAPIClient:
    """범용 HTTP API 클라이언트"""
    
    def __init__(
        self,
        platform: Platform,
        auth_token: str,
        enable_cache: bool = True,
        enable_rate_limiting: bool = True,
        max_retries: int = 3,
        timeout: int = 30,
        session: Optional[requests.Session] = None
    ):
        self.platform = platform
        self.auth_token = auth_token
        self.enable_cache = enable_cache
        self.enable_rate_limiting = enable_rate_limiting
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 어댑터 초기화
        self.adapter = AdapterFactory.create_adapter(platform, auth_token)
        
        # Rate Limiter 초기화
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        
        # 캐시 초기화
        self.cache = SimpleCache() if enable_cache else None
        
        # HTTP 세션 설정
        self.session = session or self._create_session()
        
        # 로거 설정
        self.logger = logging.getLogger(f"HTTPAPIClient.{platform.value}")
        
        # 입출력 로거 설정
        self.io_logger = ModuleIOLogger("HTTPAPIClient")
    
    def _create_session(self) -> requests.Session:
        """HTTP 세션 생성"""
        session = requests.Session()
        
        # 재시도 정책 설정
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        cache_ttl: int = 300,
        operation: str = "generic"
    ) -> APIResponse:
        """HTTP 요청 실행"""
        start_time = time.time()
        
        # API 요청 객체 생성
        api_request = APIRequest(
            platform=self.platform,
            method=method,
            endpoint=endpoint,
            headers=headers,
            params=params,
            data=data,
            timeout=timeout or self.timeout
        )
        
        try:
            # 캐시 확인 (GET 요청만)
            if method == HTTPMethod.GET and self.cache:
                cache_key = self._get_cache_key(endpoint, params)
                cached_response = self.cache.get(cache_key)
                if cached_response:
                    self.logger.debug(f"Cache hit for {endpoint}")
                    return cached_response
            
            # Rate limit 확인
            if self.rate_limiter and not self.rate_limiter.can_make_request(self.platform.value):
                wait_time = self.rate_limiter.get_wait_time(self.platform.value)
                if wait_time > 0:
                    raise RateLimitError(
                        f"Rate limit exceeded, wait {wait_time:.1f}s",
                        retry_after=int(wait_time),
                        platform=self.platform.value
                    )
            
            # 실제 HTTP 요청 실행
            response = self._execute_request(api_request)
            
            # Rate limit 정보 업데이트
            if self.rate_limiter:
                rate_limit_info = self.adapter.parse_rate_limit(response.headers)
                if rate_limit_info:
                    self.rate_limiter.update_limits(self.platform.value, rate_limit_info)
                    
                    # Rate limit 임계값 경고
                    if rate_limit_info.is_near_limit():
                        self.logger.warning(
                            f"Rate limit warning: {rate_limit_info.remaining} requests remaining"
                        )
                
                self.rate_limiter.record_request(self.platform.value)
            
            # 응답 파싱
            parsed_data = self.adapter.parse_response(response.data, operation)
            response.data = parsed_data
            
            # 응답 시간 기록
            response.response_time = time.time() - start_time
            
            # 캐시 저장 (GET 요청 성공시만)
            if (method == HTTPMethod.GET and self.cache and 
                response.success and 200 <= response.status_code < 300):
                cache_key = self._get_cache_key(endpoint, params)
                self.cache.set(cache_key, response, cache_ttl)
            
            self.logger.info(
                f"{method.value} {endpoint} - {response.status_code} "
                f"({response.response_time:.2f}s)"
            )
            
            return response
            
        except Exception as e:
            error_time = time.time() - start_time
            self.logger.error(
                f"{method.value} {endpoint} failed ({error_time:.2f}s): {str(e)}"
            )
            raise
    
    def _execute_request(self, api_request: APIRequest) -> APIResponse:
        """실제 HTTP 요청 실행"""
        url = self.adapter.build_url(api_request.endpoint)
        
        # 헤더 준비
        headers = self.adapter.get_default_headers()
        if api_request.headers:
            headers.update(api_request.headers)
        
        try:
            # requests 라이브러리로 요청 실행
            response = self.session.request(
                method=api_request.method.value,
                url=url,
                params=api_request.params,
                json=api_request.data if api_request.data else None,
                headers=headers,
                timeout=api_request.timeout
            )
            
            # 응답 데이터 파싱
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {"raw_content": response.text}
            
            # 성공 응답
            if response.ok:
                return APIResponse.success_response(
                    status_code=response.status_code,
                    data=response_data,
                    headers=dict(response.headers)
                )
            
            # 에러 응답
            error_message = self._extract_error_message(response_data, response.text)
            raise handle_http_error(response.status_code, error_message, self.platform.value)
            
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Request timeout after {api_request.timeout}s",
                timeout=api_request.timeout,
                platform=self.platform.value
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Network connection failed: {str(e)}",
                platform=self.platform.value
            )
        except requests.exceptions.RequestException as e:
            raise APIError(
                f"Request failed: {str(e)}",
                platform=self.platform.value
            )
    
    def _extract_error_message(self, response_data: Dict[str, Any], raw_text: str) -> str:
        """에러 메시지 추출"""
        # 플랫폼별 에러 메시지 형식에 맞게 추출
        if isinstance(response_data, dict):
            # GitHub 스타일
            if "message" in response_data:
                return response_data["message"]
            
            # GitLab 스타일
            if "error" in response_data:
                error = response_data["error"]
                if isinstance(error, str):
                    return error
                elif isinstance(error, dict) and "message" in error:
                    return error["message"]
            
            # 일반적인 형식들
            for key in ["error_description", "detail", "details"]:
                if key in response_data:
                    return str(response_data[key])
        
        return raw_text[:200] if raw_text else "Unknown error"
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """캐시 키 생성"""
        return self.adapter.get_cache_key(endpoint, params)
    
    # 편의 메서드들
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """GET 요청"""
        return self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """POST 요청"""
        return self.request(HTTPMethod.POST, endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """PUT 요청"""
        return self.request(HTTPMethod.PUT, endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """DELETE 요청"""
        return self.request(HTTPMethod.DELETE, endpoint, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """PATCH 요청"""
        return self.request(HTTPMethod.PATCH, endpoint, data=data, **kwargs)
    
    # 플랫폼별 특화 메서드들
    def get_commit(self, repo_name: str, commit_sha: str) -> APIResponse:
        """커밋 정보 조회"""
        # 입력 로깅
        self.io_logger.log_input(
            "get_commit",
            data={"repo_name": repo_name, "commit_sha": commit_sha},
            metadata={"platform": self.platform.value}
        )
        
        try:
            if self.platform == Platform.GITHUB:
                endpoint = f"/repos/{repo_name}/commits/{commit_sha}"
            elif self.platform == Platform.GITLAB:
                # GitLab에서는 프로젝트 ID 필요
                endpoint = f"/projects/{repo_name.replace('/', '%2F')}/commits/{commit_sha}"
            else:
                raise APIError(f"get_commit not implemented for {self.platform.value}")
            
            response = self.get(endpoint, operation="get_commit")
            
            # 출력 로깅
            self.io_logger.log_output(
                "get_commit",
                data=response.data,
                metadata={
                    "platform": self.platform.value,
                    "status_code": response.status_code,
                    "success": response.success,
                    "commit_sha": commit_sha,
                    "files_changed": len(response.data.get("files", [])) if response.data else 0
                }
            )
            
            return response
            
        except Exception as e:
            # 오류 로깅
            self.io_logger.log_error(
                "get_commit",
                e,
                metadata={
                    "platform": self.platform.value,
                    "repo_name": repo_name,
                    "commit_sha": commit_sha
                }
            )
            raise
    
    def get_repository(self, repo_name: str) -> APIResponse:
        """저장소 정보 조회"""
        if self.platform == Platform.GITHUB:
            endpoint = f"/repos/{repo_name}"
            operation = "get_repository"
        elif self.platform == Platform.GITLAB:
            endpoint = f"/projects/{repo_name.replace('/', '%2F')}"
            operation = "get_project"
        else:
            raise APIError(f"get_repository not implemented for {self.platform.value}")
        
        return self.get(endpoint, operation=operation)
    
    def get_diff(self, repo_name: str, commit_sha: str) -> APIResponse:
        """커밋 diff 조회"""
        if self.platform == Platform.GITHUB:
            endpoint = f"/repos/{repo_name}/commits/{commit_sha}"
        elif self.platform == Platform.GITLAB:
            endpoint = f"/projects/{repo_name.replace('/', '%2F')}/commits/{commit_sha}/diff"
        else:
            raise APIError(f"get_diff not implemented for {self.platform.value}")
        
        return self.get(endpoint, operation="get_diff")
    
    def close(self):
        """클라이언트 정리"""
        if self.session:
            self.session.close()
        if self.cache:
            self.cache.clear()


class AsyncHTTPAPIClient:
    """비동기 HTTP API 클라이언트"""
    
    def __init__(
        self,
        platform: Platform,
        auth_token: str,
        enable_cache: bool = True,
        enable_rate_limiting: bool = True,
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.platform = platform
        self.auth_token = auth_token
        self.enable_cache = enable_cache
        self.enable_rate_limiting = enable_rate_limiting
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 어댑터 초기화
        self.adapter = AdapterFactory.create_adapter(platform, auth_token)
        
        # Rate Limiter 초기화
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        
        # 캐시 초기화
        self.cache = SimpleCache() if enable_cache else None
        
        # 로거 설정
        self.logger = logging.getLogger(f"AsyncHTTPAPIClient.{platform.value}")
    
    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        cache_ttl: int = 300,
        operation: str = "generic"
    ) -> APIResponse:
        """비동기 HTTP 요청 실행"""
        start_time = time.time()
        
        # 캐시 확인 (GET 요청만)
        if method == HTTPMethod.GET and self.cache:
            cache_key = self.adapter.get_cache_key(endpoint, params)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                self.logger.debug(f"Cache hit for {endpoint}")
                return cached_response
        
        url = self.adapter.build_url(endpoint)
        request_headers = self.adapter.get_default_headers()
        if headers:
            request_headers.update(headers)
        
        timeout_config = aiohttp.ClientTimeout(total=timeout or self.timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.request(
                    method=method.value,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers
                ) as response:
                    
                    # 응답 데이터 파싱
                    try:
                        response_data = await response.json()
                    except:
                        response_text = await response.text()
                        response_data = {"raw_content": response_text}
                    
                    response_time = time.time() - start_time
                    
                    if response.ok:
                        # 응답 파싱
                        parsed_data = self.adapter.parse_response(response_data, operation)
                        
                        api_response = APIResponse.success_response(
                            status_code=response.status,
                            data=parsed_data,
                            headers=dict(response.headers),
                            response_time=response_time
                        )
                        
                        # 캐시 저장
                        if (method == HTTPMethod.GET and self.cache and 
                            200 <= response.status < 300):
                            cache_key = self.adapter.get_cache_key(endpoint, params)
                            self.cache.set(cache_key, api_response, cache_ttl)
                        
                        return api_response
                    else:
                        error_message = self._extract_error_message(response_data, "")
                        raise handle_http_error(response.status, error_message, self.platform.value)
                        
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Request timeout after {timeout or self.timeout}s",
                timeout=timeout or self.timeout,
                platform=self.platform.value
            )
        except aiohttp.ClientError as e:
            raise NetworkError(
                f"Network error: {str(e)}",
                platform=self.platform.value
            )
    
    def _extract_error_message(self, response_data: Dict[str, Any], raw_text: str) -> str:
        """에러 메시지 추출 (동기 버전과 동일)"""
        if isinstance(response_data, dict):
            if "message" in response_data:
                return response_data["message"]
            if "error" in response_data:
                error = response_data["error"]
                if isinstance(error, str):
                    return error
                elif isinstance(error, dict) and "message" in error:
                    return error["message"]
            for key in ["error_description", "detail", "details"]:
                if key in response_data:
                    return str(response_data[key])
        return raw_text[:200] if raw_text else "Unknown error"
    
    # 편의 메서드들 (동기 버전과 동일한 인터페이스)
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """비동기 GET 요청"""
        return await self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """비동기 POST 요청"""
        return await self.request(HTTPMethod.POST, endpoint, data=data, **kwargs) 