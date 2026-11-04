from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from auth.config import load_users
from auth.jwt import issue_token, verify_token
from auth.models import TokenRequest, TokenResponse, VerifyRequest


def make_app() -> FastAPI:
    app = FastAPI(title="Auth Service")

    @app.post("/auth/token", response_model=TokenResponse)
    def issue_access_token(payload: TokenRequest) -> TokenResponse:
        users = load_users()
        user = users.get(payload.username)
        if user is None or user.get("password") != payload.password:
            raise HTTPException(status_code=401, detail="invalid_credentials")

        token = issue_token(
            {"username": payload.username}, ["agentflow"], list(user.get("scopes", []))
        )
        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=900,
            scope=" ".join(user.get("scopes", [])),
        )

    @app.get("/auth/.well-known/jwks.json")
    def jwks() -> dict[str, list[dict[str, str]]]:
        from auth.keys import get_public_jwk_set

        return get_public_jwk_set()

    @app.post("/auth/verify")
    def verify(payload: VerifyRequest) -> dict[str, Any]:
        result = verify_token(payload.token, "agentflow")
        if not result.valid:
            return JSONResponse(status_code=401, content={"valid": False, "reason": result.reason})
        return {
            "valid": True,
            "sub": result.sub,
            "tenant": result.tenant,
            "scopes": result.scopes,
            "exp": result.exp,
            "jti": result.jti,
        }

    return app
