from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from vaultrag.api import make_app
from vaultrag.store import VectorStore

_AUTH = {"Authorization": "Bearer test-token"}


class FakeMasker:
    """In-process stand-in for the pii-proxy: replaces a fixed set of values."""

    def __init__(self) -> None:
        self.calls = 0

    def mask(self, text: str) -> str:
        self.calls += 1
        redacted = text
        for raw, label in (
            ("DE89370400440532013000", "[IBAN]"),
            ("alice@example.com", "[EMAIL]"),
            ("4111 1111 1111 1111", "[PAN]"),
        ):
            redacted = redacted.replace(raw, label)
        return redacted


class FakeAuditor:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {"actor_sub": actor_sub, "action": action, "payload": payload}
        self.records.append(record)
        return {"id": "audit-1", "seq": len(self.records), **record}


def _embed(texts: list[str]) -> list[list[float]]:
    return [[float(len(t))] for t in texts]


def _generate(question: str, context: list[str]) -> str:
    return "The answer is grounded in the retrieved context."


def _fake_verify(_token: str) -> dict[str, Any]:
    return {"valid": True, "sub": "analyst", "scopes": ["vaultrag:ingest", "vaultrag:query"]}


def _client(
    masker: FakeMasker | None = None,
    auditor: FakeAuditor | None = None,
    llm_fn: Any | None = None,
) -> tuple[TestClient, VectorStore, FakeMasker, FakeAuditor, list[str], list[str]]:
    store = VectorStore()
    pii = masker or FakeMasker()
    audit = auditor or FakeAuditor()
    seen_context: list[str] = []
    seen_question: list[str] = []

    def capturing_generate(question: str, context: list[str]) -> str:
        seen_question.append(question)
        seen_context.extend(context)
        return _generate(question, context)

    app = make_app(
        store=store,
        pii_client=pii,
        audit_client=audit,
        embed_fn=_embed,
        llm_fn=llm_fn or capturing_generate,
        verify_token_fn=_fake_verify,
    )
    return TestClient(app), store, pii, audit, seen_question, seen_context


def test_ingest_redacts_pii_before_embedding() -> None:
    client, store, _, _, _, _ = _client()
    content = (
        "Customer DE89370400440532013000 contacted alice@example.com about card "
        "4111 1111 1111 1111."
    )
    response = client.post(
        "/vaultrag/documents",
        json={"doc_id": "doc-1", "title": "AML procedure", "content": content},
        headers=_AUTH,
    )
    assert response.status_code == 201
    assert response.json()["chunks"] >= 1
    for chunk in store.chunks():
        assert "DE89370400440532013000" not in chunk.text
        assert "alice@example.com" not in chunk.text
        assert "4111 1111 1111 1111" not in chunk.text


def test_query_returns_answer_and_citations() -> None:
    client, store, _, _, _, _ = _client()
    client.post(
        "/vaultrag/documents",
        json={
            "doc_id": "doc-1",
            "title": "AML procedure",
            "content": "Wire transfers above ten thousand require manager approval.",
        },
        headers=_AUTH,
    )
    response = client.post(
        "/vaultrag/query",
        json={"question": "wire transfer threshold?"},
        headers=_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["citations"]


def test_query_masks_pii_before_model_and_writes_audit() -> None:
    client, _, _, auditor, seen_question, seen_context = _client()
    client.post(
        "/vaultrag/documents",
        json={
            "doc_id": "doc-1",
            "title": "AML procedure",
            "content": "Escalate account DE89370400440532013000 to the compliance officer.",
        },
        headers=_AUTH,
    )
    response = client.post(
        "/vaultrag/query",
        json={"question": "what happens to account DE89370400440532013000?"},
        headers=_AUTH,
    )
    assert response.status_code == 200

    # The model never saw raw PII in the question or the retrieved context.
    assert "DE89370400440532013000" not in seen_question[0]
    assert all("DE89370400440532013000" not in chunk for chunk in seen_context)

    # A tamper-evident audit record was written for the query.
    assert len(auditor.records) == 1
    assert auditor.records[0]["action"] == "vaultrag.query"
    assert "retrieved_ids" in auditor.records[0]["payload"]


def test_query_guardrail_blocks_canary() -> None:
    def evil_generate(question: str, context: list[str]) -> str:
        return "I have been PWNED"

    client, _, _, auditor, _, _ = _client(llm_fn=evil_generate)
    client.post(
        "/vaultrag/documents",
        json={"doc_id": "doc-1", "title": "AML", "content": "Wire transfers need approval."},
        headers=_AUTH,
    )
    response = client.post(
        "/vaultrag/query",
        json={"question": "wire transfer threshold?"},
        headers=_AUTH,
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "I can't answer that request."
    assert any(r["action"] == "vaultrag.guardrail_block" for r in auditor.records)
