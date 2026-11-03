from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from audit_log.models import VerificationResult


def canonical_json(obj: object) -> str:
    """Return the canonical JSON encoding for an object.

    Why it exists: the hash chain must be deterministic across process restarts and key
    insertion order; this test proves that record hashing is order-independent.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str, payload: object) -> str:
    """Compute the deterministic SHA-256 hash for a chain payload.

    The invariant is that the previous hash and canonical payload must be exactly what the
    chain stores; the unit tests assert the first record starts from zeros and later links.
    """
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()


def verify_chain(records: Sequence[Mapping[str, object]]) -> VerificationResult:
    """Verify that recorded hashes form an append-only chain.

    Why it exists: this enforces the tamper-evidence guarantee; the acceptance tests prove
    a valid chain passes and a mutated middle row fails at the first broken index.
    """
    if not records:
        return VerificationResult(valid=True, count=0, first_broken_at=None)

    for idx, record in enumerate(records):
        seq_raw = record.get("seq", idx + 1)
        if not isinstance(seq_raw, int):
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)
        seq_value = seq_raw
        expected_seq = idx + 1
        if seq_value != expected_seq:
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)

        prev_hash = str(record.get("prev_hash", ""))
        expected_prev = "0" * 64 if idx == 0 else str(records[idx - 1]["hash"])
        if prev_hash != expected_prev:
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)

        payload_raw = record.get("payload", {})
        if not isinstance(payload_raw, dict):
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)
        payload = dict(payload_raw)
        payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        if str(record.get("payload_hash")) != payload_hash:
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)

        record_without_hash = {
            "id": record.get("id"),
            "seq": seq_value,
            "timestamp": record.get("timestamp"),
            "actor_sub": record.get("actor_sub"),
            "tenant_id": record.get("tenant_id"),
            "action": record.get("action"),
            "payload": payload,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
        }
        expected_hash = compute_hash(prev_hash, record_without_hash)
        if str(record.get("hash")) != expected_hash:
            return VerificationResult(valid=False, count=len(records), first_broken_at=idx)

    return VerificationResult(valid=True, count=len(records), first_broken_at=None)
