from __future__ import annotations

import base64
import json
import os
import secrets
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecretVault:
    def __init__(self, key: bytes | None = None) -> None:
        key_material = key or self._load_key()
        self._cipher = AESGCM(key_material)
        self._records: dict[str, dict[str, object]] = {}

    @staticmethod
    def _load_key() -> bytes:
        configured = os.environ.get("PII_PROXY_KEY")
        if configured:
            return base64.urlsafe_b64decode(configured.encode() + b"=" * (-len(configured) % 4))
        return sha256(b"pii-proxy-default-key").digest()[:32]

    def store(self, record_type: str, payload: dict[str, object]) -> str:
        receipt = secrets.token_urlsafe(18)
        nonce = os.urandom(12)
        body = {
            "record_type": record_type,
            "payload": payload,
            "payload_hash": sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        ciphertext = self._cipher.encrypt(nonce, json.dumps(body, sort_keys=True).encode(), None)
        self._records[receipt] = {
            "record_type": record_type,
            "payload": payload,
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }
        return json.dumps(
            {
                "receipt": receipt,
                "record_type": record_type,
                "customer_id": str(payload.get("customer_id") or "unknown"),
                "message": "stored",
            },
            sort_keys=True,
        )

    def get(self, receipt: str) -> dict[str, object] | None:
        return self._records.get(receipt)
