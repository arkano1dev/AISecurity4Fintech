from __future__ import annotations

from typing import Any, Protocol, cast

import httpx


class Masker(Protocol):
    def mask(self, text: str) -> str: ...


class Auditor(Protocol):
    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class PiiClient:
    """HTTP client for the shared pii-proxy service."""

    def __init__(self, base_url: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client

    def mask(self, text: str) -> str:
        response = self._post("/pii/mask", json={"text": text})
        response.raise_for_status()
        return str(response.json()["redacted"])

    def _post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(path, json=json, timeout=10.0)
        return httpx.post(f"{self.base_url}{path}", json=json, timeout=10.0)


class AuditClient:
    """HTTP client for the shared audit-log service."""

    def __init__(self, base_url: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._post(
            "/audit/append",
            json={"actor_sub": actor_sub, "action": action, "payload": payload},
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def _post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(path, json=json, timeout=10.0)
        return httpx.post(f"{self.base_url}{path}", json=json, timeout=10.0)
