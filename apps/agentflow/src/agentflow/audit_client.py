from __future__ import annotations

from typing import Any, Protocol, cast

import httpx


class Auditor(Protocol):
    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]: ...


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
