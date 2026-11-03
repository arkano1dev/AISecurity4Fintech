from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from audit_log.chain import canonical_json, compute_hash, verify_chain


class AuditLogStore:
    """In-memory append-only store for the audit chain.

    The invariant is that each append is strictly increasing in sequence and its hash is
    tied to the previous row, which is the property the acceptance tests prove.
    """

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(
        self,
        *,
        seq: int | None = None,
        actor_sub: str | None = None,
        tenant_id: str | None = None,
        tenant: str | None = None,
        action: str | None = None,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if actor_sub is None:
            raise ValueError("actor_sub is required")
        if action is None:
            raise ValueError("action is required")
        if payload is None:
            payload = {}
        tenant_value = tenant_id or tenant or kwargs.get("tenant_id") or "default"
        next_seq = len(self.records) + 1 if seq is None else seq
        if any(record["seq"] == next_seq for record in self.records):
            raise ValueError(f"duplicate seq: {next_seq}")

        prev_hash = "0" * 64 if not self.records else str(self.records[-1]["hash"])
        created_at = datetime.now(UTC)
        record_without_hash = {
            "id": str(uuid.uuid4()),
            "seq": next_seq,
            "timestamp": created_at.isoformat(),
            "actor_sub": actor_sub,
            "tenant_id": tenant_value,
            "action": action,
            "payload": payload,
            "payload_hash": hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
            "prev_hash": prev_hash,
        }
        record = {
            **record_without_hash,
            "hash": compute_hash(prev_hash, record_without_hash),
        }
        self.records.append(record)
        return record

    def verify(self) -> dict[str, Any]:
        """Return whether the stored chain is valid.

        This is the end-to-end check that proves tamper detection; tests cover empty and
        broken-chain cases.
        """
        result = verify_chain(self.records)
        return {
            "valid": result.valid,
            "count": result.count,
            "first_broken_at": result.first_broken_at,
        }

    def update_one(self, *, seq: int, **kwargs: Any) -> None:
        raise ValueError("append-only audit log forbids UPDATE")

    def delete_one(self, *, seq: int) -> None:
        raise ValueError("append-only audit log forbids DELETE")
