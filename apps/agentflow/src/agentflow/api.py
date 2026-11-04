from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from agentflow.auth_client import AuthServiceClient, configure_auth_client
from agentflow.deps import require_auth
from agentflow.settings import settings


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
        return {
            "sub": details["sub"],
            "scopes": details["scopes"],
            "message": payload.get("message", ""),
            "status": "accepted",
        }

    return app
