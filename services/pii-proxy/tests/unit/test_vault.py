from __future__ import annotations

import json

from pii_proxy.vault import SecretVault


def _vault() -> SecretVault:
    return SecretVault(key=b"x" * 32)


def test_store_does_not_keep_plaintext_at_rest() -> None:
    vault = _vault()
    raw = vault.store(
        "customer_profile",
        {"email": "alice@example.com", "customer_id": "C-1001"},
    )
    receipt = json.loads(raw)["receipt"]
    record = vault._records[receipt]
    assert "payload" not in record
    assert "ciphertext" in record
    assert "nonce" in record
    assert "alice@example.com" not in str(record)


def test_get_returns_decrypted_payload_without_storage_metadata() -> None:
    vault = _vault()
    raw = vault.store(
        "customer_profile",
        {"email": "alice@example.com", "customer_id": "C-1001"},
    )
    receipt = json.loads(raw)["receipt"]
    body = vault.get(receipt)
    assert body is not None
    assert body["record_type"] == "customer_profile"
    assert body["payload"]["email"] == "alice@example.com"
    assert "nonce" not in body
    assert "ciphertext" not in body
