from __future__ import annotations

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


class VerifyRequest(BaseModel):
    token: str


class JWK(BaseModel):
    kty: str
    alg: str
    use: str
    kid: str
    n: str
    e: str


class VerifyResult(BaseModel):
    valid: bool
    sub: str | None = None
    tenant: str | None = None
    scopes: list[str] = Field(default_factory=list)
    exp: int | None = None
    jti: str | None = None
    reason: str | None = None
