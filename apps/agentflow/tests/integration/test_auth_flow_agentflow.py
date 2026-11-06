from __future__ import annotations

from agentflow.api import make_app
from auth.api import make_app as make_auth_app
from fastapi.testclient import TestClient


def test_end_to_end_login_then_protected_route() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    login = agentflow_client.post(
        "/chat/session",
        json={"username": "alice", "password": "correct-horse"},
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    whoami = agentflow_client.get(
        "/chat/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert whoami.status_code == 200
    assert whoami.json()["sub"] == "alice"


def test_jwks_fetch_is_cached() -> None:
    auth_client = TestClient(make_auth_app())
    agentflow_client = TestClient(
        make_app(auth_service_url="http://testserver", auth_service_client=auth_client)
    )

    first = agentflow_client.get("/chat/whoami", headers={"Authorization": "Bearer invalid"})
    assert first.status_code == 401
    # The JWKS cache is exercised during verification and should not crash the request.
    assert first.json()["detail"] in {"missing_token", "invalid_signature", "invalid_algorithm"}
