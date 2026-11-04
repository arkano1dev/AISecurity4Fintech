from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.config import settings
from auth.jwt import verify_token

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

        result = verify_token(credentials.credentials, settings.auth_audiences[0])
        if not result.valid:
            raise HTTPException(status_code=401, detail=result.reason)

        missing_scopes = set(required_scopes or []) - set(result.scopes)
        if missing_scopes:
            raise HTTPException(status_code=403, detail="insufficient_scope")

        return {"sub": result.sub, "scopes": result.scopes}

    return dependency