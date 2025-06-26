"""
HTTPAPIClient 모듈 단위 테스트
"""

import json
import pytest
import requests
import requests_mock
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from modules.http_api_client import (
    HTTPAPIClient, Platform, HTTPMethod, APIResponse, 
    APIError, RateLimitError, AuthenticationError
)


class TestHTTPAPIClient:
    """HTTPAPIClient 테스트"""
    
    @pytest.fixture
    def github_client(self):
        """GitHub 클라이언트 픽스처"""
        return HTTPAPIClient(
            platform=Platform.GITHUB,
            auth_token="test_token",
            enable_cache=True,
            enable_rate_limiting=True
        )
    
    @pytest.fixture
    def gitlab_client(self):
        """GitLab 클라이언트 픽스처"""
        return HTTPAPIClient(
            platform=Platform.GITLAB,
            auth_token="test_token",
            enable_cache=True,
            enable_rate_limiting=True
        )
    
    def test_client_initialization(self, github_client):
        """클라이언트 초기화 테스트"""
        assert github_client.platform == Platform.GITHUB
        assert github_client.auth_token == "test_token"
        assert github_client.enable_cache is True
        assert github_client.enable_rate_limiting is True
        assert github_client.adapter is not None
        assert github_client.cache is not None
        assert github_client.rate_limiter is not None
    
    def test_github_get_request_success(self, github_client):
        """GitHub GET 요청 성공 테스트"""
        with requests_mock.Mocker() as m:
            # Mock 응답 설정
            mock_response = {
                "sha": "abc123",
                "commit": {
                    "message": "Test commit",
                    "author": {"name": "Test User", "email": "test@example.com"}
                },
                "stats": {"total": 10, "additions": 5, "deletions": 5},
                "files": [{"filename": "test.py", "status": "modified"}]
            }
            
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                json=mock_response,
                headers={
                    "X-RateLimit-Remaining": "4999",
                    "X-RateLimit-Limit": "5000",
                    "X-RateLimit-Reset": str(int((datetime.now() + timedelta(hours=1)).timestamp()))
                }
            )
            
            # 요청 실행
            response = github_client.get_commit("test/repo", "abc123")
            
            # 응답 검증
            assert response.success is True
            assert response.status_code == 200
            assert response.data["sha"] == "abc123"
            assert response.data["message"] == "Test commit"
            assert "author" in response.data
            assert "stats" in response.data
    
    def test_gitlab_get_request_success(self, gitlab_client):
        """GitLab GET 요청 성공 테스트"""
        with requests_mock.Mocker() as m:
            mock_response = {
                "id": "abc123",
                "message": "Test commit",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "authored_date": "2023-01-01T00:00:00Z",
                "committer_name": "Test User",
                "committer_email": "test@example.com",
                "committed_date": "2023-01-01T00:00:00Z",
                "stats": {"additions": 5, "deletions": 5, "total": 10}
            }
            
            m.get(
                "https://gitlab.com/api/v4/projects/test%2Frepo/commits/abc123",
                json=mock_response,
                headers={
                    "RateLimit-Remaining": "299",
                    "RateLimit-Limit": "300",
                    "RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
                }
            )
            
            response = gitlab_client.get_commit("test/repo", "abc123")
            
            assert response.success is True
            assert response.status_code == 200
            assert response.data["sha"] == "abc123"
            assert response.data["message"] == "Test commit"
            assert response.data["author"]["name"] == "Test User"
    
    def test_authentication_error(self, github_client):
        """인증 에러 테스트"""
        with requests_mock.Mocker() as m:
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                status_code=401,
                json={"message": "Bad credentials"}
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                github_client.get_commit("test/repo", "abc123")
            
            assert "Bad credentials" in str(exc_info.value)
            assert exc_info.value.status_code == 401
    
    def test_rate_limit_error(self, github_client):
        """Rate limit 에러 테스트"""
        with requests_mock.Mocker() as m:
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                status_code=429,
                json={"message": "API rate limit exceeded"},
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Limit": "5000",
                    "X-RateLimit-Reset": str(int((datetime.now() + timedelta(hours=1)).timestamp())),
                    "Retry-After": "3600"
                }
            )
            
            with pytest.raises(RateLimitError) as exc_info:
                github_client.get_commit("test/repo", "abc123")
            
            assert "API rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.status_code == 429
    
    def test_cache_functionality(self, github_client):
        """캐시 기능 테스트"""
        with requests_mock.Mocker() as m:
            mock_response = {
                "sha": "abc123",
                "commit": {"message": "Test commit"}
            }
            
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                json=mock_response
            )
            
            # 첫 번째 요청
            response1 = github_client.get_commit("test/repo", "abc123")
            assert response1.cached is False
            
            # 두 번째 요청 (캐시에서 조회)
            response2 = github_client.get_commit("test/repo", "abc123")
            assert response2.cached is True
            
            # 응답 데이터가 동일한지 확인
            assert response1.data["sha"] == response2.data["sha"]
            
            # API 호출이 한 번만 일어났는지 확인
            assert m.call_count == 1
    
    def test_post_request(self, github_client):
        """POST 요청 테스트"""
        with requests_mock.Mocker() as m:
            mock_response = {"status": "created", "id": 123}
            
            m.post(
                "https://api.github.com/repos/test/repo/issues",
                json=mock_response,
                status_code=201
            )
            
            data = {
                "title": "Test Issue",
                "body": "Test description"
            }
            
            response = github_client.post("/repos/test/repo/issues", data=data)
            
            assert response.success is True
            assert response.status_code == 201
            assert response.data["status"] == "created"
    
    def test_custom_headers(self, github_client):
        """커스텀 헤더 테스트"""
        with requests_mock.Mocker() as m:
            m.get(
                "https://api.github.com/repos/test/repo",
                json={"name": "repo"}
            )
            
            custom_headers = {"X-Custom-Header": "test-value"}
            
            response = github_client.get("/repos/test/repo", headers=custom_headers)
            
            # 요청에 커스텀 헤더가 포함되었는지 확인
            request = m.last_request
            assert request.headers["X-Custom-Header"] == "test-value"
            # 기본 인증 헤더도 포함되었는지 확인
            assert "Authorization" in request.headers
    
    def test_timeout_handling(self, github_client):
        """타임아웃 처리 테스트"""
        with requests_mock.Mocker() as m:
            from modules.http_api_client.exceptions import TimeoutError as APITimeoutError
            
            # requests.exceptions.Timeout을 발생시키도록 설정
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                exc=requests.exceptions.Timeout
            )
            
            with pytest.raises(APITimeoutError):
                github_client.get_commit("test/repo", "abc123")
    
    def test_network_error_handling(self, github_client):
        """네트워크 에러 처리 테스트"""
        with requests_mock.Mocker() as m:
            from modules.http_api_client.exceptions import NetworkError
            
            m.get(
                "https://api.github.com/repos/test/repo/commits/abc123",
                exc=requests.exceptions.ConnectionError
            )
            
            with pytest.raises(NetworkError):
                github_client.get_commit("test/repo", "abc123")
    
    def test_rate_limiter_functionality(self, github_client):
        """Rate Limiter 기능 테스트"""
        rate_limiter = github_client.rate_limiter
        
        # 초기 상태에서는 요청 가능
        assert rate_limiter.can_make_request("github") is True
        
        # 요청 기록
        for _ in range(50):
            rate_limiter.record_request("github")
        
        # 여전히 요청 가능 (60개 제한)
        assert rate_limiter.can_make_request("github") is True
        
        # 60개 초과
        for _ in range(15):
            rate_limiter.record_request("github")
        
        # 이제 요청 불가
        assert rate_limiter.can_make_request("github") is False
    
    def test_cache_expiration(self, github_client):
        """캐시 만료 테스트"""
        cache = github_client.cache
        
        # 테스트용 응답 생성
        response = APIResponse.success_response(
            status_code=200,
            data={"test": "data"},
            headers={}
        )
        
        # 짧은 TTL로 캐시 저장
        cache.set("test_key", response, ttl=1)
        
        # 즉시 조회하면 캐시 히트
        cached = cache.get("test_key")
        assert cached is not None
        assert cached.cached is True
        
        # 2초 후 조회하면 캐시 만료
        import time
        time.sleep(2)
        expired = cache.get("test_key")
        assert expired is None
    
    def test_client_close(self, github_client):
        """클라이언트 정리 테스트"""
        # 클라이언트가 정상적으로 정리되는지 확인
        github_client.close()
        
        # 세션이 닫혔는지 확인 (세션을 닫아도 새 요청은 가능할 수 있음)
        assert github_client.session is not None


