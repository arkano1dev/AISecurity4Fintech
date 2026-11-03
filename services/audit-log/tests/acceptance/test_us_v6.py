from __future__ import annotations

import hashlib
import json
from typing import Any, cast

import pytest
from audit_log.api import make_app
from audit_log.chain import canonical_json
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    app = make_app()
    return TestClient(app)


def test_audit_record_written(client: TestClient) -> None:
    response = client.post(
        "/audit/append",
        json={
            "actor_sub": "u1",
            "tenant": "acme",
            "action": "query.executed",
            "payload": {"q": "hi"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) >= {
        "id",
        "seq",
        "timestamp",
        "actor_sub",
        "tenant_id",
        "action",
        "payload_hash",
        "prev_hash",
        "hash",
    }
    assert body["seq"] == 1
    assert body["prev_hash"] == "0" * 64
    record_without_hash = {
        "id": body["id"],
        "seq": body["seq"],
        "timestamp": body["timestamp"],
        "actor_sub": body["actor_sub"],
        "tenant_id": body["tenant_id"],
        "action": body["action"],
        "payload": body["payload"],
        "payload_hash": body["payload_hash"],
        "prev_hash": body["prev_hash"],
    }
    expected_hash = hashlib.sha256(
        (body["prev_hash"] + canonical_json(record_without_hash)).encode("utf-8")
    ).hexdigest()
    assert body["hash"] == expected_hash


def test_chain_appends_correctly(client: TestClient) -> None:
    responses = [
        client.post(
            "/audit/append",
            json={
                "actor_sub": f"u{i}",
                "tenant": "acme",
                "action": "query.executed",
                "payload": {"q": f"q{i}"},
            },
        )
        for i in range(1, 4)
    ]
    records = [response.json() for response in responses]
    for index, record in enumerate(records):
        if index == 0:
            assert record["prev_hash"] == "0" * 64
        else:
            assert record["prev_hash"] == records[index - 1]["hash"]
        assert record["seq"] == index + 1


def test_chain_verification_passes(client: TestClient) -> None:
    for i in range(3):
        response = client.post(
            "/audit/append",
            json={
                "actor_sub": f"u{i}",
                "tenant": "acme",
                "action": "query.executed",
                "payload": {"q": f"q{i}"},
            },
        )
        assert response.status_code == 201

    response = client.get("/audit/verify")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["count"] >= 3
    assert payload["first_broken_at"] is None


def test_tamper_detection(client: TestClient) -> None:
    for i in range(5):
        response = client.post(
            "/audit/append",
            json={
                "actor_sub": f"u{i}",
                "tenant": "acme",
                "action": "query.executed",
                "payload": {"q": f"q{i}"},
            },
        )
        assert response.status_code == 201

    store = cast(Any, client).app.state.audit_store
    # mutate middle row directly
    target = store.records[2]
    target["payload"] = {"q": "tampered"}
    target["payload_hash"] = hashlib.sha256(
        json.dumps(
            target["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    target["hash"] = hashlib.sha256(
        (
            target["prev_hash"]
            + canonical_json(
                {
                    "id": target["id"],
                    "seq": target["seq"],
                    "timestamp": target["timestamp"],
                    "actor_sub": target["actor_sub"],
                    "tenant_id": target["tenant_id"],
                    "action": target["action"],
                    "payload": target["payload"],
                    "payload_hash": target["payload_hash"],
                    "prev_hash": target["prev_hash"],
                }
            )
        ).encode("utf-8")
    ).hexdigest()

    response = client.get("/audit/verify")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["first_broken_at"] == 3


def test_append_only_enforced_at_db_layer(client: TestClient) -> None:
    client.post(
        "/audit/append",
        json={
            "actor_sub": "u1",
            "tenant": "acme",
            "action": "query.executed",
            "payload": {"q": "hi"},
        },
    )
    store = cast(Any, client).app.state.audit_store
    with pytest.raises(ValueError):
        store.update_one(seq=1, payload={"q": "hacked"})
    with pytest.raises(ValueError):
        store.delete_one(seq=1)


def test_canonical_json_is_deterministic() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    left_json = canonical_json(left)
    right_json = canonical_json(right)

    assert left_json == right_json
    assert (
        hashlib.sha256(left_json.encode("utf-8")).hexdigest()
        == hashlib.sha256(right_json.encode("utf-8")).hexdigest()
    )
