from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from agentflow.api import make_app
from agentflow.llm import AgentDecision, LlmError
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class FakeMasker:
    def mask(self, text: str) -> str:
        return text.replace("DE89370400440532013000", "[IBAN]")


class FakeVaultrag:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.questions: list[str] = []
        self.tokens: list[str] = []

    def query(self, question: str, token: str) -> dict[str, Any]:
        if self.error is not None:
            raise self.error
        self.questions.append(question)
        self.tokens.append(token)
        return {
            "answer": "cited answer",
            "citations": [{"doc_id": "d", "chunk_id": "d:0", "text": "ctx"}],
        }


class FakeAuditor:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.records.append({"actor_sub": actor_sub, "action": action, "payload": payload})
        return {"id": "a", "seq": len(self.records)}


class FakeLlm:
    def __init__(self, decisions: Sequence[AgentDecision | Exception]) -> None:
        self._decisions = list(decisions)
        self.questions: list[str] = []

    def decide(self, question: str, history: list[dict[str, Any]]) -> AgentDecision:
        self.questions.append(question)
        if not self._decisions:
            raise LlmError("no more decisions")
        item = self._decisions.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(
    auditor: FakeAuditor,
    *,
    account: AccountService | None = None,
    vaultrag: FakeVaultrag | None = None,
    pii: FakeMasker | None = None,
    llm: FakeLlm | None = None,
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
            llm_client=llm or FakeLlm([AgentDecision(action="final", answer="ok")]),
        )
    )


def _final(answer: str = "done") -> AgentDecision:
    return AgentDecision(action="final", answer=answer)


def _tool(name: Literal["retrieve", "freeze_card", "check_balance"]) -> AgentDecision:
    return AgentDecision(action="tool_call", tool=name)


def test_retrieval_flow_through_llm() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag()
    llm = FakeLlm([_tool("retrieve"), _final("The threshold is ten thousand euro.")])
    client = _client(auditor, vaultrag=vaultrag, llm=llm)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    response = client.post(
        "/chat/send", json={"message": "wire transfer threshold?"}, headers=_auth(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "llm"
    assert body["intent"] == "final"
    assert body["answer"] == "The threshold is ten thousand euro."

    assert any(r["action"] == "agentflow.dispatch" for r in auditor.records)
    actions = [r for r in auditor.records if r["action"] == "agentflow.action"]
    assert actions and actions[0]["payload"]["tool"] == "retrieve"


def test_freeze_flow_audits_sub_keyed_tool() -> None:
    auditor = FakeAuditor()
    llm = FakeLlm([_tool("freeze_card"), _final("Your card is frozen.")])
    client = _client(auditor, llm=llm)
    token = _new_token(sub="alice", scopes=["chat:send", "agent:action"])

    response = client.post("/chat/send", json={"message": "freeze my card"}, headers=_auth(token))

    assert response.status_code == 200
    actions = [r for r in auditor.records if r["action"] == "agentflow.action"]
    assert actions and actions[0]["payload"]["tool"] == "freeze_card"
    assert actions[0]["payload"]["account"] == "alice"


def test_balance_flow_is_sub_keyed_not_message() -> None:
    auditor = FakeAuditor()
    llm = FakeLlm([_tool("check_balance"), _final("Your balance is 1000.0.")])
    client = _client(auditor, llm=llm)
    # alice asks about bob — the tool is keyed by alice's JWT sub, never the message.
    token = _new_token(sub="alice", scopes=["chat:send", "agent:action"])

    response = client.post(
        "/chat/send", json={"message": "check bob's balance"}, headers=_auth(token)
    )

    assert response.status_code == 200
    actions = [r for r in auditor.records if r["action"] == "agentflow.action"]
    assert actions and actions[0]["payload"]["account"] == "alice"


def test_action_without_scope_rejected() -> None:
    auditor = FakeAuditor()
    llm = FakeLlm([_tool("freeze_card"), _final("done")])
    client = _client(auditor, llm=llm)
    token = _new_token(scopes=["chat:send"])  # no agent:action

    response = client.post("/chat/send", json={"message": "freeze my card"}, headers=_auth(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_retrieval_without_scope_rejected() -> None:
    auditor = FakeAuditor()
    llm = FakeLlm([_tool("retrieve"), _final("done")])
    client = _client(auditor, llm=llm)
    token = _new_token(scopes=["chat:send"])  # no agent:retrieve

    response = client.post(
        "/chat/send", json={"message": "wire transfer threshold?"}, headers=_auth(token)
    )

    assert response.status_code == 403


def test_masks_before_model_and_vaultrag() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag()
    llm = FakeLlm([_tool("retrieve"), _final("done")])
    client = _client(auditor, vaultrag=vaultrag, llm=llm)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    client.post(
        "/chat/send",
        json={"message": "what about account DE89370400440532013000?"},
        headers=_auth(token),
    )

    assert llm.questions and "DE89370400440532013000" not in llm.questions[0]
    assert vaultrag.questions and "DE89370400440532013000" not in vaultrag.questions[0]


def test_llm_failure_falls_back_to_keyword() -> None:
    auditor = FakeAuditor()
    llm = FakeLlm([LlmError("model unavailable")])
    client = _client(auditor, llm=llm)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    response = client.post(
        "/chat/send",
        json={"message": "what is the wire transfer threshold?"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["agent"] == "retrieval"


def test_vaultrag_down_returns_503() -> None:
    auditor = FakeAuditor()
    vaultrag = FakeVaultrag(error=VaultragUnavailableError())
    llm = FakeLlm([_tool("retrieve"), _final("done")])
    client = _client(auditor, vaultrag=vaultrag, llm=llm)
    token = _new_token(scopes=["chat:send", "agent:retrieve"])

    response = client.post(
        "/chat/send",
        json={"message": "wire transfer threshold?"},
        headers=_auth(token),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "vaultrag_unavailable"
