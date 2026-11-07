from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from agentflow.agent import Agent
from agentflow.agents import ActionAgent, RetrievalAgent
from agentflow.audit_client import AuditClient, Auditor
from agentflow.auth_client import AuthServiceClient, configure_auth_client
from agentflow.deps import require_auth
from agentflow.llm import Decider, LlmClient
from agentflow.pii_client import Masker, PiiClient
from agentflow.settings import settings
from agentflow.supervisor import InsufficientScopeError, Supervisor
from agentflow.tools import AccountService
from agentflow.vaultrag_client import VaultragClient, VaultragQuerier, VaultragUnavailableError


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
    pii_client: Masker | None = None,
    vaultrag_client: VaultragQuerier | None = None,
    account_service: AccountService | None = None,
    llm_client: Decider | None = None,
    agent: Agent | None = None,
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
    pii = pii_client or PiiClient(settings.pii_proxy_url)
    vaultrag = vaultrag_client or VaultragClient(settings.vaultrag_url)
    account_svc = account_service or AccountService()
    fallback = supervisor or Supervisor(
        RetrievalAgent(pii, vaultrag),
        ActionAgent(account_svc),
    )
    audit = audit_client or AuditClient(settings.audit_log_url)
    llm = llm_client or LlmClient()
    agent_obj = agent or Agent(llm, pii, vaultrag, account_svc, fallback, audit)

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
            outcome = agent_obj.run(
                message,
                actor_sub=details["sub"],
                scopes=details["scopes"],
                token=details["token"],
            )
        except InsufficientScopeError:
            raise HTTPException(status_code=403, detail="insufficient_scope") from None
        except VaultragUnavailableError:
            raise HTTPException(status_code=503, detail="vaultrag_unavailable") from None

        return {
            "sub": details["sub"],
            "scopes": details["scopes"],
            **outcome,
            "status": "routed",
        }

    return app
