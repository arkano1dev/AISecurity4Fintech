from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from auth.api import make_app
from auth.deps import require_auth
from auth.keys import get_active_private_key, get_public_jwk_set
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

client = TestClient(make_app())


def test_valid_credentials_return_scoped_jwt() -> None:
    response = client.post("/auth/token", json={"username": "alice", "password": "correct-horse"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 900
    assert "access_token" in body

    token = body["access_token"]
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["sub"] == "alice"
    assert payload["iss"] == "auth"
    assert payload["aud"] == "agentflow"
    assert payload["jti"]
    assert payload["scopes"] == ["chat:send", "account:read"]
    assert payload["exp"] > datetime.now(UTC).timestamp()

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"
    assert header["kid"]

    private_key = get_active_private_key()
    assert jwt.decode(
        token,
        private_key.public_key(),
        algorithms=["RS256"],
        audience="agentflow",
        issuer="auth",
    )


def test_wrong_password_is_rejected() -> None:
    response = client.post("/auth/token", json={"username": "alice", "password": "bad"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


def test_unknown_user_is_indistinguishable_from_wrong_password() -> None:
    response = client.post("/auth/token", json={"username": "nobody", "password": "bad"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


def test_expired_token_rejected_at_verify() -> None:
    private_key = get_active_private_key()
    expired = jwt.encode(
        {
            "sub": "alice",
            "scopes": ["chat:send"],
            "iss": "auth",
            "aud": "agentflow",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "jti": "expired-token-1",
        },
        private_key.private_key,
        algorithm="RS256",
        headers={"kid": private_key.key_id},
    )
    response = client.post("/auth/verify", json={"token": expired})
    assert response.status_code == 401
    assert response.json() == {"valid": False, "reason": "token_expired"}


def test_tampered_signature_rejected() -> None:
    valid = client.post(
        "/auth/token", json={"username": "alice", "password": "correct-horse"}
    ).json()["access_token"]
    parts = valid.split(".")
    signature = bytearray(base64.urlsafe_b64decode(parts[2] + "=="))
    signature[-1] ^= 1
    changed_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    tampered = parts[0] + "." + parts[1] + "." + changed_signature
    response = client.post("/auth/verify", json={"token": tampered})
    assert response.status_code == 401
    assert response.json() == {"valid": False, "reason": "invalid_signature"}


def test_jwks_serves_current_public_key() -> None:
    response = client.get("/auth/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data and len(data["keys"]) >= 1
    jwk = data["keys"][0]
    assert jwk["kty"] == "RSA"
    assert jwk["alg"] == "RS256"
    assert jwk["use"] == "sig"
    assert jwk["kid"]
    assert "n" in jwk and "e" in jwk

    expected = get_public_jwk_set()["keys"][0]
    assert jwk["n"] == expected["n"]
    assert jwk["e"] == expected["e"]


def test_wrong_audience_rejected() -> None:
    private_key = get_active_private_key()
    token = jwt.encode(
        {
            "sub": "alice",
            "scopes": ["chat:send"],
            "iss": "auth",
            "aud": "vaultrag",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "jti": "wrong-aud-1",
        },
        private_key.private_key,
        algorithm="RS256",
        headers={"kid": private_key.key_id},
    )
    response = client.post("/auth/verify", json={"token": token})
    assert response.status_code == 401
    assert response.json() == {"valid": False, "reason": "invalid_audience"}


def test_expired_token_rejected_by_protected_dependency() -> None:
    app = FastAPI()

    @app.get("/protected-dependency")
    def protected(_: Annotated[dict[str, Any], Depends(require_auth())]) -> dict[str, bool]:
        return {"ok": True}

    private_key = get_active_private_key()
    expired = jwt.encode(
        {
            "sub": "alice",
            "scopes": ["chat:send"],
            "iss": "auth",
            "aud": "agentflow",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "jti": "expired-protected-1",
        },
        private_key.private_key,
        algorithm="RS256",
        headers={"kid": private_key.key_id},
    )
    response = TestClient(app).get(
        "/protected-dependency", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401
