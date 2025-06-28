"""Global test configuration and fixtures."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="session")
def patch_universal_webhook_receiver():
    """Patch universal_webhook_receiver Settings to include github_webhook_secret."""
    import universal_webhook_receiver.router as router_module
    
    # Store original Settings class
    original_settings_class = router_module.Settings
    original_get_settings = router_module.get_settings
    
    # Create a patched Settings class
    class PatchedSettings(original_settings_class):
        github_webhook_secret: str = "test_webhook_secret"
    
    # Replace the Settings class in the module
    router_module.Settings = PatchedSettings
    
    # Create a patched get_settings function
    def patched_get_settings():
        return PatchedSettings()
    
    # Replace the get_settings function
    router_module.get_settings = patched_get_settings
    
    yield
    
    # Restore original classes after tests
    router_module.Settings = original_settings_class
    router_module.get_settings = original_get_settings


@pytest.fixture(autouse=True, scope="session")
def patch_git_data_parser():
    """Patch universal_git_data_parser to fix CommitInfo and ValidatedEvent creation."""
    import universal_git_data_parser.service as service_module
    from universal_git_data_parser.models import ValidatedEvent
    from universal_git_data_parser.exceptions import InvalidPayloadError
    from datetime import datetime
    from typing import Dict, Any
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Store original method
    original_parse_github_push = service_module.GitDataParserService.parse_github_push
    
    def patched_parse_github_push(self, headers: Dict[str, str], payload: Dict[str, Any]) -> ValidatedEvent:
        """
        Patched GitHub push webhook 이벤트를 파싱하여 ValidatedEvent 반환
        """
        logger.debug("Parsing GitHub push event")
        
        try:
            # Repository 정보 추출
            repo_info = payload.get("repository", {})
            repository = repo_info.get("full_name")
            if not repository:
                raise InvalidPayloadError("Missing repository full_name")
            
            # Ref 정보 (브랜치)
            ref = payload.get("ref", "")
            
            # Pusher 정보 추출
            pusher_info = payload.get("pusher", {})
            pusher = pusher_info.get("name", "unknown")
            
            # Commits 파싱 - GitCommit 형태로 변환
            commits_data = payload.get("commits", [])
            commits = []
            
            for commit_data in commits_data:
                try:
                    # Author 정보 파싱 (문자열로)
                    author_data = commit_data.get("author", {})
                    author_name = author_data.get("name", "Unknown")
                    
                    # Timestamp 파싱
                    timestamp_str = commit_data.get("timestamp")
                    if timestamp_str:
                        # ISO 형식의 timestamp를 문자열로 유지
                        timestamp = timestamp_str
                    else:
                        timestamp = datetime.now().isoformat()
                    
                    # GitCommit 형태로 생성
                    git_commit = {
                        "id": commit_data.get("sha", commit_data.get("id", "")),
                        "message": commit_data.get("message", ""),
                        "url": commit_data.get("url", ""),
                        "author": author_name,
                        "timestamp": timestamp,
                        "added": commit_data.get("added", []),
                        "removed": commit_data.get("removed", []),
                        "modified": commit_data.get("modified", [])
                    }
                    commits.append(git_commit)
                    
                except Exception as e:
                    logger.warning("Failed to parse commit: %s", str(e))
                    continue
            
            # ValidatedEvent 생성 (딕셔너리 형태로)
            validated_event_data = {
                "repository": repository,
                "ref": ref,
                "pusher": pusher,
                "commits": commits,
                "timestamp": datetime.now().isoformat()
            }
            
            validated_event = ValidatedEvent(**validated_event_data)
            
            logger.debug("Successfully parsed %d commits for %s", len(commits), repository)
            return validated_event
            
        except Exception as e:
            logger.error("Failed to parse GitHub push event: %s", str(e))
            raise InvalidPayloadError(f"Failed to parse push event: {str(e)}")
    
    # Replace the method
    service_module.GitDataParserService.parse_github_push = patched_parse_github_push
    
    yield
    
    # Restore original method
    service_module.GitDataParserService.parse_github_push = original_parse_github_push 