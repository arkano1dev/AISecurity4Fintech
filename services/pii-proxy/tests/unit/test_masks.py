from fastapi.testclient import TestClient
from pii_proxy.api import make_app

client = TestClient(make_app())


def test_mask_endpoint_redacts_email_and_ssn() -> None:
    response = client.post(
        "/pii/mask",
        json={
            "text": "Contact alice@example.com or SSN 123-45-6789 before 2025-01-01.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["redacted"]
    assert "alice@example.com" not in body["redacted"]
    assert "123-45-6789" not in body["redacted"]
    assert "[EMAIL]" in body["redacted"]
    assert "[SSN]" in body["redacted"]


def test_vault_receipt_tracks_encrypted_record() -> None:
    response = client.post(
        "/pii/vault",
        json={
            "record_type": "customer_profile",
            "payload": {"email": "alice@example.com", "customer_id": "C-1001"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["receipt"]
    assert body["message"] == "stored"
    assert "alice@example.com" not in body["receipt"]
    assert "customer_id" in body["receipt"]
