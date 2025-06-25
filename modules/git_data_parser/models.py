"""Git data parsing models and DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CommitInfo(BaseModel):
    """Commit information extracted from GitHub push event."""
    
    sha: str = Field(..., description="Commit SHA hash")
    message: str = Field(..., description="Commit message")
    author_name: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    timestamp: datetime = Field(..., description="Commit timestamp")
    url: str = Field(..., description="GitHub commit URL")
    
    model_config = ConfigDict(from_attributes=True)


class GitCommit(BaseModel):
    """Legacy git commit model for compatibility."""
    
    id: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")
    url: str = Field(..., description="Commit URL")
    author: Optional[str] = Field(None, description="Author name")
    timestamp: Optional[datetime] = Field(None, description="Commit timestamp")
    added: List[str] = Field(default_factory=list, description="Added files")
    removed: List[str] = Field(default_factory=list, description="Removed files")
    modified: List[str] = Field(default_factory=list, description="Modified files")
    
    model_config = ConfigDict(from_attributes=True)


class ValidatedEvent(BaseModel):
    """Validated webhook event structure."""
    
    repository: str = Field(..., description="Repository full name")
    ref: str = Field(..., description="Git reference (branch)")
    pusher: str = Field(..., description="User who pushed")
    commits: List[GitCommit] = Field(..., description="List of commits")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class FileChange(BaseModel):
    """File change information from commit diff."""
    
    filename: str = Field(..., description="File path")
    status: str = Field(..., description="Change status: added, modified, removed")
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    patch: Optional[str] = Field(default=None, description="Diff patch content")
    
    model_config = ConfigDict(from_attributes=True)


class DiffData(BaseModel):
    """Complete diff data for a commit."""
    
    commit_sha: str = Field(..., description="Commit SHA")
    repository: str = Field(..., description="Repository full name")
    files: List[FileChange] = Field(default_factory=list, description="List of changed files")
    total_additions: int = Field(default=0, description="Total lines added")
    total_deletions: int = Field(default=0, description="Total lines deleted")
    raw_patch: Optional[str] = Field(default=None, description="Raw unified diff")
    
    # Legacy fields for compatibility
    diff_content: Optional[bytes] = Field(default=None, description="Raw diff content (legacy)")
    added_lines: Optional[int] = Field(None, description="Number of added lines (legacy)")
    deleted_lines: Optional[int] = Field(None, description="Number of deleted lines (legacy)")
    files_changed: Optional[int] = Field(None, description="Number of changed files (legacy)")
    stats: Optional[Dict[str, Any]] = Field(None, description="Additional diff statistics (legacy)")
    
    model_config = ConfigDict(from_attributes=True)


class GitHubPushPayload(BaseModel):
    """GitHub push webhook payload structure."""
    
    repository: Dict[str, Any] = Field(..., description="Repository information")
    commits: List[Dict[str, Any]] = Field(default_factory=list, description="List of commits")
    head_commit: Optional[Dict[str, Any]] = Field(default=None, description="Head commit info")
    ref: str = Field(..., description="Git reference")
    pusher: Dict[str, Any] = Field(..., description="User who pushed")
    
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow"  # Allow additional fields from GitHub
    ) 