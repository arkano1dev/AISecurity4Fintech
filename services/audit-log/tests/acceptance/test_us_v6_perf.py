from __future__ import annotations

import time

from audit_log.store import AuditLogStore


def test_verify_chain_10k_records_in_under_2_seconds() -> None:
    store = AuditLogStore()
    for i in range(10_000):
        store.append(
            actor_sub=f"u{i}", tenant_id="acme", action="query.executed", payload={"q": f"q{i}"}
        )

    start = time.perf_counter()
    result = store.verify()
    duration = time.perf_counter() - start

    assert result["valid"] is True
    assert duration < 2.0
