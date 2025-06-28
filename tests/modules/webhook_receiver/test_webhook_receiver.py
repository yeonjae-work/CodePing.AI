"""Tests for webhook receiver module."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
SECRET = "test_webhook_secret"


def _create_signature(body: bytes) -> str:
    """Create GitHub webhook signature for testing."""
    mac = hmac.new(SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


@pytest.fixture(autouse=True)
def setup_local_settings(monkeypatch):
    """Setup local settings for testing."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    monkeypatch.setenv("CELERY_ALWAYS_EAGER", "true")
    
    # Clear local settings cache
    from shared.config.settings import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _sample_github_payload() -> dict:
    """Create sample GitHub push payload."""
    return {
        "ref": "refs/heads/main",
        "repository": {
            "full_name": "test/repo",
            "name": "repo",
            "owner": {"login": "test"}
        },
        "pusher": {"name": "testuser"},
        "head_commit": {
            "id": "abc123def456",
            "sha": "abc123def456",
            "message": "Test commit",
            "timestamp": "2023-01-01T10:00:00Z",
            "url": "https://github.com/test/repo/commit/abc123def456",
            "author": {
                "name": "Test User",
                "email": "test@example.com"
            },
            "added": ["file1.py"],
            "removed": [],
            "modified": ["file2.py"]
        },
        "commits": [
            {
                "id": "abc123def456",
                "sha": "abc123def456",
                "message": "Test commit",
                "timestamp": "2023-01-01T10:00:00Z",
                "url": "https://github.com/test/repo/commit/abc123def456",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com"
                },
                "added": ["file1.py"],
                "removed": [],
                "modified": ["file2.py"]
            }
        ]
    }


@patch("universal_webhook_receiver.service.celery_app.send_task")
def test_webhook_endpoint_valid_signature(mock_send_task):
    """Test webhook endpoint with valid GitHub push signature."""
    # Mock Celery task
    mock_send_task.return_value = AsyncMock()

    payload = _sample_github_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "test/repo"
    assert data["ref"] == "refs/heads/main"
    assert data["pusher"] == "testuser"
    assert len(data["commits"]) == 1

    # Verify Celery task was called
    mock_send_task.assert_called_once()


def test_webhook_endpoint_invalid_signature():
    """Test webhook endpoint with invalid signature."""
    payload = _sample_github_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": "sha256=invalid_signature",
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]


def test_webhook_endpoint_missing_signature():
    """Test webhook endpoint without signature header."""
    payload = _sample_github_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 401
    assert "Missing signature" in response.json()["detail"]


def test_webhook_endpoint_unsupported_event():
    """Test webhook endpoint with unsupported event type."""
    payload = {"action": "opened", "issue": {"title": "Test issue"}}
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "issues",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 202  # Accepted but ignored
    assert "ignored" in response.json()["detail"]


def test_webhook_endpoint_malformed_json():
    """Test webhook endpoint with malformed JSON."""
    body = b"invalid json"
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 400  # Bad Request


@patch("universal_webhook_receiver.service.celery_app.send_task")
def test_webhook_multiple_commits(mock_send_task):
    """Test webhook with multiple commits."""
    # Mock Celery task
    mock_send_task.return_value = AsyncMock()
    
    payload = _sample_github_payload()
    payload["commits"].append({
        "id": "def456ghi789",
        "sha": "def456ghi789",
        "message": "Second commit",
        "timestamp": "2023-01-01T11:00:00Z",
        "url": "https://github.com/test/repo/commit/def456ghi789",
        "author": {
            "name": "Test User",
            "email": "test@example.com"
        },
        "added": [],
        "removed": ["old_file.py"],
        "modified": ["file3.py"]
    })

    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["commits"]) == 2

    # Should be called once with entire payload
    mock_send_task.assert_called_once()


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Git Diff Monitor API" in data["message"]
