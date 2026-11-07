from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agentflow.auth_client import verify_token
from agentflow.settings import settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(required_scopes: list[str] | None = None) -> Callable[..., dict[str, Any]]:
    def dependency(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer),
        ],
    ) -> dict[str, Any]:
        if credentials is None:
            raise HTTPException(status_code=401, detail="missing_token")

        result = verify_token(credentials.credentials, expected_audience=settings.audience)
        if not result["valid"]:
            raise HTTPException(status_code=401, detail=result["reason"])

        scopes = list(result.get("scopes", []))
        if required_scopes and set(required_scopes) - set(scopes):
            raise HTTPException(status_code=403, detail="insufficient_scope")

        return {"sub": result.get("sub"), "scopes": scopes, "token": credentials.credentials}

    return dependency
