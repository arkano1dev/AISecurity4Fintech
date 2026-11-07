from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from agentflow.api import make_app
from auth.api import make_app as make_auth_app
from auth.keys import get_active_private_key
from fastapi.testclient import TestClient


def _new_token(*, scopes: list[str], audience: str = "agentflow") -> str:
    key = get_active_private_key()
    now = datetime.now(UTC)
    payload = {
        "sub": "alice",
        "iss": "auth",
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "test-token-1",
        "scopes": scopes,
        "scope": " ".join(scopes),
    }
    return jwt.encode(payload, key.private_key, algorithm="RS256", headers={"kid": key.key_id})


class FakeAuditor:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {"actor_sub": actor_sub, "action": action, "payload": payload}
        self.records.append(record)
        return {"id": "audit-1", "seq": len(self.records), **record}


def _client(auditor: FakeAuditor) -> TestClient:
    auth_client = TestClient(make_auth_app())
    return TestClient(
        make_app(
            auth_service_url="http://testserver",
            auth_service_client=auth_client,
            audit_client=auditor,
        )
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_retrieval_routes_and_audits_dispatch() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    response = client.post(
        "/chat/send",
        json={"message": "what is the wire transfer threshold?"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "retrieval"
    assert body["agent"] == "retrieval"
    assert body["result"]["answer"]

    assert any(r["action"] == "agentflow.dispatch" for r in auditor.records)


def test_action_freezes_card_and_audits() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    token = _new_token(scopes=["chat:send", "agent:action"])

    response = client.post(
        "/chat/send",
        json={"message": "please freeze my card"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "action"
    assert body["agent"] == "action"
    assert body["result"]["status"] == "frozen"

    actions = [r for r in auditor.records if r["action"] == "agentflow.action"]
    assert len(actions) == 1
    assert actions[0]["payload"]["tool"] == "freeze_card"


def test_action_without_scope_rejected() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    token = _new_token(scopes=["chat:send"])  # no agent:action

    response = client.post(
        "/chat/send",
        json={"message": "please freeze my card"},
        headers=_auth(token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_retrieval_without_scope_rejected() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    token = _new_token(scopes=["chat:send"])  # no agent:retrieve

    response = client.post(
        "/chat/send",
        json={"message": "what is the wire transfer threshold?"},
        headers=_auth(token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"
