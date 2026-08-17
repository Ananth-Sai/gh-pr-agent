import hashlib
import hmac
import json
from fastapi.testclient import TestClient
from main import app
import routers.webhook as webhook_module

client = TestClient(app)
TEST_SECRET = "test_webhook_secret_key"


def generate_signature(body_bytes: bytes, secret: str) -> str:
    return (
        "sha256="
        + hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    )


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "active", "service": "GitHub PR Agent"}


def test_webhook_missing_signature(monkeypatch):
    monkeypatch.setattr(webhook_module, "WEBHOOK_SECRET", TEST_SECRET)
    response = client.post("/webhook", json={"action": "opened"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Missing signature"


def test_webhook_invalid_signature(monkeypatch):
    monkeypatch.setattr(webhook_module, "WEBHOOK_SECRET", TEST_SECRET)
    payload = {"action": "opened"}
    response = client.post(
        "/webhook",
        json=payload,
        headers={"x-hub-signature-256": "sha256=invalid_hash"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid signature"


def test_webhook_valid_signature_accepted(monkeypatch):
    # Patch the loaded secret directly in the webhook module
    monkeypatch.setattr(webhook_module, "WEBHOOK_SECRET", TEST_SECRET)

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 99,
            "title": "Test PR",
            "head": {"ref": "feature-test", "sha": "abc1234"},
        },
        "repository": {"full_name": "owner/repo"},
    }
    # Encode explicit raw bytes so HMAC matches the exact wire payload
    body_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_signature(body_bytes, TEST_SECRET)

    response = client.post(
        "/webhook",
        content=body_bytes,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": signature,
            "x-github-event": "pull_request",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"