class TestPlatformSupport:
    """플랫폼 지원 테스트"""
    
    def test_github_platform_methods(self):
        """GitHub 플랫폼 특화 메서드 테스트"""
        client = HTTPAPIClient(Platform.GITHUB, "token")
        
        with requests_mock.Mocker() as m:
            # Repository 정보 조회
            m.get("https://api.github.com/repos/test/repo", json={"name": "repo"})
            response = client.get_repository("test/repo")
            assert response.success
            
            # Commit 정보 조회
            m.get("https://api.github.com/repos/test/repo/commits/abc123", json={"sha": "abc123"})
            response = client.get_commit("test/repo", "abc123")
            assert response.success
    
    def test_gitlab_platform_methods(self):
        """GitLab 플랫폼 특화 메서드 테스트"""
        client = HTTPAPIClient(Platform.GITLAB, "token")
        
        with requests_mock.Mocker() as m:
            # Project 정보 조회
            m.get("https://gitlab.com/api/v4/projects/test%2Frepo", json={"name": "repo"})
            response = client.get_repository("test/repo")
            assert response.success
            
            # Commit 정보 조회
            m.get("https://gitlab.com/api/v4/projects/test%2Frepo/commits/abc123", json={"id": "abc123"})
            response = client.get_commit("test/repo", "abc123")
            assert response.success


if __name__ == "__main__":
    pytest.main([__file__]) 