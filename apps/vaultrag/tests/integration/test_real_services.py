"""Real cross-service integration tests.

These wire the REAL pii-proxy, audit-log, and auth-service into VaultRAG over an
in-process ASGI transport, so the real redaction regexes, the real hash-chain
audit, and the real JWKS verification run — not fakes.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from audit_log.api import make_app as make_audit_app
from auth.api import make_app as make_auth_app
from auth.keys import get_active_private_key
from pii_proxy.api import make_app as make_pii_app
from vaultrag.auth import verify_token
from vaultrag.clients import AuditClient, PiiClient


class _SyncASGITransport(httpx.BaseTransport):
    """Runs an ASGI app synchronously per request, so sync httpx clients work."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        async def _run() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.request(
                    request.method,
                    request.url.path,
                    content=request.content,
                    headers=request.headers,
                )
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=response.content,
                )

        return asyncio.run(_run())


def _asgi_client(app: Any) -> httpx.Client:
    return httpx.Client(transport=_SyncASGITransport(app), base_url="http://test")


def test_real_pii_redaction_over_http() -> None:
    # The real pii-proxy app and its real regexes run over an ASGI transport.
    client = PiiClient("http://pii", client=_asgi_client(make_pii_app()))

    redacted = client.mask(
        "IBAN DE89370400440532013000, card 4111 1111 1111 1111, call +49 170 123 4567."
    )

    assert "DE89370400440532013000" not in redacted
    assert "4111 1111 1111 1111" not in redacted
    assert "+49 170 123 4567" not in redacted
    assert "[IBAN]" in redacted
    assert "[PAN]" in redacted
    assert "[PHONE]" in redacted


def test_real_audit_hash_chain_over_http() -> None:
    audit_app = make_audit_app()
    client = _asgi_client(audit_app)
    audit = AuditClient("http://audit", client=client)

    audit.append(actor_sub="analyst", action="query.executed", payload={"q": "x"})
    audit.append(actor_sub="analyst", action="query.executed", payload={"q": "y"})

    verdict = client.get("/audit/verify").json()
    assert verdict["valid"] is True
    assert verdict["count"] == 2


def test_real_auth_verify_accepts_valid_token() -> None:
    auth_client = _asgi_client(make_auth_app())
    token = _mint_token(scopes=["vaultrag:query"])

    result = verify_token(token, http_client=auth_client)

    assert result["valid"] is True
    assert result["sub"] == "alice"
    assert result["scopes"] == ["vaultrag:query"]


def test_real_auth_verify_rejects_garbage() -> None:
    auth_client = _asgi_client(make_auth_app())

    result = verify_token("not-a-real-token", http_client=auth_client)

    assert result["valid"] is False


def _mint_token(*, scopes: list[str], audience: str = "agentflow") -> str:
    key = get_active_private_key()
    now = datetime.now(UTC)
    payload = {
        "sub": "alice",
        "iss": "auth",
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "integration-jti",
        "scopes": scopes,
        "scope": " ".join(scopes),
    }
    return jwt.encode(payload, key.private_key, algorithm="RS256", headers={"kid": key.key_id})
