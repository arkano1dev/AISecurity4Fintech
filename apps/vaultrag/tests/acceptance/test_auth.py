from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from vaultrag.api import make_app


def _verify_with_scopes(scopes: list[str]) -> Callable[[str], dict[str, Any]]:
    def _verify(_token: str) -> dict[str, Any]:
        return {"valid": True, "sub": "analyst", "scopes": scopes}

    return _verify


def _client(scopes: list[str]) -> TestClient:
    return TestClient(make_app(verify_token_fn=_verify_with_scopes(scopes)))


def test_query_requires_token() -> None:
    client = _client(["vaultrag:query"])
    response = client.post("/vaultrag/query", json={"question": "hi"})
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"


def test_query_requires_vaultrag_query_scope() -> None:
    client = _client(["chat:send"])  # wrong scope
    response = client.post(
        "/vaultrag/query",
        json={"question": "hi"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_ingest_requires_vaultrag_ingest_scope() -> None:
    client = _client(["vaultrag:query"])  # has query, not ingest
    response = client.post(
        "/vaultrag/documents",
        json={"doc_id": "d", "title": "t", "content": "some content"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_scope"


def test_query_with_valid_scope_passes_auth() -> None:
    client = _client(["vaultrag:query"])
    # Empty store -> 409, which proves auth passed (got past the dependency).
    response = client.post(
        "/vaultrag/query",
        json={"question": "hi"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 409
