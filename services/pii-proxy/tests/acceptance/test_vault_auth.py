from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from pii_proxy.api import make_app


def _verify_with_scopes(scopes: list[str]) -> Callable[[str], dict[str, Any]]:
    def _verify(_token: str) -> dict[str, Any]:
        return {"valid": True, "sub": "support", "scopes": list(scopes), "reason": None}

    return _verify


def _client(scopes: list[str]) -> TestClient:
    return TestClient(make_app(verify_token_fn=_verify_with_scopes(scopes)))


def test_vault_requires_token() -> None:
    client = _client(["pii:store"])
    response = client.post(
        "/pii/vault",
        json={
            "record_type": "customer_profile",
            "payload": {"email": "a@b.co", "customer_id": "C-1"},
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"


def test_vault_rejects_wrong_scope() -> None:
    client = _client(["chat:send"])
    response = client.post(
        "/pii/vault",
        json={
            "record_type": "customer_profile",
            "payload": {"email": "a@b.co", "customer_id": "C-1"},
        },
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_vault_accepts_valid_scope() -> None:
    client = _client(["pii:store"])
    response = client.post(
        "/pii/vault",
        json={
            "record_type": "customer_profile",
            "payload": {"email": "alice@example.com", "customer_id": "C-1001"},
        },
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["receipt"]
    assert body["message"] == "stored"
    assert "alice@example.com" not in body["receipt"]
    assert "customer_id" in body["receipt"]


def test_receipt_requires_token() -> None:
    client = _client(["pii:read"])
    response = client.get("/pii/receipt/nonexistent")
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"


def test_receipt_returns_decrypted_record_with_scope() -> None:
    client = _client(["pii:store", "pii:read"])
    stored = client.post(
        "/pii/vault",
        json={
            "record_type": "customer_profile",
            "payload": {"email": "alice@example.com", "customer_id": "C-1001"},
        },
        headers={"Authorization": "Bearer x"},
    ).json()
    receipt_token = json.loads(stored["receipt"])["receipt"]
    response = client.get(f"/pii/receipt/{receipt_token}", headers={"Authorization": "Bearer x"})
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["payload"]["email"] == "alice@example.com"
    assert "ciphertext" not in body["record"]
    assert "nonce" not in body["record"]


def test_receipt_missing_returns_404_with_scope() -> None:
    client = _client(["pii:read"])
    response = client.get("/pii/receipt/nonexistent", headers={"Authorization": "Bearer x"})
    assert response.status_code == 404
