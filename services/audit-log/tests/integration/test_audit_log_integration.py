from __future__ import annotations

import pytest

from audit_log.store import AuditLogStore


@pytest.mark.skip(
    reason=(
        "Postgres integration requires Docker and testcontainers; kept as an "
        "explicit W7 readiness test."
    )
)
def test_append_and_verify_roundtrip_against_real_postgres() -> None:
    store = AuditLogStore()
    for idx in range(3):
        store.append(
            actor_sub=f"u{idx}",
            tenant_id="acme",
            action="query.executed",
            payload={"q": f"q{idx}"},
        )
    result = store.verify()
    assert result["valid"] is True


@pytest.mark.skip(
    reason=(
        "DB trigger test is intentionally deferred to the Postgres-backed integration environment."
    )
)
def test_db_trigger_blocks_update() -> None:
    store = AuditLogStore()
    with pytest.raises(ValueError):
        store.update_one(seq=1)


@pytest.mark.skip(
    reason=(
        "DB trigger test is intentionally deferred to the Postgres-backed integration environment."
    )
)
def test_db_trigger_blocks_delete() -> None:
    store = AuditLogStore()
    with pytest.raises(ValueError):
        store.delete_one(seq=1)
