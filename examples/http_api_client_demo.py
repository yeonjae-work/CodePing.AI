"""
HTTPAPIClient 모듈 사용 예제

이 예제는 HTTPAPIClient 모듈의 주요 기능들을 보여줍니다:
1. GitHub API 사용
2. GitLab API 사용  
3. 캐싱 기능
4. Rate Limiting
5. 에러 처리
"""

import os
import sys
import logging
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from modules.http_api_client import (
    HTTPAPIClient, Platform, APIError, RateLimitError, 
    AuthenticationError, NetworkError
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def github_api_demo():
    """GitHub API 사용 예제"""
    print("\n=== GitHub API Demo ===")
    
    # GitHub 토큰 설정 (환경변수에서 읽기)
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("GITHUB_TOKEN 환경변수가 설정되지 않았습니다.")
        print("export GITHUB_TOKEN=your_token_here")
        return
    
    try:
        # GitHub 클라이언트 생성
        client = HTTPAPIClient(
            platform=Platform.GITHUB,
            auth_token=github_token,
            enable_cache=True,
            enable_rate_limiting=True
        )
        
        # 1. 저장소 정보 조회
        print("\n1. 저장소 정보 조회")
        repo_response = client.get_repository("octocat/Hello-World")
        
        if repo_response.success:
            repo_data = repo_response.data
            print(f"저장소 이름: {repo_data.get('name')}")
            print(f"설명: {repo_data.get('description')}")
            print(f"언어: {repo_data.get('language')}")
            print(f"스타 수: {repo_data.get('stars')}")
            print(f"포크 수: {repo_data.get('forks')}")
            print(f"응답 시간: {repo_response.response_time:.2f}초")
        
        # 2. 커밋 정보 조회
        print("\n2. 커밋 정보 조회")
        commit_response = client.get_commit("octocat/Hello-World", "master")
        
        if commit_response.success:
            commit_data = commit_response.data
            print(f"커밋 SHA: {commit_data.get('sha')}")
            print(f"커밋 메시지: {commit_data.get('message')}")
            print(f"작성자: {commit_data.get('author', {}).get('name')}")
            print(f"응답 시간: {commit_response.response_time:.2f}초")
        
        # 3. 캐시 기능 테스트 (동일한 요청 재실행)
        print("\n3. 캐시 기능 테스트")
        cached_response = client.get_repository("octocat/Hello-World")
        print(f"캐시에서 조회됨: {cached_response.cached}")
        print(f"응답 시간: {cached_response.response_time:.2f}초")
        
        # 4. 직접 API 호출
        print("\n4. 직접 API 호출")
        user_response = client.get("/user")
        if user_response.success:
            user_data = user_response.data
            print(f"사용자: {user_data.get('login')}")
            print(f"이름: {user_data.get('name')}")
        
        # 클라이언트 정리
        client.close()
        
    except AuthenticationError as e:
        print(f"인증 오류: {e}")
    except RateLimitError as e:
        print(f"Rate Limit 오류: {e}")
    except APIError as e:
        print(f"API 오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")


def gitlab_api_demo():
    """GitLab API 사용 예제"""
    print("\n=== GitLab API Demo ===")
    
    # GitLab 토큰 설정
    gitlab_token = os.getenv("GITLAB_TOKEN")
    if not gitlab_token:
        print("GITLAB_TOKEN 환경변수가 설정되지 않았습니다.")
        print("export GITLAB_TOKEN=your_token_here")
        return
    
    try:
        # GitLab 클라이언트 생성
        client = HTTPAPIClient(
            platform=Platform.GITLAB,
            auth_token=gitlab_token,
            enable_cache=True,
            enable_rate_limiting=True
        )
        
        # 1. 프로젝트 정보 조회
        print("\n1. 프로젝트 정보 조회")
        # GitLab의 공개 프로젝트 예제
        project_response = client.get_repository("gitlab-org/gitlab")
        
        if project_response.success:
            project_data = project_response.data
            print(f"프로젝트 이름: {project_data.get('name')}")
            print(f"네임스페이스: {project_data.get('full_name')}")
            print(f"설명: {project_data.get('description')}")
            print(f"스타 수: {project_data.get('stars')}")
            print(f"응답 시간: {project_response.response_time:.2f}초")
        
        # 클라이언트 정리
        client.close()
        
    except AuthenticationError as e:
        print(f"인증 오류: {e}")
    except RateLimitError as e:
        print(f"Rate Limit 오류: {e}")
    except APIError as e:
        print(f"API 오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")


def error_handling_demo():
    """에러 처리 예제"""
    print("\n=== Error Handling Demo ===")
    
    # 잘못된 토큰으로 클라이언트 생성
    client = HTTPAPIClient(
        platform=Platform.GITHUB,
        auth_token="invalid_token",
        enable_cache=False,
        enable_rate_limiting=False
    )
    
    try:
        # 인증이 필요한 API 호출 (실패할 것임)
        response = client.get("/user")
        print("예상치 못하게 성공했습니다.")
        
    except AuthenticationError as e:
        print(f"✓ 인증 오류를 올바르게 처리했습니다: {e}")
    except APIError as e:
        print(f"✓ API 오류를 올바르게 처리했습니다: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
    
    client.close()


def performance_demo():
    """성능 테스트 예제"""
    print("\n=== Performance Demo ===")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("GITHUB_TOKEN이 필요합니다.")
        return
    
    # 캐시 활성화/비활성화 비교
    endpoints = [
        "/repos/octocat/Hello-World",
        "/repos/microsoft/vscode", 
        "/repos/facebook/react"
    ]
    
    print("\n1. 캐시 비활성화")
    client_no_cache = HTTPAPIClient(
        platform=Platform.GITHUB,
        auth_token=github_token,
        enable_cache=False
    )
    
    start_time = datetime.now()
    for endpoint in endpoints:
        response = client_no_cache.get(endpoint)
        print(f"{endpoint}: {response.response_time:.2f}초")
    
    total_time_no_cache = (datetime.now() - start_time).total_seconds()
    print(f"총 시간 (캐시 없음): {total_time_no_cache:.2f}초")
    
    client_no_cache.close()
    
    print("\n2. 캐시 활성화")
    client_with_cache = HTTPAPIClient(
        platform=Platform.GITHUB,
        auth_token=github_token,
        enable_cache=True
    )
    
    # 첫 번째 실행 (캐시 채우기)
    for endpoint in endpoints:
        client_with_cache.get(endpoint)
    
    # 두 번째 실행 (캐시에서 조회)
    start_time = datetime.now()
    for endpoint in endpoints:
        response = client_with_cache.get(endpoint)
        print(f"{endpoint}: {response.response_time:.2f}초 (캐시: {response.cached})")
    
    total_time_with_cache = (datetime.now() - start_time).total_seconds()
    print(f"총 시간 (캐시 사용): {total_time_with_cache:.2f}초")
    
    # 성능 개선 계산
    if total_time_no_cache > 0:
        improvement = ((total_time_no_cache - total_time_with_cache) / total_time_no_cache) * 100
        print(f"성능 개선: {improvement:.1f}%")
    
    client_with_cache.close()


def rate_limiting_demo():
    """Rate Limiting 예제"""
    print("\n=== Rate Limiting Demo ===")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("GITHUB_TOKEN이 필요합니다.")
        return
    
    client = HTTPAPIClient(
        platform=Platform.GITHUB,
        auth_token=github_token,
        enable_rate_limiting=True
    )
    
    try:
        # 연속으로 여러 요청 보내기
        for i in range(5):
            response = client.get("/user")
            if response.success:
                rate_limit = client.rate_limiter._limits.get("github")
                if rate_limit:
                    print(f"요청 {i+1}: 남은 요청 수 {rate_limit.remaining}/{rate_limit.limit}")
                else:
                    print(f"요청 {i+1}: 성공")
    
    except RateLimitError as e:
        print(f"Rate Limit에 도달했습니다: {e}")
    
    client.close()


def main():
    """메인 함수"""
    print("HTTPAPIClient 모듈 데모")
    print("=" * 50)
    
    # 각 데모 실행
    github_api_demo()
    gitlab_api_demo()
    error_handling_demo()
    performance_demo()
    rate_limiting_demo()
    
    print("\n데모가 완료되었습니다.")
    print("\n사용법:")
    print("1. 환경변수 설정:")
    print("   export GITHUB_TOKEN=your_github_token")
    print("   export GITLAB_TOKEN=your_gitlab_token")
    print("\n2. 스크립트 실행:")
    print("   python examples/http_api_client_demo.py")


if __name__ == "__main__":
    main() 