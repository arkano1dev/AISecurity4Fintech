from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidAlgorithmError, InvalidAudienceError, InvalidTokenError

from auth.config import settings
from auth.keys import get_active_private_key
from auth.models import VerifyResult


def _scope_value(scopes: list[str]) -> str:
    return " ".join(scopes)


def issue_token(user: dict[str, Any], audiences: list[str], scopes: list[str]) -> str:
    now = datetime.now(timezone.utc)
    key_handle = get_active_private_key()
    payload = {
        "sub": user["username"],
        "iss": settings.auth_issuer,
        "aud": audiences[0] if audiences else settings.auth_audiences[0],
        "exp": int((now + timedelta(seconds=settings.auth_token_ttl)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scopes": scopes,
        "scope": _scope_value(scopes),
    }
    return jwt.encode(payload, key_handle.private_key, algorithm="RS256", headers={"kid": key_handle.key_id})


def verify_token(token: str, expected_audience: str) -> VerifyResult:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in {"RS256"}:
            return VerifyResult(valid=False, reason="invalid_algorithm")

        payload = jwt.decode(
            token,
            key=get_active_private_key().public_key(),
            algorithms=["RS256"],
            audience=expected_audience,
            issuer=settings.auth_issuer,
            options={"require": ["exp", "iss", "aud", "sub", "jti"]},
        )
    except ExpiredSignatureError:
        return VerifyResult(valid=False, reason="token_expired")
    except InvalidAudienceError:
        return VerifyResult(valid=False, reason="invalid_audience")
    except (InvalidAlgorithmError, InvalidTokenError, ValueError):
        return VerifyResult(valid=False, reason="invalid_signature")

    return VerifyResult(
        valid=True,
        sub=str(payload.get("sub")),
        tenant=str(payload.get("tenant")) if payload.get("tenant") is not None else None,
        scopes=list(payload.get("scopes", [])),
        exp=int(payload.get("exp")) if payload.get("exp") is not None else None,
        jti=str(payload.get("jti")) if payload.get("jti") is not None else None,
    )
