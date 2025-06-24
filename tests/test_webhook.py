import hashlib
import hmac
import json
from datetime import datetime, timezone
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings, Settings

client = TestClient(app)

SECRET = "mydevsecret"


def _signature(body: bytes) -> str:
    mac = hmac.new(SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    # Clear cached settings so new env var takes effect
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _sample_payload() -> dict:
    return {
        "ref": "refs/heads/main",
        "repository": {"full_name": "octocat/Hello-World"},
        "pusher": {"name": "octocat"},
        "commits": [
            {
                "id": "d6fde92930d4715a2b49857d24b940956b26d2d3",
                "message": "Fix all the bugs",
                "url": "https://github.com/octocat/Hello-World/commit/d6fde92930d4",
                "added": ["file1.py"],
                "removed": [],
                "modified": ["file2.py"],
            }
        ],
    }


def test_valid_signature_returns_validated_event():
    payload = _sample_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": _signature(body),
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", data=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "octocat/Hello-World"
    assert data["pusher"] == "octocat"
    assert data["commits"][0]["id"] == payload["commits"][0]["id"]
    # timestamp present
    assert "timestamp" in data


def test_invalid_signature_returns_401():
    payload = _sample_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": "sha256=invalidsignature",
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", data=body, headers=headers)

    assert response.status_code == 401 