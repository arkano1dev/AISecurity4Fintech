from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditRecordCreate(BaseModel):
    """Request model for appending an audit record.

    The invariant is that every append must carry a visible actor, a tenant boundary,
    and a canonical payload; this is the proof the audit chain starts from a legal event.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    actor_sub: str
    tenant_id: str | None = Field(default=None)
    tenant: str | None = Field(default=None)
    action: str
    payload: dict[str, Any]

    @property
    def tenant_value(self) -> str:
        return self.tenant_id or self.tenant or "default"


class AuditRecord(BaseModel):
    """Stored record model.

    This model captures the chain invariant: each row includes its predecessor hash, its
    own hash, and a deterministic payload hash so later verification can detect tampering.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    seq: int
    timestamp: datetime
    actor_sub: str
    tenant_id: str
    action: str
    payload: dict[str, Any]
    payload_hash: str
    prev_hash: str
    hash: str
    retention_until: datetime | None = Field(default=None)


class VerificationResult(BaseModel):
    """Verification response.

    The invariant is simple: every record must be sequential, linked, and internally
    consistent; if any row breaks, the first broken index is reported.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    valid: bool
    count: int
    first_broken_at: int | None = Field(default=None)
