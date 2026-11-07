from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from agentflow.api import make_app
from agentflow.tools import AccountService
from agentflow.vaultrag_client import VaultragUnavailableError
from auth.api import make_app as make_auth_app
from auth.keys import get_active_private_key
from fastapi.testclient import TestClient


def _new_token(*, sub: str = "alice", scopes: list[str], audience: str = "agentflow") -> str:
    key = get_active_private_key()
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iss": "auth",
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": f"test-token-{sub}",
        "scopes": scopes,
        "scope": " ".join(scopes),
    }
    return jwt.encode(payload, key.private_key, algorithm="RS256", headers={"kid": key.key_id})


class FakeMasker:
    def mask(self, text: str) -> str:
        return text.replace("DE89370400440532013000", "[IBAN]")


class FakeVaultrag:
    def __init__(self, answer: str = "Grounded answer.", error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.questions: list[str] = []
        self.tokens: list[str] = []

    def query(self, question: str, token: str) -> dict[str, Any]:
        self.questions.append(question)
        self.tokens.append(token)
        if self.error is not None:
            raise self.error
        return {
            "answer": self.answer,
            "citations": [{"doc_id": "d", "chunk_id": "d:0", "text": "context"}],
        }


class FakeAuditor:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {"actor_sub": actor_sub, "action": action, "payload": payload}
        self.records.append(record)
        return {"id": "audit-1", "seq": len(self.records), **record}


def _client(
    auditor: FakeAuditor,
    *,
    account: AccountService | None = None,
    vaultrag: FakeVaultrag | None = None,
    pii: FakeMasker | None = None,
) -> TestClient:
    auth_client = TestClient(make_auth_app())
    return TestClient(
        make_app(
            auth_service_url="http://testserver",
            auth_service_client=auth_client,
            audit_client=auditor,
            account_service=account or AccountService(balances={"alice": 1000.0, "bob": 250.0}),
            vaultrag_client=vaultrag or FakeVaultrag(),
            pii_client=pii or FakeMasker(),
        )
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_retrieval_routes_and_audits_dispatch() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag()
    client = _client(auditor, vaultrag=vaultrag)
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
    assert body["result"]["answer"] == "Grounded answer."

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


def test_retrieval_masks_pii_before_vaultrag() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag()
    client = _client(auditor, vaultrag=vaultrag)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    client.post(
        "/chat/send",
        json={"message": "what about account DE89370400440532013000?"},
        headers=_auth(token),
    )

    # The question that reached VaultRAG was masked (defense in depth).
    assert vaultrag.questions
    assert "DE89370400440532013000" not in vaultrag.questions[0]
    assert "[IBAN]" in vaultrag.questions[0]


def test_retrieval_forwards_caller_token() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag()
    client = _client(auditor, vaultrag=vaultrag)
    token = _new_token(sub="support", scopes=["chat:send", "agent:retrieve"])

    client.post(
        "/chat/send",
        json={"message": "what is the wire transfer threshold?"},
        headers=_auth(token),
    )

    # The caller's own bearer token was forwarded to VaultRAG.
    assert vaultrag.tokens == [token]


def test_check_balance_returns_own_balance() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    token = _new_token(sub="alice", scopes=["chat:send", "agent:action"])

    response = client.post(
        "/chat/send",
        json={"message": "check my balance"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["tool"] == "check_balance"
    assert body["result"]["account"] == "alice"
    assert body["result"]["balance"] == 1000.0


def test_check_balance_does_not_leak_other_users_balance() -> None:
    auditor = FakeAuditor()
    client = _client(auditor)
    # alice asks about bob — the action is keyed by alice's JWT sub, so bob's
    # balance can never be returned.
    token = _new_token(sub="alice", scopes=["chat:send", "agent:action"])

    response = client.post(
        "/chat/send",
        json={"message": "check bob's balance"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["account"] == "alice"
    assert body["result"]["balance"] == 1000.0  # never bob's 250.0


def test_vaultrag_down_returns_503() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag(error=VaultragUnavailableError())
    client = _client(auditor, vaultrag=vaultrag)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    response = client.post(
        "/chat/send",
        json={"message": "what is the wire transfer threshold?"},
        headers=_auth(token),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "vaultrag_unavailable"
