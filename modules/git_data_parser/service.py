"""Git data parsing service for fetching and processing diffs."""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from modules.git_data_parser.models import ValidatedEvent, GitCommit, DiffData

logger = logging.getLogger(__name__)


class GitDataParserService:
    """Service for parsing git webhook data and fetching diffs."""
    
    def __init__(self):
        self.github_token = os.environ.get("GITHUB_TOKEN")
    
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
    
    def fetch_diff_data(self, payload: Dict[str, Any], headers: Dict[str, str]) -> DiffData:
        """Fetch diff data from GitHub API."""
        
        platform = "github" if "x-github-event" in {k.lower() for k in headers} else "gitlab"
        
        if platform == "github":
            return self._fetch_github_diff(payload)
        else:
            raise NotImplementedError(f"Platform '{platform}' not implemented yet")
    
    def _fetch_github_diff(self, payload: Dict[str, Any]) -> DiffData:
        """Fetch diff from GitHub Commits API."""
        
        repo = payload["repository"]["full_name"]
        commit_sha = payload.get("after") or payload.get("checkout_sha")
        
        if not commit_sha:
            raise ValueError("No commit SHA found in payload")
        
        try:
            url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}"
            headers_req = {}
            if self.github_token:
                headers_req["Authorization"] = f"token {self.github_token}"
            
            with httpx.Client(timeout=20) as client:
                response = client.get(url, headers=headers_req)
                response.raise_for_status()
                
                data = response.json()
                stats = data.get("stats", {})
                
                # Get patch format for diff content
                patch_response = client.get(url + ".patch", headers=headers_req)
                patch_response.raise_for_status()
                
                return DiffData(
                    commit_sha=commit_sha,
                    repository=repo,
                    diff_content=patch_response.content,
                    added_lines=stats.get("additions"),
                    deleted_lines=stats.get("deletions"),
                    files_changed=stats.get("total"),
                    stats=stats,
                )
                
        except Exception as exc:
            logger.exception("Failed to fetch GitHub diff: %s", exc)
            # Return empty diff data to prevent task failure
            return DiffData(
                commit_sha=commit_sha,
                repository=repo,
                diff_content=b"",
                added_lines=0,
                deleted_lines=0,
                files_changed=0,
            )
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not timestamp_str:
            return None
        
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None 