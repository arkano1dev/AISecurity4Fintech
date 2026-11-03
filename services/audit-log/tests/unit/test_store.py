from __future__ import annotations

from audit_log.store import AuditLogStore


def test_append_returns_record_with_hash() -> None:
    store = AuditLogStore()
    record = store.append(actor_sub="u1", tenant_id="acme", action="query.executed", payload={"q": "hi"})
    assert record["seq"] == 1
    assert record["hash"]


def test_append_raises_on_duplicate_seq() -> None:
    store = AuditLogStore()
    store.append(actor_sub="u1", tenant_id="acme", action="query.executed", payload={"q": "hi"})
    try:
        store.append(seq=1, actor_sub="u2", tenant_id="acme", action="query.executed", payload={"q": "there"})
    except ValueError:
        return
    raise AssertionError("duplicate sequence should raise ValueError")


def test_verify_returns_valid_for_empty() -> None:
    store = AuditLogStore()
    result = store.verify()
    assert result["valid"] is True
    assert result["count"] == 0
