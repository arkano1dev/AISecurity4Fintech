from __future__ import annotations

import json
import time
from typing import Any, cast

import httpx
import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidTokenError,
)

from agentflow.settings import settings


class AuthServiceClient:
    def __init__(self, base_url: str | None = None, http_client: Any | None = None) -> None:
        self.base_url = (base_url or settings.auth_service_url).rstrip("/")
        self.http_client = http_client
        self._jwks_cache: list[dict[str, Any]] | None = None
        self._jwks_cache_expires_at = 0.0

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if self.http_client is not None:
            if hasattr(self.http_client, "request"):
                response = self.http_client.request(method.upper(), path, json=payload)
            else:
                response = getattr(self.http_client, method.lower())(path, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"auth-service request failed: {response.text}")
            return response.json()

        url = f"{self.base_url}{path}"
        response = httpx.request(method.upper(), url, json=payload, timeout=5.0)
        if response.status_code >= 400:
            raise RuntimeError(f"auth-service request failed: {response.text}")
        return response.json()

    def issue_session(self, username: str, password: str) -> dict[str, Any]:
        token_response = self._request_json(
            "post",
            "/auth/token",
            payload={"username": username, "password": password},
        )
        return {
            "access_token": token_response["access_token"],
            "token_type": token_response.get("token_type", "Bearer"),
            "expires_in": int(token_response.get("expires_in", settings.token_ttl_seconds)),
        }

    def fetch_jwks(self) -> list[dict[str, Any]]:
        if self.http_client is not None:
            jwks = self._request_json("get", "/auth/.well-known/jwks.json")
            return cast(list[dict[str, Any]], jwks.get("keys", []))

        now = time.time()
        if self._jwks_cache is None or now >= self._jwks_cache_expires_at:
            jwks = self._request_json("get", "/auth/.well-known/jwks.json")
            self._jwks_cache = jwks.get("keys", [])
            self._jwks_cache_expires_at = now + settings.auth_service_jwks_ttl_seconds
        return self._jwks_cache or []


DEFAULT_CLIENT = AuthServiceClient()


def configure_auth_client(
    base_url: str | None = None,
    http_client: Any | None = None,
) -> AuthServiceClient:
    DEFAULT_CLIENT.base_url = (base_url or settings.auth_service_url).rstrip("/")
    DEFAULT_CLIENT.http_client = http_client
    DEFAULT_CLIENT._jwks_cache = None
    DEFAULT_CLIENT._jwks_cache_expires_at = 0.0
    return DEFAULT_CLIENT


def verify_token(token: str, expected_audience: str = "agentflow") -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            return {"valid": False, "reason": "invalid_algorithm"}

        jwk_key = next(
            (key for key in DEFAULT_CLIENT.fetch_jwks() if key.get("kid") == header.get("kid")),
            None,
        )
        if jwk_key is None:
            return {"valid": False, "reason": "invalid_signature"}

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
            json.dumps(
                {
                    "kty": "RSA",
                    "n": jwk_key["n"],
                    "e": jwk_key["e"],
                }
            )
        )
        payload = jwt.decode(
            token,
            key=public_key,  # type: ignore[arg-type]  # from_jwk returns public for a JWKS key
            algorithms=["RS256"],
            audience=expected_audience,
            issuer=settings.issuer,
            options={"require": ["exp", "iss", "aud", "sub", "jti"]},
        )
    except ExpiredSignatureError:
        return {"valid": False, "reason": "token_expired"}
    except InvalidAudienceError:
        return {"valid": False, "reason": "invalid_audience"}
    except (InvalidAlgorithmError, InvalidTokenError, ValueError, TypeError):
        return {"valid": False, "reason": "invalid_signature"}

    scopes = payload.get("scopes") or []
    if isinstance(scopes, str):
        scopes = scopes.split()

    return {
        "valid": True,
        "sub": payload.get("sub"),
        "tenant": payload.get("tenant"),
        "scopes": list(scopes),
        "exp": int(payload["exp"]),
        "jti": payload.get("jti"),
        "reason": None,
    }
