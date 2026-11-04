from __future__ import annotations

import base64
import hashlib
import hmac
import json

from cryptography.hazmat.primitives import serialization

from auth.jwt import verify_token
from auth.keys import get_active_private_key


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(header: dict[str, str], payload: dict[str, object], signature: bytes) -> str:
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}"
    return f"{signing_input}.{_b64url(signature)}"


def _claims() -> dict[str, object]:
    return {
        "sub": "alice",
        "iss": "auth",
        "aud": "agentflow",
        "exp": 4_102_444_800,
        "jti": "algorithm-confusion-test",
        "scopes": ["chat:send"],
    }


def test_hs256_signed_with_public_key_bytes_is_rejected() -> None:
    key = get_active_private_key()
    public_key_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    header = {"alg": "HS256", "typ": "JWT", "kid": key.key_id}
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url(json.dumps(_claims(), separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(public_key_pem, signing_input, hashlib.sha256).digest()
    result = verify_token(f"{signing_input.decode()}.{_b64url(signature)}", "agentflow")
    assert result.valid is False


def test_none_algorithm_token_is_rejected() -> None:
    key = get_active_private_key()
    token = _token(
        {"alg": "none", "typ": "JWT", "kid": key.key_id},
        _claims(),
        b"",
    )
    result = verify_token(token, "agentflow")
    assert result.valid is False