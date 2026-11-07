from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from agentflow.api import make_app
from auth.api import make_app as make_auth_app
from auth.keys import get_active_private_key


def _new_token(*, scopes: list[str], exp_delta: timedelta, audience: str = "agentflow") -> str:
    key = get_active_private_key()
    now = datetime.now(UTC)
    payload = {
        "sub": "alice",
        "iss": "auth",
        "aud": audience,
        "exp": int((now + exp_delta).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "test-token-1",
        "scopes": scopes,
        "scope": " ".join(scopes),
    }
    return jwt.encode(payload, key.private_key, algorithm="RS256", headers={"kid": key.key_id})


def test_valid_login_returns_session_token() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    response = agentflow_client.post(
        "/chat/session",
        json={"username": "alice", "password": "correct-horse"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 900
    assert payload["access_token"]


def test_expired_token_rejected() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    token = _new_token(scopes=["chat:send", "account:read"], exp_delta=timedelta(minutes=-5))
    response = agentflow_client.get(
        "/chat/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "token_expired"


def test_tampered_token_rejected() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    valid = _new_token(scopes=["chat:send", "account:read"], exp_delta=timedelta(minutes=5))
    parts = valid.split(".")
    tampered = parts[0] + "." + parts[1] + "." + "Z" * 64
    response = agentflow_client.get(
        "/chat/whoami",
        headers={"Authorization": f"Bearer {tampered}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_signature"


def test_wrong_scope_rejected() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    token = _new_token(scopes=["chat:send"], exp_delta=timedelta(minutes=5))
    response = agentflow_client.get(
        "/chat/account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_valid_scope_accepted() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    token = _new_token(scopes=["chat:send", "account:read"], exp_delta=timedelta(minutes=5))
    response = agentflow_client.get(
        "/chat/account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["sub"] == "alice"


def test_self_signed_token_rejected() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    other_key = get_active_private_key()
    token = jwt.encode(
        {
            "sub": "alice",
            "iss": "evil",
            "aud": "agentflow",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": "evil-token",
            "scopes": ["chat:send"],
            "scope": "chat:send",
        },
        other_key.private_key,
        algorithm="RS256",
        headers={"kid": "evil-kid"},
    )
    response = agentflow_client.get(
        "/chat/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] in {
        "invalid_signature",
        "invalid_audience",
        "invalid_algorithm",
    }
