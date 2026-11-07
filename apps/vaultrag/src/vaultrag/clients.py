from __future__ import annotations

from typing import Any, Protocol, cast

import httpx


class Masker(Protocol):
    def mask(self, text: str) -> str: ...


class Auditor(Protocol):
    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class PiiClient:
    """HTTP client for the shared pii-proxy service."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def mask(self, text: str) -> str:
        response = httpx.post(f"{self.base_url}/pii/mask", json={"text": text}, timeout=10.0)
        response.raise_for_status()
        return str(response.json()["redacted"])


class AuditClient:
    """HTTP client for the shared audit-log service."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/audit/append",
            json={"actor_sub": actor_sub, "action": action, "payload": payload},
            timeout=10.0,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
