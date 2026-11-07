from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vaultrag.settings import settings

_bearer = HTTPBearer(auto_error=False)

TokenVerifier = Callable[[str], dict[str, Any]]


def verify_token(token: str, *, http_client: httpx.Client | None = None) -> dict[str, Any]:
    """Verify an RS256 JWT against the shared auth-service JWKS.

    The consumer verifies locally against a fetched JWKS; the issuer holds the
    private key. The audience is the shared ``agentflow`` value for the MVP.
    """
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            return {"valid": False, "reason": "invalid_algorithm"}
        if http_client is not None:
            response = http_client.get("/auth/.well-known/jwks.json")
        else:
            response = httpx.get(
                f"{settings.auth_service_url}/auth/.well-known/jwks.json", timeout=5.0
            )
        response.raise_for_status()
        keys = response.json().get("keys", [])
        jwk_key = next((key for key in keys if key.get("kid") == header.get("kid")), None)
        if jwk_key is None:
            return {"valid": False, "reason": "invalid_signature"}
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
            json.dumps({"kty": "RSA", "n": jwk_key["n"], "e": jwk_key["e"]})
        )
        payload = jwt.decode(
            token,
            key=public_key,  # type: ignore[arg-type]  # from_jwk returns a public key for a JWKS key
            algorithms=["RS256"],
            audience=settings.audience,
            issuer=settings.issuer,
            options={"require": ["exp", "iss", "aud", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "token_expired"}
    except jwt.InvalidAudienceError:
        return {"valid": False, "reason": "invalid_audience"}
    except (jwt.InvalidAlgorithmError, jwt.InvalidTokenError, ValueError, TypeError):
        return {"valid": False, "reason": "invalid_signature"}

    scopes = payload.get("scopes") or []
    if isinstance(scopes, str):
        scopes = scopes.split()
    return {"valid": True, "sub": payload.get("sub"), "scopes": list(scopes), "reason": None}


def require_auth(
    required_scopes: list[str] | None = None,
    verify: TokenVerifier | None = None,
) -> Callable[..., dict[str, Any]]:
    def dependency(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer),
        ],
    ) -> dict[str, Any]:
        if credentials is None:
            raise HTTPException(status_code=401, detail="missing_token")
        result = (verify or verify_token)(credentials.credentials)
        if not result["valid"]:
            raise HTTPException(status_code=401, detail=result.get("reason"))
        scopes = list(result.get("scopes", []))
        if required_scopes and set(required_scopes) - set(scopes):
            raise HTTPException(status_code=403, detail="insufficient_scope")
        return {"sub": result.get("sub"), "scopes": scopes}

    return dependency
