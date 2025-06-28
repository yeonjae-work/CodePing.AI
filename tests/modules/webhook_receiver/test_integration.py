"""Integration tests with real GitHub webhook payloads."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from main import app
from shared.config.settings import get_settings

client = TestClient(app)

SECRET = "test_webhook_secret"


def _create_signature(body: bytes) -> str:
    """Create GitHub webhook signature for testing."""
    mac = hmac.new(SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("CELERY_ALWAYS_EAGER", "true")


def _real_github_push_payload():
    """Real GitHub push webhook payload for testing."""
    return {
        "ref": "refs/heads/changes",
        "before": "9049f1265b7d61be4a8904a9a27120d2064dab3b",
        "after": "0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c",
        "repository": {
            "id": 35129377,
            "name": "public-repo",
            "full_name": "baxterthehacker/public-repo",
            "owner": {
                "name": "baxterthehacker",
                "email": "baxterthehacker@users.noreply.github.com",
                "login": "baxterthehacker",
                "id": 6752317,
                "avatar_url": "https://avatars.githubusercontent.com/u/6752317?v=3",
                "gravatar_id": "",
                "url": "https://api.github.com/users/baxterthehacker",
                "html_url": "https://github.com/baxterthehacker",
                "type": "User",
                "site_admin": False
            },
            "private": False,
            "html_url": "https://github.com/baxterthehacker/public-repo",
            "description": "",
            "fork": False,
            "url": "https://api.github.com/repos/baxterthehacker/public-repo",
            "created_at": "2015-05-05T23:40:12Z",
            "updated_at": "2015-05-05T23:40:12Z",
            "pushed_at": "2015-05-05T23:40:27Z",
            "git_url": "git://github.com/baxterthehacker/public-repo.git",
            "ssh_url": "git@github.com:baxterthehacker/public-repo.git",
            "clone_url": "https://github.com/baxterthehacker/public-repo.git",
            "svn_url": "https://github.com/baxterthehacker/public-repo",
            "homepage": None,
            "size": 0,
            "stargazers_count": 0,
            "watchers_count": 0,
            "language": None,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True,
            "has_pages": False,
            "forks_count": 0,
            "mirror_url": None,
            "open_issues_count": 0,
            "forks": 0,
            "open_issues": 0,
            "watchers": 0,
            "default_branch": "master"
        },
        "pusher": {
            "name": "baxterthehacker",
            "email": "baxterthehacker@users.noreply.github.com"
        },
        "sender": {
            "login": "baxterthehacker",
            "id": 6752317,
            "avatar_url": "https://avatars.githubusercontent.com/u/6752317?v=3",
            "gravatar_id": "",
            "url": "https://api.github.com/users/baxterthehacker",
            "html_url": "https://github.com/baxterthehacker",
            "type": "User",
            "site_admin": False
        },
        "commits": [
            {
                "id": "0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c",
                "tree_id": "f9d2a07e9488b91af2641b26b9407fe22a451433",
                "distinct": True,
                "message": "Update README.md",
                "timestamp": "2015-05-05T19:40:15-04:00",
                "url": "https://github.com/baxterthehacker/public-repo/commit/0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c",
                "author": {
                    "name": "baxterthehacker",
                    "email": "baxterthehacker@users.noreply.github.com",
                    "username": "baxterthehacker"
                },
                "committer": {
                    "name": "baxterthehacker",
                    "email": "baxterthehacker@users.noreply.github.com",
                    "username": "baxterthehacker"
                },
                "added": [],
                "removed": [],
                "modified": ["README.md"]
            }
        ],
        "head_commit": {
            "id": "0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c",
            "tree_id": "f9d2a07e9488b91af2641b26b9407fe22a451433",
            "distinct": True,
            "message": "Update README.md",
            "timestamp": "2015-05-05T19:40:15-04:00",
            "url": "https://github.com/baxterthehacker/public-repo/commit/0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c",
            "author": {
                "name": "baxterthehacker",
                "email": "baxterthehacker@users.noreply.github.com",
                "username": "baxterthehacker"
            },
            "committer": {
                "name": "baxterthehacker",
                "email": "baxterthehacker@users.noreply.github.com",
                "username": "baxterthehacker"
            },
            "added": [],
            "removed": [],
            "modified": ["README.md"]
        }
    }


@patch("shared.config.celery_app.celery_app.send_task")
def test_real_github_push_webhook(mock_send_task):
    """Test with realistic GitHub push webhook payload."""
    # Mock Celery task
    mock_send_task.return_value = AsyncMock()

    payload = _real_github_push_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "repository" in data
    assert data["repository"] == "baxterthehacker/public-repo"
    assert "ref" in data
    assert data["ref"] == "refs/heads/changes"
    assert "commits" in data
    assert len(data["commits"]) == 1

    # Verify commit details
    commit = data["commits"][0]
    assert commit["id"] == "0d1a26e67d8f5eaf1f6ba5c57fc3c7d91ac0fd1c"
    assert commit["message"] == "Update README.md"
    assert commit["author"] == "baxterthehacker"

    # Verify Celery task was called (just check task name and payload, not headers)
    mock_send_task.assert_called_once()
    call_args = mock_send_task.call_args
    assert call_args[0][0] == "webhook_receiver.process_webhook_async"
    assert call_args[1]["args"][0] == payload  # First arg is the payload
    # Headers are lowercased by TestClient, so just verify the essential ones exist
    passed_headers = call_args[1]["args"][1]
    assert "x-github-event" in passed_headers
    assert passed_headers["x-github-event"] == "push"


@patch("shared.config.celery_app.celery_app.send_task")
def test_github_force_push_webhook(mock_send_task):
    """Test GitHub force push webhook."""
    mock_send_task.return_value = AsyncMock()

    payload = _real_github_push_payload()
    payload["forced"] = True
    payload["before"] = "0000000000000000000000000000000000000000"  # Force push indicator

    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "baxterthehacker/public-repo"

    # Should still process force pushes
    mock_send_task.assert_called_once()


def test_github_ping_webhook():
    """Test GitHub ping webhook (repository setup)."""
    payload = {
        "zen": "Keep it logically awesome.",
        "hook_id": 12345,
        "hook": {
            "type": "Repository",
            "id": 12345,
            "events": ["push"],
            "active": True,
            "config": {
                "content_type": "json",
                "insecure_ssl": "0",
                "url": "http://example.com/webhook"
            }
        },
        "repository": {
            "id": 35129377,
            "name": "public-repo",
            "full_name": "baxterthehacker/public-repo",
            "owner": {
                "login": "baxterthehacker",
                "id": 6752317
            }
        }
    }

    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "ping",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 202  # Ping events are ignored but accepted
    assert "ignored" in response.json()["detail"].lower()


@patch("shared.config.celery_app.celery_app.send_task")
def test_large_payload_handling(mock_send_task):
    """Test handling of large webhook payloads."""
    # Create a payload with many commits
    payload = _real_github_push_payload()
    large_commits = []

    for i in range(50):  # 50 commits
        commit = {
            "id": f"commit{i:02d}{'a' * 32}",
            "tree_id": f"tree{i:02d}{'b' * 35}",
            "distinct": True,
            "message": f"Commit #{i} with a very long message " + "x" * 100,
            "timestamp": "2015-05-05T19:40:15-04:00",
            "url": f"https://github.com/baxterthehacker/public-repo/commit/commit{i:02d}",
            "author": {
                "name": "baxterthehacker",
                "email": "baxterthehacker@users.noreply.github.com",
                "username": "baxterthehacker"
            },
            "committer": {
                "name": "baxterthehacker",
                "email": "baxterthehacker@users.noreply.github.com",
                "username": "baxterthehacker"
            },
            "added": [f"file{i}.txt"],
            "removed": [],
            "modified": []
        }
        large_commits.append(commit)

    payload["commits"] = large_commits
    payload["head_commit"] = large_commits[-1]

    mock_send_task.return_value = AsyncMock()

    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _create_signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook/", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Should handle all 50 commits
    assert len(data["commits"]) == 50
    assert data["repository"] == "baxterthehacker/public-repo"

    # Large payload should still trigger background processing
    mock_send_task.assert_called_once()
    call_args = mock_send_task.call_args
    assert call_args[0][0] == "webhook_receiver.process_webhook_async"
    assert call_args[1]["args"][0] == payload  # First arg is the payload
