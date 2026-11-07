from __future__ import annotations

import hashlib
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from audit_log.chain import canonical_json, compute_hash, verify_chain


@st.composite
def record_payloads(draw: st.DrawFn) -> list[dict[str, object]]:
    length = draw(st.integers(min_value=0, max_value=10))
    items: list[dict[str, object]] = []
    for i in range(length):
        payload = {
            "value": draw(st.integers(min_value=0, max_value=1000)),
            "label": f"r{i}",
        }
        items.append(payload)
    return items


@given(record_payloads())
def test_verify_chain_for_random_records(records: list[dict[str, object]]) -> None:
    chain: list[dict[str, Any]] = []
    prev_hash = "0" * 64

    for idx, payload in enumerate(records, start=1):
        payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        record: dict[str, Any] = {
            "id": f"r-{idx}",
            "seq": idx,
            "timestamp": "2024-01-01T00:00:00Z",
            "actor_sub": "user",
            "tenant_id": "acme",
            "action": "query.executed",
            "payload": payload,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
        }
        record["hash"] = str(
            compute_hash(
                prev_hash,
                {k: v for k, v in record.items() if k != "hash"},
            )
        )
        chain.append(record)
        prev_hash = str(record["hash"])

    result = verify_chain(chain)
    assert result.valid is True
    assert result.first_broken_at is None


def test_verify_chain_fails_after_single_flipped_byte() -> None:
    chain: list[dict[str, Any]] = []
    prev_hash = "0" * 64

    for idx in range(1, 4):
        payload = {"value": idx, "label": f"r{idx}"}
        payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        record: dict[str, Any] = {
            "id": f"r-{idx}",
            "seq": idx,
            "timestamp": "2024-01-01T00:00:00Z",
            "actor_sub": "user",
            "tenant_id": "acme",
            "action": "query.executed",
            "payload": payload,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
        }
        record["hash"] = str(
            compute_hash(
                prev_hash,
                {k: v for k, v in record.items() if k != "hash"},
            )
        )
        chain.append(record)
        prev_hash = str(record["hash"])

    tampered: dict[str, Any] = dict(chain[1])
    tampered["payload"] = {"value": 999, "label": "r2"}
    tampered["payload_hash"] = hashlib.sha256(
        canonical_json(tampered["payload"]).encode("utf-8")
    ).hexdigest()
    tampered["hash"] = compute_hash(
        str(tampered["prev_hash"]),
        {k: v for k, v in tampered.items() if k != "hash"},
    )
    chain[1] = tampered

    result = verify_chain(chain)
    assert result.valid is False
    assert result.first_broken_at == 2
