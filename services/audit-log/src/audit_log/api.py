from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI

from audit_log.models import AuditRecordCreate
from audit_log.store import AuditLogStore


def make_app(store: AuditLogStore | None = None) -> FastAPI:
    """Create the FastAPI application for the audit log service.

    The invariant is that the app exposes the append and verify endpoints for the same
    store logic the tests exercise; this proves the API matches the chain contract.
    """
    app = FastAPI(title="Audit Log Service")
    app.state.audit_store = store or AuditLogStore()

    @app.post("/audit/append", status_code=201)
    def append_record(payload: AuditRecordCreate) -> dict[str, Any]:
        record = app.state.audit_store.append(
            actor_sub=payload.actor_sub,
            tenant_id=payload.tenant_value,
            action=payload.action,
            payload=payload.payload,
        )
        return cast(dict[str, Any], record)

    @app.get("/audit/verify")
    def verify_chain() -> dict[str, Any]:
        return cast(dict[str, Any], app.state.audit_store.verify())

    return app
