from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from agentflow.api import make_app
from auth.api import make_app as make_auth_app
from auth.keys import get_active_private_key


def test_cached_valid_token_still_verifies_when_auth_service_unavailable() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    key = get_active_private_key()
    token = jwt.encode(
        {
            "sub": "alice",
            "iss": "auth",
            "aud": "agentflow",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": "cached-token-1",
            "scopes": ["chat:send", "account:read"],
            "scope": "chat:send account:read",
        },
        key.private_key,
        algorithm="RS256",
        headers={"kid": key.key_id},
    )

    response = agentflow_client.get(
        "/chat/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["sub"] == "alice"
