from __future__ import annotations

import hashlib
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from agentflow.audit_client import AuditClient, Auditor
from agentflow.auth_client import AuthServiceClient, configure_auth_client
from agentflow.deps import require_auth
from agentflow.settings import settings
from agentflow.supervisor import InsufficientScopeError, Supervisor


class SessionRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


def make_app(
    auth_service_url: str | None = None,
    auth_service_client: Any | None = None,
    *,
    supervisor: Supervisor | None = None,
    audit_client: Auditor | None = None,
) -> FastAPI:
    app = FastAPI(title="AgentFlow")
    configured_client = AuthServiceClient(
        base_url=auth_service_url or settings.auth_service_url,
        http_client=auth_service_client,
    )
    configure_auth_client(
        base_url=auth_service_url or settings.auth_service_url,
        http_client=auth_service_client,
    )
    supervisor_obj = supervisor or Supervisor()
    audit = audit_client or AuditClient(settings.audit_log_url)

    @app.post("/chat/session", response_model=SessionResponse)
    def create_session(payload: SessionRequest) -> SessionResponse:
        result = configured_client.issue_session(payload.username, payload.password)
        return SessionResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "Bearer"),
            expires_in=int(result.get("expires_in", settings.token_ttl_seconds)),
        )

    @app.get("/chat/whoami")
    def whoami(
        details: Annotated[dict[str, Any], Depends(require_auth())],
    ) -> dict[str, Any]:
        return {"sub": details["sub"], "scopes": details["scopes"]}

    @app.get("/chat/account")
    def account(
        details: Annotated[
            dict[str, Any],
            Depends(require_auth(required_scopes=["account:read"])),
        ],
    ) -> dict[str, Any]:
        return {"sub": details["sub"], "scopes": details["scopes"], "account": "primary"}

    @app.post("/chat/send")
    def send_message(
        payload: dict[str, str],
        details: Annotated[
            dict[str, Any],
            Depends(require_auth(required_scopes=["chat:send"])),
        ],
    ) -> dict[str, Any]:
        message = payload.get("message", "")
        try:
            outcome = supervisor_obj.dispatch(message, details["scopes"])
        except InsufficientScopeError:
            raise HTTPException(status_code=403, detail="insufficient_scope") from None

        audit.append(
            actor_sub=details["sub"],
            action="agentflow.dispatch",
            payload={
                "intent": outcome["intent"],
                "agent": outcome["agent"],
                "message_hash": _sha256(message),
            },
        )
        if outcome["intent"] == "action":
            audit.append(
                actor_sub=details["sub"],
                action="agentflow.action",
                payload={
                    "tool": outcome["result"]["tool"],
                    "card_ref_hash": _sha256(str(outcome["result"]["card_ref"])),
                    "status": outcome["result"]["status"],
                },
            )
        return {
            "sub": details["sub"],
            "scopes": details["scopes"],
            "intent": outcome["intent"],
            "agent": outcome["agent"],
            "result": outcome["result"],
            "status": "routed",
        }

    return app


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
